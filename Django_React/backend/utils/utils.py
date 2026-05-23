from __future__ import annotations

import re


def to_local_09(phone_number: str) -> str:
    if not phone_number:
        raise ValueError("Phone number cannot be empty")

    phone_number = str(phone_number).strip()
    digits = "".join(ch for ch in phone_number if ch.isdigit())

    if digits.startswith("98") and len(digits) == 12:
        local_number = "0" + digits[2:]
    elif digits.startswith("0098") and len(digits) == 13:
        local_number = "0" + digits[4:]
    elif len(digits) == 10 and digits.startswith("9"):
        local_number = "0" + digits
    elif len(digits) == 11 and digits.startswith("09"):
        local_number = digits
    else:
        raise ValueError(f"Invalid phone number format: {phone_number}")

    if not re.match(r"^09\d{9}$", local_number):
        raise ValueError(f"Invalid Iranian phone number: {local_number}")

    return local_number

