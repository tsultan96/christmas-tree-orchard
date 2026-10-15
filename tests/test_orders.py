from orders import order_total
import pytest


def test_two_five_foot_trees():
    data = {"tree_size": "5ft", "flocked": False, "quantity": 2}
    assert order_total(data) == 30000  # $300.00, in cents


def test_flocking_adds_25_per_tree():
    data = {"tree_size": "3ft", "flocked": True, "quantity": 1}
    assert order_total(data) == 12500  # $100 + $25


def test_dozen_and_premium_discounts_stack():
    data = {"tree_size": "3ft", "flocked": True, "quantity": 12}
    assert order_total(data) == 135000                 # 12 x $125, minus 10% dozen discount
    assert order_total(data, premium=True) == 128250   # and then 5% Premium on top
from orders import validate_order


def valid_order(**changes):
    """A complete order that passes validation. Pass changes to break one field on purpose."""
    order = {
        "species": "fraser_fir",
        "tree_size": "5ft",
        "quantity": 2,
        "flocked": False,
        "name": "Test Customer",
        "phone": "5555555555",
        "street": "1 Main St",
        "city": "Arlington",
        "delivery_date": "2099-12-01",
        "time_window": "morning",
        "payment": "cash",
    }
    order.update(changes)
    return order


def test_valid_order_has_no_errors():
    assert validate_order(valid_order()) == []


def test_past_delivery_date_is_rejected():
    errors = validate_order(valid_order(delivery_date="2020-01-01"))
    assert any("can't be in the past" in e for e in errors)
def test_zero_quantity_is_rejected():
    errors = validate_order(valid_order(quantity=0))
    assert any ("quantity" in e for e in errors)
    