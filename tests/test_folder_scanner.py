"""
Tests for core/folder_scanner.py
"""
import os
import tempfile
import pytest
from core.folder_scanner import scan_folder, format_file_size


class TestFolderScanner:

    def test_format_file_size(self):
        assert format_file_size(500) == "500 B"
        assert format_file_size(2048) == "2.0 KB"
        assert format_file_size(1048576 * 3) == "3.00 MB"
        assert format_file_size(1073741824 * 2) == "2.00 GB"

    def test_invalid_path(self):
        res = scan_folder("Z:\\Non_Existent_Folder_12345\\Random")
        assert res["is_valid"] is False
        assert "does not exist" in res["error_message"]

    def test_empty_string_path(self):
        res = scan_folder("")
        assert res["is_valid"] is False
        assert "cannot be empty" in res["error_message"]

    def test_recursive_scanning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create root PDF
            root_pdf = os.path.join(tmpdir, "resume_root.pdf")
            with open(root_pdf, "wb") as f:
                f.write(b"%PDF-1.4 mock content")

            # Create subfolder 1
            sub1 = os.path.join(tmpdir, "Batch_A")
            os.makedirs(sub1)
            sub1_pdf = os.path.join(sub1, "candidate_a.pdf")
            with open(sub1_pdf, "wb") as f:
                f.write(b"%PDF-1.4 candidate A")

            # Create non-pdf file
            sub1_txt = os.path.join(sub1, "notes.txt")
            with open(sub1_txt, "w") as f:
                f.write("Some notes")

            # Create subfolder 2 nested
            sub2 = os.path.join(sub1, "Sub_Batch")
            os.makedirs(sub2)
            sub2_pdf = os.path.join(sub2, "candidate_b.pdf")
            with open(sub2_pdf, "wb") as f:
                f.write(b"%PDF-1.4 candidate B")

            # Recursive scan (default)
            res_rec = scan_folder(tmpdir, recursive=True, file_types=[".pdf"])
            assert res_rec["is_valid"] is True
            assert res_rec["total_files"] == 3
            assert res_rec["total_folders_searched"] >= 3

            filenames = [f["filename"] for f in res_rec["files"]]
            assert "resume_root.pdf" in filenames
            assert "candidate_a.pdf" in filenames
            assert "candidate_b.pdf" in filenames
            assert "notes.txt" not in filenames

            # Non-recursive scan
            res_non_rec = scan_folder(tmpdir, recursive=False, file_types=[".pdf"])
            assert res_non_rec["is_valid"] is True
            assert res_non_rec["total_files"] == 1
            assert res_non_rec["files"][0]["filename"] == "resume_root.pdf"

    def test_multi_extension_scanning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p_pdf = os.path.join(tmpdir, "doc1.pdf")
            p_docx = os.path.join(tmpdir, "doc2.docx")
            p_txt = os.path.join(tmpdir, "doc3.txt")
            p_jpg = os.path.join(tmpdir, "doc4.jpg")

            for p in (p_pdf, p_docx, p_txt, p_jpg):
                with open(p, "wb") as f:
                    f.write(b"content")

            res = scan_folder(tmpdir, recursive=False, file_types=[".pdf", ".docx", ".txt"])
            assert res["is_valid"] is True
            assert res["total_files"] == 3
            filenames = [f["filename"] for f in res["files"]]
            assert "doc1.pdf" in filenames
            assert "doc2.docx" in filenames
            assert "doc3.txt" in filenames
            assert "doc4.jpg" not in filenames
