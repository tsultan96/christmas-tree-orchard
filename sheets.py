"""Everything that reads or writes the Google Sheet."""

import os
from datetime import datetime

import gspread
from werkzeug.security import generate_password_hash


DELIVERED_COLUMN = 17  # column Q in the orders tab: "Delivered"
PAID_COLUMN = 18       # column R in the orders tab: "Paid"


def get_book():
    client = gspread.service_account(filename=os.getenv("GOOGLE_CREDENTIALS_FILE"))
    return client.open_by_key(os.getenv("SHEET_ID"))


def get_sheet():
    return get_book().sheet1


def get_customers_sheet():
    return get_book().worksheet("Customers")


# ---------- orders ----------

def save_order(data):
    """Append the order as a new row and return its row number."""
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
    result = get_sheet().append_row(row)
    updated_range = result["updates"]["updatedRange"]   # e.g. "Sheet1!A23:R23"
    return int(updated_range.split("!")[1].split(":")[0][1:])


TIME_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}


def get_orders_for_month(month):
    """Return all orders delivering in this month ("2026-12"), sorted by date and time window."""
    orders = get_sheet().get_all_records(numericise_ignore=["all"])
    result = []
    for row_number, order in enumerate(orders, start=2):
        if order["Delivery date"].startswith(month + "-"):
            order["row"] = row_number
            result.append(order)
    result.sort(key=lambda o: (o["Delivery date"], TIME_ORDER.get(o["Time window"], 9)))
    return result


def set_delivered(row, delivered):
    get_sheet().update_cell(row, DELIVERED_COLUMN, "Yes" if delivered else "No")


def set_paid(row):
    get_sheet().update_cell(row, PAID_COLUMN, "Yes")


# ---------- customers ----------

def find_customer(email):
    """Return the customer row for this email, or None if there's no account."""
    for customer in get_customers_sheet().get_all_records(numericise_ignore=["all"]):
        if customer["Email"] == email:
            return customer
    return None


def create_customer(email, name, phone, password):
    get_customers_sheet().append_row([
        email,
        name,
        phone,
        generate_password_hash(password),
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ])
