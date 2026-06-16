"""Lightweight bilingual text heuristics (AR-EG / EN).

These power language detection, Arabizi normalization, intent guessing and
quantity extraction. They keep the local (mock) path useful with no LLM and
double as cheap pre-processing in production.
"""
from __future__ import annotations

import re

from app.schemas.enums import Intent, Lang

_ARABIC_RE = re.compile(r"[؀-ۿ]")
_DIACRITICS_RE = re.compile(r"[ؗ-ًؚ-ْٰـ]")  # harakat + tatweel

# Egyptian / Arabic number words → int
NUM_WORDS: dict[str, int] = {
    "واحد": 1, "واحده": 1, "وحده": 1,
    "اتنين": 2, "اثنين": 2, "إتنين": 2,
    "تلاته": 3, "تلاتة": 3, "ثلاثة": 3, "ثلاث": 3,
    "اربعه": 4, "اربعة": 4, "أربعة": 4, "اربع": 4,
    "خمسه": 5, "خمسة": 5, "خمس": 5,
    "سته": 6, "ستة": 6, "ست": 6,
    "سبعه": 7, "سبعة": 7,
    "تمنيه": 8, "تمانية": 8,
    "تسعه": 9, "تسعة": 9,
    "عشره": 10, "عشرة": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_WESTERN_TO_ARABIC_DIGIT = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

INTENT_KEYWORDS: dict[Intent, list[str]] = {
    Intent.RESERVE: ["احجز", "حجز", "طاوله", "طاولة", "ترابيزه", "ترابيزة", "book", "reserve", "table", "reservation"],
    Intent.TRACK: ["فين الاوردر", "فين الأوردر", "الاوردر فين", "وصل", "اوردري", "track", "where is my order", "status", "وصلت"],
    Intent.PAY: ["ادفع", "أدفع", "دفع", "تأكيد الاوردر", "تاكيد", "اكد", "checkout", "pay", "confirm order", "كاش", "فيزا", "كارت"],
    Intent.SUPPORT: ["شكوى", "مشكله", "مشكلة", "مساعده", "مساعدة", "كلمني", "اكلم", "موظف", "خدمة العملاء", "خدمه العملاء", "ممثل", "complaint", "help", "support", "agent", "human", "customer service"],
    Intent.ORDER: ["عايز", "عاوز", "اطلب", "أطلب", "هات", "ضيف", "اضيف", "order", "want", "add", "get me", "i'll have"],
    Intent.BROWSE: ["المنيو", "المينو", "قائمه", "قائمة", "عندكم ايه", "في ايه", "menu", "what do you have", "options", "show me"],
}


def has_arabic(text: str) -> bool:
    return bool(_ARABIC_RE.search(text))


def detect_lang(text: str) -> Lang:
    return Lang.AR if has_arabic(text) else Lang.EN


def normalize_arabizi(text: str) -> str:
    """Light normalization: strip diacritics/tatweel, unify alef/ya/ta-marbuta,
    convert Arabic-Indic digits to western. (Full Arabizi→Arabic is a prod model.)"""
    t = text.translate(_WESTERN_TO_ARABIC_DIGIT)
    t = _DIACRITICS_RE.sub("", t)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    t = t.replace("ى", "ي").replace("ة", "ه")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_quantity(text: str, default: int = 1) -> int:
    """Best-effort quantity from digits or number words."""
    t = text.translate(_WESTERN_TO_ARABIC_DIGIT)
    m = re.search(r"\b(\d{1,2})\b", t)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 50 else default
    for word, n in NUM_WORDS.items():
        if word in t:
            return n
    return default


SMALLTALK_KEYWORDS = [
    "هاي", "هلا", "اهلا", "ازيك", "ازيكم", "ازي", "السلام", "صباح", "مساء",
    "شكر", "متشكر", "تسلم", "باي", "عامل ايه",
    "hi", "hello", "hey", "thanks", "thank", "bye", "good morning", "good evening",
]


def guess_intent(text: str) -> Intent:
    """Keyword-based intent. Order matters: more specific intents win.

    A bare dish name ("شاورما فراخ") has no order verb, so anything that isn't a
    recognized intent or a greeting defaults to ORDER — the menu lookup then
    either fulfills it or reports it's not found.
    """
    t = normalize_arabizi(text.lower())
    for intent in (Intent.PAY, Intent.TRACK, Intent.RESERVE, Intent.SUPPORT, Intent.BROWSE):
        for kw in INTENT_KEYWORDS[intent]:
            if normalize_arabizi(kw.lower()) in t:
                return intent
    for kw in INTENT_KEYWORDS[Intent.ORDER]:
        if normalize_arabizi(kw.lower()) in t:
            return Intent.ORDER
    for kw in SMALLTALK_KEYWORDS:
        if normalize_arabizi(kw.lower()) in t:
            return Intent.SMALLTALK
    # default: treat remaining text as a food request (bare dish name)
    return Intent.ORDER


_ORDER_STOP = {
    "عايز", "عاوز", "اطلب", "هات", "ضيف", "اضيف", "لو", "سمحت", "فضلك", "محتاج",
    "want", "order", "add", "get", "me", "a", "an", "the", "please", "i", "id", "like",
}
# split an order utterance into line items on connectors (handles attached و)
_SEG_SPLIT = re.compile(r"\s+و|،|,|\s+مع\s+|\s+and\s+|\s+plus\s+")
# modifier phrases: "بدون طرشي" / "من غير بصل" / "زيادة جبنة" / "no onions"
_MOD_RE = re.compile(
    r"(بدون|من غير|بلا|زياده|زيادة|اكسترا|extra|no|without)\s+([^\sو،,]+(?:\s+[^\sو،,]+)?)"
)


def parse_order_lines(text: str) -> list[dict]:
    """Parse free-text into order lines: ``[{qty, phrase, modifiers}]``.

    Handles multi-item ("شاورما وبطاطس وكولا"), quantities ("اتنين برجر")
    and modifiers ("برجر بدون مخلل"). Best-effort for the local/mock path;
    the production LLM planner handles the long tail.
    """
    t = normalize_arabizi(text)
    lines: list[dict] = []
    for seg in _SEG_SPLIT.split(t):
        seg = seg.strip()
        if not seg:
            continue
        qty = extract_quantity(seg, default=1)
        mods: list[str] = []
        phrase = _MOD_RE.sub(lambda m: mods.append(f"{m.group(1)} {m.group(2)}".strip()) or " ", seg)
        phrase = re.sub(r"\b\d+\b", " ", phrase)
        tokens = [w for w in phrase.split() if w not in _ORDER_STOP and w not in NUM_WORDS]
        phrase = " ".join(tokens).strip()
        if not phrase and not mods:
            continue
        lines.append({"qty": qty, "phrase": phrase, "modifiers": mods})
    return lines
