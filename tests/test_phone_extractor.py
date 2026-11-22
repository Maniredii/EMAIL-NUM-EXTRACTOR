"""
Tests for core/phone_extractor.py
"""
import pytest
from core.phone_extractor import (
    extract_phone_numbers_from_text,
    normalize_phone_number,
    is_valid_phone_candidate
)


class TestPhoneExtractor:

    def test_north_american_formats(self):
        # Various standard US/Canada representations
        texts = [
            ("Call me at (555) 010-1234 today.", "(555) 010-1234"),
            ("Phone: 555-010-1234.", "(555) 010-1234"),
            ("Direct line: 555.010.1234", "(555) 010-1234"),
            ("Contact: +1 (555) 010-1234", "+1 (555) 010-1234"),
            ("Cell: +1-555-010-1234", "+1 (555) 010-1234"),
        ]
        for text, expected in texts:
            result = extract_phone_numbers_from_text(text)
            assert len(result) >= 1
            assert expected in result

    def test_indian_phone_formats(self):
        text = "Contact: +91 98765 43210 or alternate mobile: 9876543210"
        result = extract_phone_numbers_from_text(text)
        assert len(result) >= 1
        assert "+91 98765 43210" in result

    def test_international_formats(self):
        text = "London office: +44 20 7946 0958, Sydney: +61 412 345 678"
        result = extract_phone_numbers_from_text(text)
        assert len(result) == 2
        assert any("+44" in p for p in result)
        assert any("+61" in p for p in result)

    def test_keyword_context_extraction(self):
        text = "Candidate resume. Tel: (555) 234-5678, Email: test@dev.com"
        result = extract_phone_numbers_from_text(text)
        assert "(555) 234-5678" in result

    def test_date_range_rejection(self):
        text = """
        Experience:
        Senior Software Engineer (2018 - 2022)
        Previous Role (2014 to 2018)
        Education:
        B.S. Computer Science (2010 – 2014)
        """
        result = extract_phone_numbers_from_text(text)
        assert len(result) == 0

    def test_invalid_numbers_rejection(self):
        text = """
        0000000000
        1111111111
        1234567890
        9876543210987654
        12345
        """
        result = extract_phone_numbers_from_text(text)
        assert len(result) == 0

    def test_deduplication(self):
        text = "Mobile: (555) 010-1234. Again: 555-010-1234 or +1 (555) 010-1234"
        result = extract_phone_numbers_from_text(text)
        # Should deduplicate to the same core number
        assert len(result) == 1

    def test_normalize_helper(self):
        assert normalize_phone_number("5550101234") == "(555) 010-1234"
        assert normalize_phone_number("+15550101234") == "+1 (555) 010-1234"
        assert normalize_phone_number("+919876543210") == "+91 98765 43210"
        assert normalize_phone_number("invalid-phone") is None
        assert normalize_phone_number("2018 - 2022") is None
