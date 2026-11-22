"""
Email Extractor Module
Extracts, normalizes, sanitizes, and deduplicates email addresses from text.
"""
import re
from typing import List, Set, Optional

# Primary regex for email detection
# Matches user@domain.tld with standard character sets
BASE_EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Mailto link pattern
MAILTO_REGEX = re.compile(
    r'mailto:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    re.IGNORECASE
)

# Common invalid file extension "TLDs" that occur as false positives (e.g. image@2x.png)
INVALID_TLDS = {
    "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "tiff", "ico",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "zip", "rar",
    "css", "js", "json", "html", "htm", "xml", "txt", "exe", "bin",
    "mp3", "mp4", "wav", "avi", "mov"
}

# Obfuscation replacement patterns
OBFUSCATION_PATTERNS = [
    (re.compile(r'\s*(\[at\]|\(at\)|\{at\}|\[AT\]|\(AT\)|\{AT\})\s*', re.IGNORECASE), '@'),
    (re.compile(r'\s*(\[dot\]|\(dot\)|\{dot\}|\[DOT\]|\(DOT\)|\{DOT\})\s*', re.IGNORECASE), '.'),
]


def clean_obfuscation(text: str) -> str:
    """Pre-processes text to resolve common resume email obfuscation patterns."""
    processed = text
    for pattern, replacement in OBFUSCATION_PATTERNS:
        processed = pattern.sub(replacement, processed)
    return processed


def normalize_email(email_str: str) -> Optional[str]:
    """
    Sanitizes, trims punctuation, checks validity, and converts email to lowercase.
    Returns normalized string or None if invalid.
    """
    if not email_str or not isinstance(email_str, str):
        return None

    # Strip whitespace and common wrappers
    cleaned = email_str.strip()
    
    # Trim leading/trailing surrounding punctuation
    strip_chars = ".,;:!?()[]{}<>'\"\\/|"
    cleaned = cleaned.strip(strip_chars)

    # Basic length checks according to RFC specifications
    if len(cleaned) < 5 or len(cleaned) > 254:
        return None

    if "@" not in cleaned:
        return None

    parts = cleaned.split("@")
    if len(parts) != 2:
        return None

    local_part, domain_part = parts[0], parts[1]

    # Validate local part
    if not local_part or len(local_part) > 64:
        return None

    # Local part shouldn't start or end with a dot
    if local_part.startswith(".") or local_part.endswith("."):
        return None

    # Validate domain part
    if not domain_part or "." not in domain_part:
        return None

    domain_parts = domain_part.split(".")
    tld = domain_parts[-1].lower()

    # TLD must be purely alphabetical and at least 2 chars
    if not tld.isalpha() or len(tld) < 2:
        return None

    # Check for invalid media/file TLDs
    if tld in INVALID_TLDS:
        return None

    # Check for consecutive dots in domain
    if ".." in domain_part:
        return None

    # Domain label validations
    for label in domain_parts:
        if not label or len(label) > 63:
            return None
        if label.startswith("-") or label.endswith("-"):
            return None
        # Labels must be alphanumeric + hyphens
        if not re.match(r'^[a-zA-Z0-9-]+$', label):
            return None

    # Normalized lowercase email
    return f"{local_part.lower()}@{domain_part.lower()}"


def extract_emails_from_text(text: str) -> List[str]:
    """
    Extracts all unique, valid email addresses from text in preserved order of appearance.

    Args:
        text: String containing raw resume text.

    Returns:
        List of unique valid lowercase email addresses.
    """
    if not text or not isinstance(text, str):
        return []

    # 1. First extract mailto: addresses if present
    mailto_matches = MAILTO_REGEX.findall(text)

    # 2. Pre-process text for obfuscation
    cleaned_text = clean_obfuscation(text)

    # 3. Find standard regex matches
    raw_matches = BASE_EMAIL_REGEX.findall(cleaned_text)

    all_raw = mailto_matches + raw_matches

    # 4. Normalize and deduplicate maintaining order
    unique_emails: List[str] = []
    seen: Set[str] = set()

    for item in all_raw:
        normalized = normalize_email(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_emails.append(normalized)

    return unique_emails


def format_emails_for_client(emails: List[str], separator: str = "; ") -> str:
    """
    Formats a list of email addresses with the specified separator.
    - Semicolon ('; ') for Outlook / Microsoft 365
    - Comma (', ') for Gmail / Apple Mail
    """
    if not emails:
        return ""
    return separator.join(emails)


def slice_emails_into_batches(emails: List[str], batch_size: int = 50) -> List[dict]:
    """
    Slices a list of email addresses into manageable batches to prevent email spam flags
    and avoid provider recipient limits.

    Returns a list of batch dictionaries:
    [
        {
            "batch_number": 1,
            "start_index": 1,
            "end_index": 50,
            "total_in_batch": 50,
            "emails": [...],
            "outlook_str": "a@b.com; c@d.com...",
            "gmail_str": "a@b.com, c@d.com..."
        },
        ...
    ]
    """
    if not emails:
        return []

    if batch_size <= 0:
        batch_size = 50

    batches = []
    total = len(emails)

    for i in range(0, total, batch_size):
        chunk = emails[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        start_idx = i + 1
        end_idx = min(i + len(chunk), total)

        batches.append({
            "batch_number": batch_num,
            "start_index": start_idx,
            "end_index": end_idx,
            "total_in_batch": len(chunk),
            "emails": chunk,
            "outlook_str": format_emails_for_client(chunk, separator="; "),
            "gmail_str": format_emails_for_client(chunk, separator=", ")
        })

    return batches
