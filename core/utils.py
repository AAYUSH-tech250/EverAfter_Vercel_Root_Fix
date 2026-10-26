import re
from urllib.parse import quote

from django.conf import settings


def normalize_phone(phone):
    """Digits only, with default country code added for 10-digit Indian-style numbers."""
    digits = re.sub(r"\D", "", phone or "")
    cc = settings.DEFAULT_COUNTRY_CODE
    if len(digits) == 10:
        digits = cc + digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = cc + digits[1:]
    return digits


def invite_text(guest, wedding, link):
    return (
        wedding.invite_message
        .replace("{name}", guest.name)
        .replace("{couple}", wedding.couple_names)
        .replace("{link}", link)
    )


def whatsapp_url(guest, wedding, link):
    number = normalize_phone(guest.phone)
    base = f"https://wa.me/{number}" if number else "https://wa.me/"
    return f"{base}?text={quote(invite_text(guest, wedding, link))}"
