import os
import smtplib
from datetime import date, datetime
from email.message import EmailMessage
import secrets
from flask import Flask, redirect, render_template, request, session, url_for

import gspread, stripe
from dotenv import load_dotenv



load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")



app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


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

PRICES = {
    "3ft": 100,
    "5ft": 150,
    "8ft": 200,
    "12ft": 250,
}
FLOCKING_PRICE = 25
DOZEN_DISCOUNT = 0.10


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

def order_total(data):
    """Return the order total in cents, calculated from our own PRICES."""
    per_tree = PRICES[data["tree_size"]]
    if data["flocked"]:
        per_tree += FLOCKING_PRICE
    total = per_tree * data["quantity"]
    if data["quantity"] >= 12:
        total = total * (1 - DOZEN_DISCOUNT)
    return round(total * 100)

def create_checkout(data, row):
    """Create a Stripe Checkout page for this order and return its URL."""
    checkout = stripe.checkout.Session.create(
        mode="payment",
        metadata={"row": row},

        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": order_total(data),
                "product_data": {
                    "name": f"{data['quantity']} x {data['species']}, {data['tree_size']}",
                },
            },
            "quantity": 1,
        }],
        success_url=url_for("paid", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_for("order", _external=True),
    )
    return checkout.url


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
        "Cash" if data["payment"] == "cash" else "No",
    ]
    result = sheet.append_row(row)
    updated_range = result["updates"]["updatedRange"]   # e.g. "Sheet1!A23:R23"
    return int(updated_range.split("!")[1].split(":")[0][1:])


def get_orders_for(day):
    orders = get_sheet().get_all_records(numericise_ignore=["all"])
    result = []
    for row_number, order in enumerate(orders, start=2):
        if order["Delivery date"] == day:
            order["row"] = row_number
            result.append(order)
    return result

DELIVERED_COLUMN = 17  # column Q in the sheet: "Delivered"


def set_delivered(row, delivered):
    get_sheet().update_cell(row, DELIVERED_COLUMN, "Yes" if delivered else "No")

PAID_COLUMN = 18  # column R in the sheet: "Paid"


def set_paid(row):
    get_sheet().update_cell(row, PAID_COLUMN, "Yes")


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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        smtp.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_APP_PASSWORD"))
        smtp.send_message(msg)





@app.route("/")
def index():
    return render_template(
        "index.html",
        prices=PRICES,
        flocking_price=FLOCKING_PRICE,
        dozen_discount=DOZEN_DISCOUNT,
    )


@app.route("/member")
def member():
    return render_template("member.html")


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


            row = save_order(order_data)
            try:
                send_alert(order_data)
                if order_data["email"]:
                    send_confirmation(order_data)

            except Exception as e:
                print(f"Alert email failed: {e}")

            if order_data["payment"] == "card":
                session["last_order"] = order_data
                return redirect(create_checkout(order_data, row))
            return render_template("thanks.html", order=order_data)
    return render_template("order.html", form={}, today=date.today().isoformat())


@app.route("/paid")
def paid():
    order = session.get("last_order")
    try:
        checkout = stripe.checkout.Session.retrieve(request.args.get("session_id", ""))
    except stripe.StripeError:
        return redirect(url_for("index"))
    if checkout.payment_status != "paid":
        return redirect(url_for("index"))
    set_paid(int(checkout.metadata["row"]))
    if not order:
        return redirect(url_for("index"))
    return render_template("thanks.html", order=order)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        typed = request.form.get("password", "")
        if secrets.compare_digest(typed, os.getenv("ADMIN_PASSWORD")):
            session["admin"] = True
            return redirect(url_for("admin"))
        error = "Wrong password."
    return render_template("login.html", error=error)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))

    day = request.args.get("date", date.today().isoformat())
    orders = get_orders_for(day)
    return render_template("admin.html", orders=orders, day=day)

@app.route("/admin/delivered", methods=["POST"])
def mark_delivered():
    if not session.get("admin"):
        return redirect(url_for("login"))

    row = int(request.form["row"])
    set_delivered(row, request.form["delivered"] == "Yes")
    return redirect(url_for("admin", date=request.form["date"]))


if __name__ == "__main__":
    app.run(debug=True)