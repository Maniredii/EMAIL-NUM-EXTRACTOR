"""
Phone Number Extractor Module
Extracts, normalizes, sanitizes, and deduplicates phone numbers from resume text,
supporting international (+1, +91, +44, etc.), North American, Indian, and general formats.
"""
import re
from typing import List, Set, Optional

# Regex for common phone keywords indicating phone context
PHONE_CONTEXT_PREFIX = re.compile(
    r'(?:phone|tel|telephone|mobile|cell|contact|ph|m|whatsapp|call)[\s.:#-]*',
    re.IGNORECASE
)

# International formats with country code: +1, +91, +44, +61, etc.
INTERNATIONAL_PHONE_REGEX = re.compile(
    r'(?:\+|00)[1-9]\d{0,2}[\s.-]?(?:\(?\d{1,4}\)?[\s.-]?)?\d{1,4}[\s.-]?\d{1,4}(?:[\s.-]?\d{1,9})?'
)

# Standard North American format: (555) 010-1234, 555-010-1234, 555.010.1234, 1-555-010-1234
NORTH_AMERICA_REGEX = re.compile(
    r'(?:\+?1[\s.-]?)?\(?\b[1-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b'
)

# Indian mobile format: +91 98765 43210, 09876543210, 9876543210 (starts with 6-9)
INDIAN_PHONE_REGEX = re.compile(
    r'(?:(?:\+91|0)[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}\b'
)

# Generic phone with keyword context (e.g. "Tel: 555-0199" or "Mobile: 9876543210")
KEYWORD_PHONE_REGEX = re.compile(
    r'(?:phone|tel|telephone|mobile|cell|contact|ph|m|whatsapp)[\s.:#-]+(\+?[\d\s().-]{7,22})',
    re.IGNORECASE
)

# Common date ranges to reject (e.g. 2018 - 2022, 2019-2024)
DATE_RANGE_REGEX = re.compile(
    r'\b(?:19|20)\d{2}[\s.-]*(?:-|to|–|—)[\s.-]*(?:19|20)\d{2}\b',
    re.IGNORECASE
)


def is_valid_phone_candidate(raw: str) -> bool:
    """Checks whether the raw string is a genuine phone number and not a date/year/artifact."""
    digits = re.sub(r'\D', '', raw)
    num_digits = len(digits)

    # Valid phone numbers have between 10 and 15 digits (or 7 if local landline)
    if num_digits < 10 or num_digits > 15:
        return False

    # Check for all-identical digits (e.g., 0000000000, 1111111111)
    if len(set(digits)) == 1:
        return False

    # Check for simple sequential runs (e.g., 1234567890)
    if digits in "01234567890123456" or digits in "9876543210987654":
        return False

    # Check if raw string looks like a date range
    if DATE_RANGE_REGEX.search(raw):
        return False

    return True


def normalize_phone_number(raw_phone: str) -> Optional[str]:
    """
    Cleans and formats a phone number string into a clean, uniform presentation.
    Examples:
    - '+15550101234' -> '+1 (555) 010-1234'
    - '5550101234'   -> '(555) 010-1234'
    - '+919876543210'-> '+91 98765 43210'
    """
    if not raw_phone or not isinstance(raw_phone, str):
        return None

    cleaned = raw_phone.strip()
    strip_chars = ".,;:!?()[]{}<>'\"\\/|#- \t\n"
    cleaned = cleaned.strip(strip_chars)

    if not is_valid_phone_candidate(cleaned):
        return None

    digits = re.sub(r'\D', '', cleaned)
    has_plus = cleaned.startswith('+')

    # 1. US / Canada 10-digit number
    if len(digits) == 10 and not has_plus:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    # 2. US / Canada 11-digit number starting with 1
    if len(digits) == 11 and digits.startswith('1'):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    # 3. India 12-digit number starting with 91
    if len(digits) == 12 and digits.startswith('91'):
        return f"+91 {digits[2:7]} {digits[7:]}"

    # 4. India 11-digit starting with 0
    if len(digits) == 11 and digits.startswith('0') and digits[1] in '6789':
        return f"+91 {digits[1:6]} {digits[6:]}"

    # 5. UK 12-digit number starting with 44
    if len(digits) == 12 and digits.startswith('44'):
        return f"+44 {digits[2:6]} {digits[6:]}"

    # 6. General international format with '+'
    if has_plus:
        # Group gracefully
        return f"+{digits[:2]} {digits[2:6]} {digits[6:]}".strip()

    # Fallback to readable formatted string
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) > 10:
        return f"+{digits[:len(digits)-10]} {digits[-10:-7]} {digits[-7:-4]} {digits[-4:]}"

    return cleaned


def extract_phone_numbers_from_text(text: str) -> List[str]:
    """
    Extracts all unique, valid phone numbers from resume text in order of appearance.

    Args:
        text: String containing raw resume text.

    Returns:
        List of unique formatted phone number strings.
    """
    if not text or not isinstance(text, str):
        return []

    candidates: List[str] = []

    # 1. Check keyword-prefixed phones first (high precision)
    for m in KEYWORD_PHONE_REGEX.finditer(text):
        matched = m.group(1).strip()
        candidates.append(matched)

    # 2. Check international pattern
    for m in INTERNATIONAL_PHONE_REGEX.finditer(text):
        candidates.append(m.group(0).strip())

    # 3. Check North American pattern
    for m in NORTH_AMERICA_REGEX.finditer(text):
        candidates.append(m.group(0).strip())

    # 4. Check Indian mobile pattern
    for m in INDIAN_PHONE_REGEX.finditer(text):
        candidates.append(m.group(0).strip())

    # Deduplicate while preserving order
    unique_phones: List[str] = []
    seen: Set[str] = set()

    for item in candidates:
        norm = normalize_phone_number(item)
        if norm:
            digits = re.sub(r'\D', '', norm)
            # Normalize deduplication key across national/international formats
            if len(digits) == 11 and digits.startswith('1'):
                dedup_key = digits[1:]
            elif len(digits) == 12 and digits.startswith('91'):
                dedup_key = digits[2:]
            else:
                dedup_key = digits

            if dedup_key not in seen:
                seen.add(dedup_key)
                unique_phones.append(norm)

    return unique_phones
