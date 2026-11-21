"""
Tests for core/pdf_reader.py
"""
import os
import tempfile
import fitz
import pytest
from core.pdf_reader import extract_text_from_file, extract_text_from_pdf


class TestPdfReader:

    def test_extract_normal_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "test_resume.pdf")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 72), "John Doe\nSoftware Engineer\nEmail: john.doe@techcorp.com\nPhone: 555-0199")
            doc.save(pdf_path)
            doc.close()

            res = extract_text_from_pdf(pdf_path)
            assert res["status"] == "Completed"
            assert "john.doe@techcorp.com" in res["text"]
            assert res["page_count"] == 1
            assert res["extraction_method"] == "Text"

    def test_extract_multipage_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "multi_page.pdf")
            doc = fitz.open()
            p1 = doc.new_page()
            p1.insert_text((50, 72), "Page 1 info: Developer profile and summary.")
            p2 = doc.new_page()
            p2.insert_text((50, 72), "Page 2 contact: recruiter.contact@enterprise.com")
            doc.save(pdf_path)
            doc.close()

            res = extract_text_from_pdf(pdf_path)
            assert res["status"] == "Completed"
            assert res["page_count"] == 2
            assert "recruiter.contact@enterprise.com" in res["text"]

    def test_extract_mailto_hyperlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "hyperlinked.pdf")
            doc = fitz.open()
            page = doc.new_page()
            rect = fitz.Rect(50, 50, 200, 100)
            page.insert_text((50, 72), "Click here to email me")
            # Insert mailto URI link
            page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": "mailto:clickable@portfolio.dev"})
            doc.save(pdf_path)
            doc.close()

            res = extract_text_from_pdf(pdf_path)
            assert res["status"] == "Completed"
            assert "clickable@portfolio.dev" in res["text"]

    def test_corrupted_pdf_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            corrupt_path = os.path.join(tmpdir, "corrupted.pdf")
            with open(corrupt_path, "wb") as f:
                f.write(b"GARBAGE_DATA_NOT_A_PDF_STREAM")

            res = extract_text_from_pdf(corrupt_path)
            assert res["status"] == "Failed"
            assert len(res["error_message"]) > 0

    def test_encrypted_pdf_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            enc_path = os.path.join(tmpdir, "protected.pdf")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 72), "Secret content: secret@cia.gov")
            # Encrypt with password
            doc.save(
                enc_path,
                encryption=fitz.PDF_ENCRYPT_AES_256,
                owner_pw="P@ssw0rd99",
                user_pw="P@ssw0rd99"
            )
            doc.close()

            res = extract_text_from_pdf(enc_path)
            assert res["status"] == "Failed"
            assert "password protected" in res["error_message"].lower()

    def test_empty_scanned_pdf_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_path = os.path.join(tmpdir, "empty_scan.pdf")
            doc = fitz.open()
            doc.new_page()  # blank page without text
            doc.save(empty_path)
            doc.close()

            res = extract_text_from_pdf(empty_path, enable_ocr=False)
            assert res["status"] == "Completed"
            assert res["is_scanned"] is True
            assert "Scanned" in res["extraction_method"] or "Low/Empty" in res["extraction_method"]

    def test_txt_file_extraction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = os.path.join(tmpdir, "resume.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("Candidate text resume. Contact: plain@textformat.com")

            res = extract_text_from_file(txt_path)
            assert res["status"] == "Completed"
            assert "plain@textformat.com" in res["text"]
