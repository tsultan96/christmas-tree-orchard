"""Business rules for tree orders: what's required, what things cost."""

from datetime import date


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

SPECIES = {
    "fraser_fir": {"name": "Fraser fir", "about": "Soft needles, great needle retention", "image": "trees/fraser-fir.webp"},
    "douglas_fir": {"name": "Douglas fir", "about": "Full shape and a sweet scent", "image": "trees/douglas-fir.webp"},
    "white_pine": {"name": "White pine", "about": "Long, soft needles and a light look", "image": "trees/white-pine.webp"},
    "norway_spruce": {"name": "Norway spruce", "about": "Classic shape with sturdy branches", "image": "trees/norway-spruce.webp"},
}

PRICES = {
    "3ft": 100,
    "5ft": 150,
    "8ft": 200,
    "12ft": 250,
}
FLOCKING_PRICE = 25
DOZEN_DISCOUNT = 0.10

PREMIUM_AFTER = 10        # delivered orders needed to become Premium
PREMIUM_DISCOUNT = 0.05   # off every order after that


def delivered_count(orders):
    """How many of these orders (rows from the sheet) were actually delivered."""
    return sum(1 for o in orders if o["Delivered"] == "Yes")


def is_premium(orders):
    return delivered_count(orders) >= PREMIUM_AFTER


def validate_order(data):
    errors = []

    for field, label in REQUIRED_FIELDS.items():
        if data[field] == "":
            errors.append(f"Please enter {label}.")

    if data["species"] and data["species"] not in SPECIES:
        errors.append("Please choose a tree from the list.")

    if data["tree_size"] and data["tree_size"] not in PRICES:
        errors.append("Please choose a tree size from the list.")

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


def order_total(data, premium=False):
    """Return the order total in cents, calculated from our own PRICES.

    The dozen discount (one order of 12+) and the Premium discount (lifetime loyalty)
    are separate rewards, so both apply.
    """
    per_tree = PRICES[data["tree_size"]]
    if data["flocked"]:
        per_tree += FLOCKING_PRICE
    total = per_tree * data["quantity"]
    if data["quantity"] >= 12:
        total = total * (1 - DOZEN_DISCOUNT)
    if premium:
        total = total * (1 - PREMIUM_DISCOUNT)
    return round(total * 100)
