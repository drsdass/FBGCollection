import os
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, login_required, logout_user, current_user

from extensions import db, login_manager
from models import User, PickupOrder, PickupStatusHistory
from forms import LoginForm, PickupForm, StatusUpdateForm, CreateUserForm
from notifications import notify_new_pickup, notify_pickup_accepted

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def role_required(*roles):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                if not current_user.is_authenticated:
                    return redirect(url_for("login"))
                if current_user.role not in roles:
                    flash("Access denied.", "danger")
                    return redirect(url_for("index"))
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    def record_status_change(order, old_status, new_status, notes=None):
        history = PickupStatusHistory(
            pickup_order_id=order.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_user_id=current_user.id if current_user.is_authenticated else None,
            notes=notes,
        )
        db.session.add(history)
        db.session.commit()

    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        if current_user.role == "nurse":
            return redirect(url_for("nurse_dashboard"))
        if current_user.role == "driver":
            return redirect(url_for("driver_dashboard"))
        return redirect(url_for("admin_dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                flash("Logged in successfully.", "success")
                return redirect(url_for("index"))
            flash("Invalid email or password.", "danger")

        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out successfully.", "info")
        return redirect(url_for("login"))

    @app.route("/nurse/dashboard")
    @login_required
    @role_required("nurse", "admin")
    def nurse_dashboard():
        if current_user.role == "admin":
            pickups = PickupOrder.query.order_by(PickupOrder.created_at.desc()).all()
        else:
            pickups = PickupOrder.query.filter_by(
                submitted_by_user_id=current_user.id
            ).order_by(PickupOrder.created_at.desc()).all()
        return render_template("nurse_dashboard.html", pickups=pickups)

    @app.route("/pickup/new", methods=["GET", "POST"])
    @login_required
    @role_required("nurse", "admin")
    def new_pickup():
        form = PickupForm()

        if current_user.role == "nurse" and request.method == "GET":
            form.ordering_nurse_name.data = current_user.full_name
            form.ordering_nurse_phone.data = current_user.phone

        if form.validate_on_submit():
            order = PickupOrder(
                patient_first_name=form.patient_first_name.data.strip(),
                patient_last_name=form.patient_last_name.data.strip(),
                dob=(form.dob.data or "").strip(),
                patient_identifier=(form.patient_identifier.data or "").strip(),
                pickup_address=form.pickup_address.data.strip(),
                facility_name=(form.facility_name.data or "").strip(),
                ordering_nurse_name=form.ordering_nurse_name.data.strip(),
                ordering_nurse_phone=(form.ordering_nurse_phone.data or "").strip(),
                tests_ordered=form.tests_ordered.data.strip(),
                special_instructions=(form.special_instructions.data or "").strip(),
                priority=form.priority.data,
                status="Requested",
                submitted_by_user_id=current_user.id,
            )
            db.session.add(order)
            db.session.commit()

            record_status_change(order, None, "Requested", "Pickup created")
            notify_new_pickup(order)

            flash("Pickup request submitted successfully.", "success")
            return redirect(url_for("pickup_detail", pickup_id=order.id))

        return render_template("new_pickup.html", form=form)

    @app.route("/driver/dashboard")
    @login_required
    @role_required("driver", "admin")
    def driver_dashboard():
        open_pickups = PickupOrder.query.filter_by(status="Requested").order_by(
            PickupOrder.created_at.asc()
        ).all()

        my_pickups = PickupOrder.query.filter_by(
            accepted_by_driver_id=current_user.id
        ).order_by(PickupOrder.created_at.desc()).all()

        return render_template(
            "driver_dashboard.html",
            open_pickups=open_pickups,
            my_pickups=my_pickups,
        )

    @app.route("/pickup/<int:pickup_id>")
    @login_required
    def pickup_detail(pickup_id):
        pickup = PickupOrder.query.get_or_404(pickup_id)

        allowed = False
        if current_user.role == "admin":
            allowed = True
        elif current_user.role == "driver" and pickup.accepted_by_driver_id == current_user.id:
            allowed = True
        elif current_user.role == "driver" and pickup.status == "Requested":
            allowed = True
        elif current_user.role == "nurse" and pickup.submitted_by_user_id == current_user.id:
            allowed = True

        if not allowed:
            abort(403)

        history = PickupStatusHistory.query.filter_by(
            pickup_order_id=pickup.id
        ).order_by(PickupStatusHistory.changed_at.desc()).all()

        status_form = StatusUpdateForm()
        return render_template(
            "pickup_detail.html",
            pickup=pickup,
            history=history,
            status_form=status_form,
        )

    @app.route("/pickup/<int:pickup_id>/accept", methods=["POST"])
    @login_required
    @role_required("driver", "admin")
    def accept_pickup(pickup_id):
        pickup = PickupOrder.query.get_or_404(pickup_id)

        if pickup.status != "Requested":
            flash("This pickup is no longer available.", "warning")
            return redirect(url_for("driver_dashboard"))

        old_status = pickup.status
        pickup.status = "Accepted"
        pickup.accepted_by_driver_id = current_user.id
        pickup.accepted_at = datetime.utcnow()

        db.session.commit()
        record_status_change(pickup, old_status, "Accepted", "Driver accepted pickup")
        notify_pickup_accepted(pickup, current_user.full_name)

        flash("Pickup accepted.", "success")
        return redirect(url_for("pickup_detail", pickup_id=pickup.id))

    @app.route("/pickup/<int:pickup_id>/update-status", methods=["POST"])
    @login_required
    @role_required("driver", "admin")
    def update_pickup_status(pickup_id):
        pickup = PickupOrder.query.get_or_404(pickup_id)
        form = StatusUpdateForm()

        if not form.validate_on_submit():
            flash("Invalid status submission.", "danger")
            return redirect(url_for("pickup_detail", pickup_id=pickup.id))

        if current_user.role == "driver":
            if pickup.accepted_by_driver_id != current_user.id:
                flash("You can only update pickups assigned to you.", "danger")
                return redirect(url_for("driver_dashboard"))

        new_status = form.status.data
        old_status = pickup.status
        pickup.status = new_status

        now = datetime.utcnow()
        if new_status == "Accepted" and not pickup.accepted_at:
            pickup.accepted_at = now
        elif new_status == "En Route":
            pickup.enroute_at = now
        elif new_status == "Picked Up":
            pickup.picked_up_at = now
        elif new_status == "Delivered to Lab":
            pickup.delivered_at = now

        db.session.commit()
        record_status_change(pickup, old_status, new_status, "Status updated")

        flash("Pickup status updated.", "success")
        return redirect(url_for("pickup_detail", pickup_id=pickup.id))

    @app.route("/admin/dashboard")
    @login_required
    @role_required("admin")
    def admin_dashboard():
        pickups = PickupOrder.query.order_by(PickupOrder.created_at.desc()).all()
        users = User.query.order_by(User.full_name.asc()).all()
        return render_template("admin_dashboard.html", pickups=pickups, users=users)

    @app.route("/admin/users/new", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def create_user():
        form = CreateUserForm()

        if form.validate_on_submit():
            existing = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if existing:
                flash("A user with that email already exists.", "warning")
                return render_template("create_user.html", form=form)

            user = User(
                full_name=form.full_name.data.strip(),
                email=form.email.data.lower().strip(),
                phone=(form.phone.data or "").strip(),
                role=form.role.data,
            )
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            flash("User created successfully.", "success")
            return redirect(url_for("admin_dashboard"))

        return render_template("create_user.html", form=form)

    @app.route("/seed-admin")
    def seed_admin():
        if User.query.filter_by(email="admin@example.com").first():
            return "Seed users already exist."

        admin = User(
            full_name="Admin User",
            email="admin@example.com",
            phone="555-100-0001",
            role="admin",
        )
        admin.set_password("admin123")

        nurse = User(
            full_name="Test Nurse",
            email="nurse@example.com",
            phone="555-100-0002",
            role="nurse",
        )
        nurse.set_password("nurse123")

        driver = User(
            full_name="Test Driver",
            email="driver@example.com",
            phone="555-100-0003",
            role="driver",
        )
        driver.set_password("driver123")

        db.session.add_all([admin, nurse, driver])
        db.session.commit()
        return "Seeded admin, nurse, and driver users."

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("base.html", content="Forbidden"), 403

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
