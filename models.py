from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # nurse, driver, admin
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    submitted_pickups = db.relationship(
        "PickupOrder",
        foreign_keys="PickupOrder.submitted_by_user_id",
        backref="submitted_by",
        lazy=True,
    )

    accepted_pickups = db.relationship(
        "PickupOrder",
        foreign_keys="PickupOrder.accepted_by_driver_id",
        backref="accepted_by_driver",
        lazy=True,
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_user

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class PickupOrder(db.Model):
    __tablename__ = "pickup_orders"

    id = db.Column(db.Integer, primary_key=True)
    patient_first_name = db.Column(db.String(100), nullable=False)
    patient_last_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(20))
    patient_identifier = db.Column(db.String(100))
    pickup_address = db.Column(db.String(255), nullable=False)
    facility_name = db.Column(db.String(150))
    ordering_nurse_name = db.Column(db.String(150), nullable=False)
    ordering_nurse_phone = db.Column(db.String(30))
    tests_ordered = db.Column(db.Text, nullable=False)
    special_instructions = db.Column(db.Text)
    priority = db.Column(db.String(20), default="Routine", nullable=False)
    status = db.Column(db.String(30), default="Requested", nullable=False, index=True)

    submitted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    accepted_by_driver_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = db.Column(db.DateTime)
    enroute_at = db.Column(db.DateTime)
    picked_up_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)

    history = db.relationship(
        "PickupStatusHistory",
        backref="pickup_order",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def patient_full_name(self) -> str:
        return f"{self.patient_first_name} {self.patient_last_name}"

    def __repr__(self):
        return f"<PickupOrder #{self.id} - {self.status}>"


class PickupStatusHistory(db.Model):
    __tablename__ = "pickup_status_history"

    id = db.Column(db.Integer, primary_key=True)
    pickup_order_id = db.Column(
        db.Integer,
        db.ForeignKey("pickup_orders.id"),
        nullable=False,
        index=True,
    )
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    changed_by = db.relationship("User", backref="status_changes", lazy=True)

    def __repr__(self):
        return f"<PickupStatusHistory {self.pickup_order_id}: {self.new_status}>"
