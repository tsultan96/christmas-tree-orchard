from orders import cart_total, describe_item, order_total, size_label, tree_name, validate_details, validate_item
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
    


def test_tree_name_and_size_label():
    assert tree_name("douglas_fir") == "Douglas fir"
    assert tree_name("something_new") == "something_new"   # unknown values pass through
    assert size_label("12ft") == "12 ft"


# ---------- cart ----------

FRASER_8 = {"species": "fraser_fir", "tree_size": "5ft", "quantity": 8, "flocked": False}       # 8 x $150 = $1200
SPRUCE_4 = {"species": "norway_spruce", "tree_size": "3ft", "quantity": 4, "flocked": True}     # 4 x $125 = $500


def test_cart_under_a_dozen_has_no_discount():
    assert cart_total([FRASER_8]) == 120000


def test_dozen_discount_counts_every_tree_in_the_cart():
    # 8 + 4 = 12 trees across two lines -> 10% off everything: $1700 -> $1530
    assert cart_total([FRASER_8, SPRUCE_4]) == 153000


def test_premium_stacks_with_cart_dozen_discount():
    # $1700 x 0.9 x 0.95, rounded per line: $1026.00 + $427.50
    assert cart_total([FRASER_8, SPRUCE_4], premium=True) == 145350


def test_bad_cart_item_is_rejected():
    errors = validate_item({"species": "palm_tree", "tree_size": "5ft", "quantity": 0, "flocked": False})
    assert any("tree from the list" in e for e in errors)
    assert any("quantity" in e for e in errors)


def test_checkout_details_need_a_name():
    errors = validate_details(valid_order(name=""))
    assert any("name" in e for e in errors)


def test_describe_item():
    assert describe_item(SPRUCE_4) == "4 x Norway spruce, 3 ft, flocked"
