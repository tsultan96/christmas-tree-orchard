"""Business rules for tree orders: what's required, what things cost."""

from datetime import date


ITEM_FIELDS = {
    "species": "a tree type",
    "tree_size": "a tree size",
}

DETAIL_FIELDS = {
    "name": "your name",
    "phone": "your phone number",
    "street": "your street address",
    "city": "your city",
    "delivery_date": "a delivery date",
    "time_window": "a delivery time",
    "payment": "a payment method",
}

REQUIRED_FIELDS = {**ITEM_FIELDS, **DETAIL_FIELDS}

MAX_CART_ITEMS = 20       # different tree lines in one cart

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


def tree_name(value):
    """'douglas_fir' -> 'Douglas fir'. Unknown values are shown as they are."""
    return SPECIES.get(value, {}).get("name", value)


def size_label(value):
    """'5ft' -> '5 ft'."""
    return value[:-2] + " ft" if value.endswith("ft") else value


def describe_item(item):
    """'2 x Douglas fir, 8 ft, flocked' - used on Stripe's page and in emails."""
    text = f"{item['quantity']} x {tree_name(item['species'])}, {size_label(item['tree_size'])}"
    return text + (", flocked" if item["flocked"] else "")


PREMIUM_AFTER = 10        # delivered TREES (lifetime, across all orders) needed to become Premium
PREMIUM_DISCOUNT = 0.05   # off every order after that


def delivered_trees(orders):
    """Total number of trees in this customer's delivered orders (rows from the sheet)."""
    total = 0
    for o in orders:
        if o["Delivered"] == "Yes":
            try:
                total += int(o["Quantity"])
            except ValueError:
                pass  # a hand-edited cell like "two" shouldn't break the page
    return total


def is_premium(orders):
    return delivered_trees(orders) >= PREMIUM_AFTER


def validate_item(item):
    """Check one cart item: which tree, what size, how many."""
    errors = []
    for field, label in ITEM_FIELDS.items():
        if item[field] == "":
            errors.append(f"Please enter {label}.")

    if item["species"] and item["species"] not in SPECIES:
        errors.append("Please choose a tree from the list.")

    if item["tree_size"] and item["tree_size"] not in PRICES:
        errors.append("Please choose a tree size from the list.")

    if item["quantity"] is None or not 1 <= item["quantity"] <= 50:
        errors.append("Please enter a quantity between 1 and 50.")
    return errors


def validate_details(data):
    """Check the checkout details: contact, address, delivery and payment."""
    errors = []
    for field, label in DETAIL_FIELDS.items():
        if data[field] == "":
            errors.append(f"Please enter {label}.")

    if data["delivery_date"]:
        try:
            chosen_date = date.fromisoformat(data["delivery_date"])
        except ValueError:
            errors.append("Please enter a valid delivery date.")
        else:
            if chosen_date < date.today():
                errors.append("The delivery date can't be in the past.")
    return errors


def validate_order(data):
    """A single-tree order: the item checks plus the checkout checks."""
    return validate_item(data) + validate_details(data)


def item_subtotal(item):
    """Price of one cart line in dollars, before any discount."""
    per_tree = PRICES[item["tree_size"]]
    if item["flocked"]:
        per_tree += FLOCKING_PRICE
    return per_tree * item["quantity"]


def tree_count(items):
    return sum(item["quantity"] for item in items)


def discount_factor(items, premium=False):
    """What fraction of the price is paid after discounts.

    The dozen discount (12+ trees in this cart) and the Premium discount (lifetime loyalty)
    are separate rewards, so both apply.
    """
    factor = 1.0
    if tree_count(items) >= 12:
        factor *= 1 - DOZEN_DISCOUNT
    if premium:
        factor *= 1 - PREMIUM_DISCOUNT
    return factor


def item_cents(item, factor):
    """Price of one cart line in cents, after discounts."""
    return round(item_subtotal(item) * factor * 100)


def cart_total(items, premium=False):
    """Total for the whole cart in cents, calculated from our own PRICES."""
    factor = discount_factor(items, premium)
    return sum(item_cents(item, factor) for item in items)


def order_total(data, premium=False):
    """Total in cents for a single-tree order (a cart with one line)."""
    return cart_total([data], premium)
