"""Card payments through Stripe Checkout. The API key is set in app.py."""

import stripe
from flask import url_for

from orders import describe_item, discount_factor, item_cents


def create_checkout(items, rows, premium=False):
    """Create one Stripe Checkout page for the whole cart and return its URL."""
    factor = discount_factor(items, premium)
    line_items = [{
        "price_data": {
            "currency": "usd",
            "unit_amount": item_cents(item, factor),   # this line's price after discounts
            "product_data": {"name": describe_item(item)},
        },
        "quantity": 1,
    } for item in items]

    checkout = stripe.checkout.Session.create(
        mode="payment",
        metadata={"rows": ",".join(str(r) for r in rows)},   # which sheet rows to mark paid
        line_items=line_items,
        success_url=url_for("paid", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_for("cart", _external=True),           # back to the cart, still full
    )
    return checkout.url


def paid_rows(session_id):
    """Ask Stripe about this checkout. Return its sheet rows if it was paid, else None."""
    try:
        checkout = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError:
        return None
    if checkout.payment_status != "paid":
        return None
    return [int(r) for r in checkout.metadata["rows"].split(",")]
