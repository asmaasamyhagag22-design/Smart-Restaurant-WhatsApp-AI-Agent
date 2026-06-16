"""Unit tests for the bilingual text heuristics."""
from app.schemas.enums import Intent, Lang
from app.services.text import (
    detect_lang,
    extract_quantity,
    guess_intent,
    normalize_arabizi,
    parse_order_lines,
)


def test_detect_lang():
    assert detect_lang("عايز برجر") == Lang.AR
    assert detect_lang("I want a burger") == Lang.EN


def test_normalize_arabizi():
    assert normalize_arabizi("أكلة") == "اكله"
    assert normalize_arabizi("١٢٣") == "123"


def test_extract_quantity():
    assert extract_quantity("اتنين برجر") == 2
    assert extract_quantity("3 cola") == 3
    assert extract_quantity("برجر") == 1
    assert extract_quantity("١٠ شاورما") == 10


def test_guess_intent():
    assert guess_intent("عايز شاورما فراخ") == Intent.ORDER
    assert guess_intent("احجز ترابيزة") == Intent.RESERVE
    assert guess_intent("فين الأوردر؟") == Intent.TRACK
    assert guess_intent("عايزة اكلم حد من خدمة العملاء") == Intent.SUPPORT
    assert guess_intent("المنيو") == Intent.BROWSE


def test_parse_order_lines_multi():
    lines = parse_order_lines("عايز برجر لحمة وبطاطس وكوكا")
    phrases = [line["phrase"] for line in lines]
    assert len(lines) == 3
    assert any("برجر" in p for p in phrases)
    assert any("بطاطس" in p for p in phrases)


def test_parse_order_lines_modifier():
    lines = parse_order_lines("عايز برجر لحمة بدون مخلل")
    assert len(lines) == 1
    assert lines[0]["modifiers"]
    assert "بدون" in lines[0]["modifiers"][0]


def test_parse_order_lines_quantity():
    lines = parse_order_lines("اتنين شاورما فراخ")
    assert lines[0]["qty"] == 2
