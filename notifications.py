import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(subject: str, body: str, recipients: list[str]) -> None:
    mail_enabled = os.getenv("MAIL_ENABLED", "false").lower() == "true"
    if not mail_enabled:
        print("MAIL DISABLED")
        print("SUBJECT:", subject)
        print("TO:", ", ".join(recipients))
        print("BODY:", body)
        return

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    mail_from = os.getenv("MAIL_FROM", "no-reply@example.com")

    msg = MIMEMultipart()
    msg["From"] = mail_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(smtp_host, smtp_port)
    try:
        if smtp_use_tls:
            server.starttls()
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        server.sendmail(mail_from, recipients, msg.as_string())
    finally:
        server.quit()


def notify_new_pickup(order) -> None:
    lab_email = os.getenv("LAB_NOTIFICATION_EMAIL", "").strip()
    driver_email = os.getenv("DRIVER_NOTIFICATION_EMAIL", "").strip()

    recipients = [email for email in [lab_email, driver_email] if email]
    if not recipients:
        return

    subject = f"New Pickup Request #{order.id}"
    body = (
        f"A new specimen pickup has been requested.\n\n"
        f"Pickup ID: {order.id}\n"
        f"Patient: {order.patient_first_name} {order.patient_last_name}\n"
        f"Address: {order.pickup_address}\n"
        f"Facility: {order.facility_name or 'N/A'}\n"
        f"Priority: {order.priority}\n"
        f"Ordered By: {order.ordering_nurse_name}\n"
        f"Tests Ordered: {order.tests_ordered}\n"
        f"Special Instructions: {order.special_instructions or 'None'}\n"
        f"Status: {order.status}\n"
    )
    send_email(subject, body, recipients)


def notify_pickup_accepted(order, driver_name: str) -> None:
    lab_email = os.getenv("LAB_NOTIFICATION_EMAIL", "").strip()
    recipients = [email for email in [lab_email] if email]
    if not recipients:
        return

    subject = f"Pickup #{order.id} Accepted"
    body = (
        f"Pickup #{order.id} has been accepted.\n\n"
        f"Driver: {driver_name}\n"
        f"Patient: {order.patient_first_name} {order.patient_last_name}\n"
        f"Address: {order.pickup_address}\n"
        f"Current Status: {order.status}\n"
    )
    send_email(subject, body, recipients)
