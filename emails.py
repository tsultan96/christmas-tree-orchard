"""Order emails sent through Gmail."""

import os
import smtplib
from email.message import EmailMessage

from orders import describe_item


def _send(msg):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_APP_PASSWORD"))
        smtp.send_message(msg)


def _trees(items):
    return "".join(f"  - {describe_item(item)}\n" for item in items)


def send_alert(details, items, total_cents):
    msg = EmailMessage()
    msg["Subject"] = f"New tree order from {details['name']} ({details['order_id']})"
    msg["From"] = os.getenv("EMAIL_ADDRESS")
    msg["To"] = os.getenv("ALERT_TO")
    msg.set_content(
        f"Order: {details['order_id']}\n"
        f"Name: {details['name']}\n"
        f"Phone: {details['phone']}\n"
        f"Trees:\n{_trees(items)}"
        f"Address: {details['street']} {details['apt']}, {details['city']} {details['zip']}\n"
        f"Delivery: {details['delivery_date']}, {details['time_window']}\n"
        f"Notes: {details['delivery_notes']}\n"
        f"Payment: {details['payment']}\n"
        f"Total: ${total_cents / 100:.2f}\n"
    )
    _send(msg)


def send_confirmation(details, items, total_cents):
    msg = EmailMessage()
    msg["Subject"] = "Your Christmas tree order is confirmed"
    msg["From"] = os.getenv("EMAIL_ADDRESS")
    msg["To"] = details["email"]
    msg.set_content(
        f"Hi {details['name']},\n\n"
        f"Thanks for your order! Here are the details:\n\n"
        f"Trees:\n{_trees(items)}"
        f"Delivery: {details['delivery_date']}, {details['time_window']}\n"
        f"Address: {details['street']} {details['apt']}, {details['city']} {details['zip']}\n"
        f"Total: ${total_cents / 100:.2f}\n\n"
        f"We'll call you at {details['phone']} if we have any questions.\n"
    )
    _send(msg)
