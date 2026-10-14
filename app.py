import os
import secrets
from datetime import date, datetime

import stripe
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from emails import send_alert, send_confirmation
from orders import DOZEN_DISCOUNT, FLOCKING_PRICE, PRICES, validate_order
from payments import create_checkout, paid_row
from sheets import create_customer, find_customer, get_orders_for_month, save_order, set_delivered, set_paid


load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


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


@app.route("/signup", methods=["GET", "POST"])
def signup():
    errors = []
    form = {}
    if request.method == "POST":
        form = {
            "email": request.form.get("email", "").strip().lower(),
            "name": request.form.get("name", "").strip(),
            "phone": request.form.get("phone", "").strip(),
        }
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if "@" not in form["email"]:
            errors.append("Please enter a valid email.")
        if not form["name"]:
            errors.append("Please enter your name.")
        if len(password) < 8:
            errors.append("Your password needs at least 8 characters.")
        if password != confirm:
            errors.append("The two passwords don't match.")
        if not errors and find_customer(form["email"]):
            errors.append("An account with this email already exists. Try logging in.")

        if not errors:
            create_customer(form["email"], form["name"], form["phone"], password)
            session["customer"] = form["email"]
            session["customer_name"] = form["name"]
            return redirect(url_for("index"))
    return render_template("signup.html", errors=errors, form=form)


@app.route("/account/login", methods=["GET", "POST"])
def account_login():
    error = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        customer = find_customer(email)
        # same message whether the email is unknown or the password is wrong,
        # so nobody can use this page to find out who has an account
        if customer and check_password_hash(customer["Password hash"], password):
            session["customer"] = customer["Email"]
            session["customer_name"] = customer["Name"]
            return redirect(url_for("index"))
        error = "Email or password is incorrect."
    return render_template("account_login.html", error=error, email=email)


@app.route("/account/logout", methods=["POST"])
def account_logout():
    session.pop("customer", None)
    session.pop("customer_name", None)
    return redirect(url_for("index"))


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
            order_data["quantity"] = int(request.form.get("quantity", ""))
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
    row = paid_row(request.args.get("session_id", ""))
    if row is None:
        return redirect(url_for("index"))
    set_paid(row)
    order = session.get("last_order")
    if not order:
        return redirect(url_for("index"))
    return render_template("thanks.html", order=order)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect(url_for("admin"))  # already logged in: go straight to deliveries
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

    month = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        month_label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")  # "December 2026"
    except ValueError:
        return redirect(url_for("admin"))  # bad month in the URL: show this month instead

    orders = get_orders_for_month(month)
    delivered = sum(1 for o in orders if o["Delivered"] == "Yes")
    return render_template(
        "admin.html",
        orders=orders,
        month=month,
        month_label=month_label,
        delivered=delivered,
    )


@app.route("/admin/delivered", methods=["POST"])
def mark_delivered():
    if not session.get("admin"):
        return redirect(url_for("login"))

    row = int(request.form["row"])
    set_delivered(row, request.form["delivered"] == "Yes")
    return redirect(url_for("admin", month=request.form["month"]))


if __name__ == "__main__":
    app.run(debug=True)
