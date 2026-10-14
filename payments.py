"""Card payments through Stripe Checkout. The API key is set in app.py."""

import stripe
from flask import url_for

from orders import order_total


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


def paid_row(session_id):
    """Ask Stripe about this checkout. Return the sheet row if it was paid, else None."""
    try:
        checkout = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError:
        return None
    if checkout.payment_status != "paid":
        return None
    return int(checkout.metadata["row"])
