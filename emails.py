"""Order emails sent through Gmail."""

import os
import smtplib
from email.message import EmailMessage


def _send(msg):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_APP_PASSWORD"))
        smtp.send_message(msg)


def send_alert(data):
    msg = EmailMessage()
    msg["Subject"] = f"New tree order from {data['name']}"
    msg["From"] = os.getenv("EMAIL_ADDRESS")
    msg["To"] = os.getenv("ALERT_TO")
    msg.set_content(
        f"Name: {data['name']}\n"
        f"Phone: {data['phone']}\n"
        f"Tree: {data['quantity']} x {data['species']}, {data['tree_size']}"
        f"{' (flocked)' if data['flocked'] else ''}\n"
        f"Address: {data['street']} {data['apt']}, {data['city']} {data['zip']}\n"
        f"Delivery: {data['delivery_date']}, {data['time_window']}\n"
        f"Notes: {data['delivery_notes']}\n"
        f"Payment: {data['payment']}\n"
    )
    _send(msg)


def send_confirmation(data):
    msg = EmailMessage()
    msg["Subject"] = "Your Christmas tree order is confirmed"
    msg["From"] = os.getenv("EMAIL_ADDRESS")
    msg["To"] = data["email"]
    msg.set_content(
        f"Hi {data['name']},\n\n"
        f"Thanks for your order! Here are the details:\n\n"
        f"Tree: {data['quantity']} x {data['species']}, {data['tree_size']}"
        f"{' (flocked)' if data['flocked'] else ''}\n"
        f"Delivery: {data['delivery_date']}, {data['time_window']}\n"
        f"Address: {data['street']} {data['apt']}, {data['city']} {data['zip']}\n\n"
        f"We'll call you at {data['phone']} if we have any questions.\n"
    )
    _send(msg)
