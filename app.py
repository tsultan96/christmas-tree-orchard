import os
import secrets
from datetime import date, datetime

import stripe
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from emails import send_alert, send_confirmation
from orders import (
    DOZEN_DISCOUNT, FLOCKING_PRICE, MAX_CART_ITEMS, PREMIUM_AFTER, PRICES, SPECIES,
    cart_total, delivered_trees, discount_factor, is_premium, item_cents, item_subtotal,
    size_label, tree_count, tree_name, validate_details, validate_item,
)
from payments import create_checkout, paid_rows
from sheets import (
    create_customer, find_customer, get_orders_for_customer, get_orders_for_month,
    new_order_id, save_cart_order, set_delivered, set_paid,
)


load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


app.add_template_filter(tree_name)
app.add_template_filter(size_label)


@app.context_processor
def tree_info():
    """Every template can use `species` (names, descriptions, pictures of the trees we sell)."""
    return {"species": SPECIES}


@app.route("/")
def index():
    return render_template(
        "index.html",
        prices=PRICES,
        flocking_price=FLOCKING_PRICE,
        dozen_discount=DOZEN_DISCOUNT,
    )


def cart_summary(items, premium):
    """Everything the cart and checkout pages show about prices."""
    factor = discount_factor(items, premium)
    return {
        "lines": [{"item": item, "subtotal": item_subtotal(item) * 100, "cents": item_cents(item, factor)} for item in items],
        "trees": tree_count(items),
        "dozen": tree_count(items) >= 12,
        "premium": premium,
        "before": sum(item_subtotal(item) * 100 for item in items),
        "total": cart_total(items, premium),
    }


@app.route("/cart")
def cart():
    items = session.get("cart", [])
    return render_template("cart.html", items=items, summary=cart_summary(items, current_customer_is_premium()))


@app.route("/cart/remove", methods=["POST"])
def cart_remove():
    items = session.get("cart", [])
    try:
        index = int(request.form.get("index", ""))
    except ValueError:
        return redirect(url_for("cart"))
    if 0 <= index < len(items):
        items = items[:index] + items[index + 1:]
        session["cart"] = items
    return redirect(url_for("cart"))


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


@app.route("/account")
def my_orders():
    if not session.get("customer"):
        return redirect(url_for("account_login"))

    orders = get_orders_for_customer(session["customer"])
    return render_template(
        "my_orders.html",
        orders=orders,
        delivered=delivered_trees(orders),
        premium=is_premium(orders),
        premium_after=PREMIUM_AFTER,
    )


@app.route("/account/logout", methods=["POST"])
def account_logout():
    session.pop("customer", None)
    session.pop("customer_name", None)
    return redirect(url_for("index"))


def current_customer_is_premium():
    """Premium only counts for a LOGGED-IN customer, checked against the trees in their own delivered orders."""
    email = session.get("customer")
    return bool(email) and is_premium(get_orders_for_customer(email))


@app.route("/order", methods=["GET", "POST"])
def order():
    """Pick a tree, size, quantity and flocking, then add it to the cart."""
    if request.method == "POST":
        item = {
            "species": request.form.get("species", "").strip(),
            "tree_size": request.form.get("tree_size", "").strip(),
            "flocked": request.form.get("flocked") == "yes",
        }
        try:
            item["quantity"] = int(request.form.get("quantity", ""))
        except ValueError:
            item["quantity"] = None

        errors = validate_item(item)
        items = session.get("cart", [])
        if len(items) >= MAX_CART_ITEMS:
            errors.append(f"Your cart can hold up to {MAX_CART_ITEMS} different trees.")
        if errors:
            return render_template("order.html", errors=errors, form=item)

        # assign a new list (not .append) so Flask notices the session changed
        session["cart"] = items + [item]
        return redirect(url_for("cart"))
    return render_template("order.html", form={})


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    """Contact, delivery and payment for everything in the cart."""
    items = session.get("cart", [])
    if not items:
        return redirect(url_for("cart"))
    premium = current_customer_is_premium()
    summary = cart_summary(items, premium)

    if request.method == "POST":
        details = {
            field: request.form.get(field, "").strip()
            for field in ["name", "email", "phone", "street", "apt", "city", "zip",
                          "delivery_date", "time_window", "delivery_notes", "payment"]
        }
        if session.get("customer"):
            # always file a member's order under their account email, whatever was typed,
            # so it shows up in My orders and counts toward Premium
            details["email"] = session["customer"]

        errors = validate_details(details)
        if errors:
            return render_template("checkout.html", errors=errors, form=details, summary=summary,
                                   today=date.today().isoformat())

        details["order_id"] = new_order_id()
        rows = save_cart_order(details, items, details["order_id"])
        try:
            send_alert(details, items, summary["total"])
            if details["email"]:
                send_confirmation(details, items, summary["total"])
        except Exception as e:
            print(f"Alert email failed: {e}")

        order = {**details, "items": items, "total": summary["total"], "premium": premium}
        if details["payment"] == "card":
            session["last_order"] = order
            return redirect(create_checkout(items, rows, premium))  # cart is kept until payment succeeds
        session["cart"] = []
        return render_template("thanks.html", order=order)

    form = {}
    if session.get("customer"):
        customer = find_customer(session["customer"])
        if customer:
            form = {"name": customer["Name"], "email": customer["Email"], "phone": customer["Phone"]}
    return render_template("checkout.html", form=form, summary=summary, today=date.today().isoformat())


@app.route("/paid")
def paid():
    rows = paid_rows(request.args.get("session_id", ""))
    if rows is None:
        return redirect(url_for("index"))
    set_paid(rows)
    session["cart"] = []
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
            # staff and customer logins never mix in one browser
            session.pop("customer", None)
            session.pop("customer_name", None)
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
