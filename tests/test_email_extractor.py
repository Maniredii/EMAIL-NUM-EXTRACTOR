"""
Tests for core/email_extractor.py
"""
import pytest
from core.email_extractor import extract_emails_from_text, normalize_email


class TestEmailExtractor:

    def test_single_email_standard(self):
        text = "Contact me at candidate@example.com for job opportunities."
        result = extract_emails_from_text(text)
        assert result == ["candidate@example.com"]

    def test_case_normalization(self):
        text = "Reach out: John.DOE_99@Sub.Domain-Corp.ORG"
        result = extract_emails_from_text(text)
        assert result == ["john.doe_99@sub.domain-corp.org"]

    def test_multiple_emails(self):
        text = "Emails: primary.dev@gmail.com, alt_address@yahoo.co.uk, work@company.io"
        result = extract_emails_from_text(text)
        assert len(result) == 3
        assert "primary.dev@gmail.com" in result
        assert "alt_address@yahoo.co.uk" in result
        assert "work@company.io" in result

    def test_deduplication(self):
        text = "My email is test@company.com. Once again, contact test@company.com or TEST@COMPANY.COM"
        result = extract_emails_from_text(text)
        assert result == ["test@company.com"]

    def test_punctuation_stripping(self):
        # Emails in parentheses, angles, quotes, ending with periods or commas
        text = """
        References:
        <alice@wonderland.org>
        (bob@builder.net)
        "charlie@chocolate.factory.com",
        david@firm.com.
        eve@secret.com;
        """
        result = extract_emails_from_text(text)
        assert "alice@wonderland.org" in result
        assert "bob@builder.net" in result
        assert "charlie@chocolate.factory.com" in result
        assert "david@firm.com" in result
        assert "eve@secret.com" in result

    def test_obfuscated_emails(self):
        text = "Reach me at alex.smith [at] techcorp [dot] com or sara(at)domain.org"
        result = extract_emails_from_text(text)
        assert "alex.smith@techcorp.com" in result
        assert "sara@domain.org" in result

    def test_mailto_link(self):
        text = 'Click here: <a href="mailto:support@hr-portal.com">Send Email</a>'
        result = extract_emails_from_text(text)
        assert "support@hr-portal.com" in result

    def test_false_positives_rejection(self):
        # Images, style assets, invalid formats
        text = """
        profile_icon@2x.png
        banner_hero@3x.jpg
        vector@1x.svg
        invalid@domain..com
        bad@.com
        @emptyuser.com
        test@domain.123
        """
        result = extract_emails_from_text(text)
        assert len(result) == 0

    def test_empty_and_none_text(self):
        assert extract_emails_from_text("") == []
        assert extract_emails_from_text(None) == []
        assert extract_emails_from_text("   \n\t  ") == []

    def test_normalize_email_helper(self):
        assert normalize_email(" USER@DOMAIN.COM. ") == "user@domain.com"
        assert normalize_email("invalid-string") is None
        assert normalize_email("user@") is None
        assert normalize_email("@domain.com") is None
        assert normalize_email("user@domain.png") is None

    def test_format_emails_for_client(self):
        from core.email_extractor import format_emails_for_client
        emails = ["alex@corp.com", "bob@gmail.com", "carol@yahoo.com"]
        assert format_emails_for_client(emails, separator="; ") == "alex@corp.com; bob@gmail.com; carol@yahoo.com"
        assert format_emails_for_client(emails, separator=", ") == "alex@corp.com, bob@gmail.com, carol@yahoo.com"
        assert format_emails_for_client([]) == ""

    def test_slice_emails_into_batches(self):
        from core.email_extractor import slice_emails_into_batches
        # Test 120 emails with batch size 50 -> 3 batches: 50, 50, 20
        emails = [f"user{i}@test.com" for i in range(1, 121)]
        batches = slice_emails_into_batches(emails, batch_size=50)

        assert len(batches) == 3
        # Batch 1
        assert batches[0]["batch_number"] == 1
        assert batches[0]["start_index"] == 1
        assert batches[0]["end_index"] == 50
        assert batches[0]["total_in_batch"] == 50
        assert "user1@test.com" in batches[0]["outlook_str"]
        assert "user50@test.com" in batches[0]["outlook_str"]

        # Batch 2
        assert batches[1]["batch_number"] == 2
        assert batches[1]["start_index"] == 51
        assert batches[1]["end_index"] == 100
        assert batches[1]["total_in_batch"] == 50

        # Batch 3
        assert batches[2]["batch_number"] == 3
        assert batches[2]["start_index"] == 101
        assert batches[2]["end_index"] == 120
        assert batches[2]["total_in_batch"] == 20
        assert batches[2]["gmail_str"].startswith("user101@test.com, ")

    def test_slice_emails_edge_cases(self):
        from core.email_extractor import slice_emails_into_batches
        assert slice_emails_into_batches([]) == []
        
        # Fewer than batch size
        small = ["a@a.com", "b@b.com"]
        b_small = slice_emails_into_batches(small, batch_size=50)
        assert len(b_small) == 1
        assert b_small[0]["total_in_batch"] == 2
