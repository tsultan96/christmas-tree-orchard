import os
import smtplib
from datetime import date, datetime
from email.message import EmailMessage

import gspread
from dotenv import load_dotenv
from flask import Flask, render_template, request



load_dotenv()



app = Flask(__name__)

REQUIRED_FIELDS = {
    "species": "a tree type",
    "tree_size": "a tree size",
    "name": "your name",
    "phone": "your phone number",
    "street": "your street address",
    "city": "your city",
    "delivery_date": "a delivery date",
    "time_window": "a delivery time",
    "payment": "a payment method",
}


def validate_order(data):
    errors = []

    for field, label in REQUIRED_FIELDS.items():
        if data[field] == "":
            errors.append(f"Please enter {label}.")

    if data["quantity"] is None or not 1 <= data["quantity"] <= 50:
        errors.append("Please enter a quantity between 1 and 50.")
        
    if data["delivery_date"]:
        try:
            chosen_date = date.fromisoformat(data["delivery_date"])
        except ValueError:
            errors.append("Please enter a valid delivery date.")
        else:
            if chosen_date < date.today():
                errors.append("The delivery date can't be in the past.")
    return errors

def get_sheet():
    client = gspread.service_account(filename=os.getenv("GOOGLE_CREDENTIALS_FILE"))
    return client.open_by_key(os.getenv("SHEET_ID")).sheet1

def save_order(data):
    sheet = get_sheet()


    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        data["name"],
        data["phone"],
        data["email"],
        data["species"],
        data["tree_size"],
        data["quantity"],
        "Yes" if data["flocked"] else "No",
        data["street"],
        data["apt"],
        data["city"],
        data["zip"],
        data["delivery_date"],
        data["time_window"],
        data["delivery_notes"],
        data["payment"],
        "No",
    ]
    sheet.append_row(row)

def get_orders_for(day):
    orders = get_sheet().get_all_records(numericise_ignore=["all"])
    result = []
    for row_number, order in enumerate(orders, start=2):
        if order["Delivery date"] == day:
            order["row"] = row_number
            result.append(order)
    return result


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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_APP_PASSWORD"))
        smtp.send_message(msg)
        
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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_APP_PASSWORD"))
        smtp.send_message(msg)





@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
            order_data = {
                "species": request.form.get("species", "").strip(),
                "tree_size": request.form.get("tree_size", "").strip(),
                "flocked": request.form.get("flocked") == "yes",
                "name": request.form.get("name", "").strip(),
                "email": request.form.get("email", "").strip(),
                "phone": request.form.get("phone", "").strip(),
                "street": request.form.get("street", "").strip(),
                "apt": request.form.get("apt", "").strip(),
                "city": request.form.get("city", "").strip(),
                "zip": request.form.get("zip", "").strip(),
                "delivery_date": request.form.get("delivery_date", "").strip(),
                "time_window": request.form.get("time_window", "").strip(),
                "delivery_notes": request.form.get("delivery_notes", "").strip(),
                "payment": request.form.get("payment", "").strip(),
            }
            
            try:
                order_data["quantity"] = int(request.form.get("quantity",""))
            except ValueError:
                order_data["quantity"] = None
            errors = validate_order(order_data)
            if errors:
                return render_template("order.html", errors=errors, form=order_data, today=date.today().isoformat())


            save_order(order_data)
            try:
                send_alert(order_data)
                if order_data["email"]:
                    send_confirmation(order_data)

            except Exception as e:
                print(f"Alert email failed: {e}")
            return render_template("thanks.html", order=order_data)



@app.route("/admin")
def admin():
    day = request.args.get("date", date.today().isoformat())
    orders = get_orders_for(day)
    return render_template("admin.html", orders=orders, day=day)


    return render_template("order.html", form={}, today = date.today().isoformat())

if __name__ == "__main__":
    app.run(debug=True)