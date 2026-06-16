"""Money formatting + cart math (price correctness is a hard requirement)."""
from app.schemas.domain import Cart, CartItem, Modifier, format_money
from app.schemas.enums import Lang


def test_format_money():
    assert format_money(8500, Lang.AR) == "85 ج"
    assert format_money(8550, Lang.AR) == "85.50 ج"
    assert format_money(11000, Lang.EN) == "110 EGP"


def test_cart_totals():
    cart = Cart(
        items=[
            CartItem(item_id="1", sku="A", name_ar="أ", name_en="A", qty=2, unit_price_cents=8500),
            CartItem(item_id="2", sku="B", name_ar="ب", name_en="B", qty=1, unit_price_cents=3500),
        ]
    )
    assert cart.subtotal_cents == 8500 * 2 + 3500
    assert cart.total_cents == cart.subtotal_cents


def test_modifier_price_delta():
    item = CartItem(
        item_id="1", sku="A", name_ar="مندي", name_en="Mandi", qty=1, unit_price_cents=24000,
        modifiers=[Modifier(name_ar="بدون مكسرات", name_en="no nuts", price_delta_cents=-1000)],
    )
    assert item.line_total_cents == 23000


def test_discount_and_delivery():
    cart = Cart(
        items=[CartItem(item_id="1", sku="A", name_ar="أ", name_en="A", qty=1, unit_price_cents=10000)],
        delivery_fee_cents=2000,
        discount_cents=3000,
    )
    assert cart.total_cents == 10000 + 2000 - 3000
