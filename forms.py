from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    SelectField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class PickupForm(FlaskForm):
    patient_first_name = StringField(
        "Patient First Name", validators=[DataRequired(), Length(max=100)]
    )
    patient_last_name = StringField(
        "Patient Last Name", validators=[DataRequired(), Length(max=100)]
    )
    dob = StringField("Date of Birth", validators=[Optional(), Length(max=20)])
    patient_identifier = StringField(
        "Patient ID / MRN", validators=[Optional(), Length(max=100)]
    )
    pickup_address = StringField(
        "Pickup Address", validators=[DataRequired(), Length(max=255)]
    )
    facility_name = StringField(
        "Facility / Agency", validators=[Optional(), Length(max=150)]
    )
    ordering_nurse_name = StringField(
        "Ordering Nurse Name", validators=[DataRequired(), Length(max=150)]
    )
    ordering_nurse_phone = StringField(
        "Ordering Nurse Phone", validators=[Optional(), Length(max=30)]
    )
    tests_ordered = TextAreaField("Tests Ordered", validators=[DataRequired()])
    special_instructions = TextAreaField("Special Instructions", validators=[Optional()])
    priority = SelectField(
        "Priority",
        choices=[("Routine", "Routine"), ("STAT", "STAT"), ("Urgent", "Urgent")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Submit Pickup Request")


class StatusUpdateForm(FlaskForm):
    status = SelectField(
        "Update Status",
        choices=[
            ("Accepted", "Accepted"),
            ("En Route", "En Route"),
            ("Picked Up", "Picked Up"),
            ("Delivered to Lab", "Delivered to Lab"),
            ("Cancelled", "Cancelled"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Update Status")


class CreateUserForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    role = SelectField(
        "Role",
        choices=[("nurse", "Nurse"), ("driver", "Driver"), ("admin", "Admin")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Create User")
