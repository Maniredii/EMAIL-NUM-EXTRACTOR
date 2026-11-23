"""
End-to-End Batch Processor and Export Tests
"""
import os
import tempfile
import threading
import fitz
import pandas as pd
import pytest

from core.folder_scanner import scan_folder
from core.processor import BatchProcessor
from core.export_manager import ExportManager


class TestBatchProcessorAndExport:

    @pytest.fixture
    def sample_batch_dir(self):
        """Creates a realistic folder structure with mixed PDFs."""
        tmp = tempfile.TemporaryDirectory()
        base_dir = tmp.name

        # 1. Resume A: Single email
        doc_a = fitz.open()
        p_a = doc_a.new_page()
        p_a.insert_text((50, 72), "Candidate Alpha\nEmail: alpha@innovate.com")
        doc_a.save(os.path.join(base_dir, "resume_alpha.pdf"))
        doc_a.close()

        # 2. Resume B: Two emails
        doc_b = fitz.open()
        p_b = doc_b.new_page()
        p_b.insert_text((50, 72), "Candidate Beta\nPrimary: beta@company.org\nAlt: beta.personal@gmail.com")
        doc_b.save(os.path.join(base_dir, "resume_beta.pdf"))
        doc_b.close()

        # 3. Resume C: Shares email with Alpha (duplicate email across resumes)
        doc_c = fitz.open()
        p_c = doc_c.new_page()
        p_c.insert_text((50, 72), "Candidate Gamma (Co-author)\nEmail: alpha@innovate.com")
        doc_c.save(os.path.join(base_dir, "resume_gamma.pdf"))
        doc_c.close()

        # 4. Resume D: No emails in content
        doc_d = fitz.open()
        p_d = doc_d.new_page()
        p_d.insert_text((50, 72), "Candidate Delta\nPortfolio: https://github.com/delta\nNo email listed here.")
        doc_d.save(os.path.join(base_dir, "resume_delta.pdf"))
        doc_d.close()

        # 5. Corrupted file
        with open(os.path.join(base_dir, "resume_corrupt.pdf"), "wb") as f:
            f.write(b"CORRUPTED_NON_PDF_STREAM")

        # 6. Nested folder with a resume
        sub = os.path.join(base_dir, "Subfolder_Engineering")
        os.makedirs(sub)
        doc_e = fitz.open()
        p_e = doc_e.new_page()
        p_e.insert_text((50, 72), "Candidate Epsilon\nContact: epsilon@eng.net")
        doc_e.save(os.path.join(sub, "resume_epsilon.pdf"))
        doc_e.close()

        yield base_dir
        tmp.cleanup()

    def test_full_batch_pipeline(self, sample_batch_dir):
        # 1. Scan folder
        scan_res = scan_folder(sample_batch_dir, recursive=True, file_types=[".pdf"])
        assert scan_res["is_valid"] is True
        assert scan_res["total_files"] == 6

        # 2. Progress callback tracking
        callbacks_received = []

        def on_progress(p):
            callbacks_received.append(p["current_index"])

        # 3. Execute batch
        processor = BatchProcessor(
            files=scan_res["files"],
            enable_ocr=False,
            progress_callback=on_progress
        )
        result = processor.process()

        assert len(callbacks_received) == 6
        summary = result["summary"]
        assert summary["total_files"] == 6
        assert summary["processed_count"] == 6
        assert summary["failed_count"] == 1  # the corrupted file
        assert summary["no_email_count"] == 1  # resume_delta
        assert summary["completed_count"] == 4  # alpha, beta, gamma, epsilon

        # 4. Check Unique Emails deduplication
        # Unique emails expected:
        # alpha@innovate.com (found in resume_alpha and resume_gamma)
        # beta@company.org
        # beta.personal@gmail.com
        # epsilon@eng.net
        # Total unique: 4
        assert summary["unique_emails_count"] == 4

        df_unique = result["df_unique_emails"]
        assert len(df_unique) == 4
        assert "alpha@innovate.com" in df_unique["Email Address"].values
        
        # Verify alpha@innovate.com lists both resumes and count is 2
        alpha_row = df_unique[df_unique["Email Address"] == "alpha@innovate.com"].iloc[0]
        assert alpha_row["Number of Resumes"] == 2
        assert "resume_alpha.pdf" in alpha_row["Found in Resume(s)"]
        assert "resume_gamma.pdf" in alpha_row["Found in Resume(s)"]

        # 5. Check Resume Mapping
        df_mapping = result["df_resume_mapping"]
        assert len(df_mapping) == 6

        # Check corrupted file record
        corrupt_row = df_mapping[df_mapping["PDF Filename"] == "resume_corrupt.pdf"].iloc[0]
        assert corrupt_row["Status"] == "Failed"
        assert len(corrupt_row["Error Details"]) > 0

        # Check zero-emails record
        delta_row = df_mapping[df_mapping["PDF Filename"] == "resume_delta.pdf"].iloc[0]
        assert delta_row["Status"] in ("No Contacts Found", "No Emails Found")
        assert delta_row["Email Count"] == 0

        # 6. Test Exports
        with tempfile.TemporaryDirectory() as export_dir:
            save_res = ExportManager.save_all_to_directory(
                output_directory=export_dir,
                df_unique=df_unique,
                df_mapping=df_mapping,
                summary=summary,
                resume_results=result["resume_results"],
                df_unique_phones=result["df_unique_phones"]
            )

            assert save_res["success"] is True

            # Verify files exist on disk
            for expected_file in [
                "unique_emails.xlsx",
                "unique_emails.csv",
                "resume_email_mapping.xlsx",
                "resume_email_mapping.csv",
                "extraction_report.xlsx",
                "bcc_batches_outlook.txt",
                "bcc_batches_gmail.txt"
            ]:
                full_fpath = os.path.join(export_dir, expected_file)
                assert os.path.isfile(full_fpath)
                assert os.path.getsize(full_fpath) > 0

            # Verify reading back multi-sheet extraction_report.xlsx
            excel_path = os.path.join(export_dir, "extraction_report.xlsx")
            with pd.ExcelFile(excel_path) as xls:
                assert "Unique Emails" in xls.sheet_names
                assert "Resume Mapping" in xls.sheet_names
                assert "Summary" in xls.sheet_names
                assert "Failed Files" in xls.sheet_names

                df_back_unique = pd.read_excel(xls, sheet_name="Unique Emails")
                assert len(df_back_unique) == 4

                df_back_failed = pd.read_excel(xls, sheet_name="Failed Files")
                assert len(df_back_failed) == 1
                assert df_back_failed.iloc[0]["Filename"] == "resume_corrupt.pdf"

        # 7. Test Customized Excel Report (Selective fields and sheets)
        custom_cfg = {
            "include_unique_emails": True,
            "include_unique_phones": False,
            "include_resume_mapping": True,
            "include_summary": False,
            "include_failed_files": False,
            "mapping_columns": ["PDF Filename", "Extracted Emails", "Status"]
        }
        custom_buf = ExportManager.generate_full_report_workbook(
            df_unique=df_unique,
            df_mapping=df_mapping,
            summary=summary,
            resume_results=result["resume_results"],
            df_unique_phones=result["df_unique_phones"],
            config=custom_cfg
        )
        with pd.ExcelFile(custom_buf) as xls_custom:
            # Only selected sheets must be present
            assert "Unique Emails" in xls_custom.sheet_names
            assert "Resume Mapping" in xls_custom.sheet_names
            assert "Summary" not in xls_custom.sheet_names
            assert "Unique Phone Numbers" not in xls_custom.sheet_names
            assert "Failed Files" not in xls_custom.sheet_names

            # Only selected columns in Resume Mapping
            df_m_custom = pd.read_excel(xls_custom, sheet_name="Resume Mapping")
            assert list(df_m_custom.columns) == ["PDF Filename", "Extracted Emails", "Status"]
            assert "Full File Path" not in df_m_custom.columns

    def test_cancellation_support(self, sample_batch_dir):
        scan_res = scan_folder(sample_batch_dir, recursive=True, file_types=[".pdf"])
        stop_evt = threading.Event()

        # Stop after 2 files
        def on_progress(p):
            if p["current_index"] >= 2:
                stop_evt.set()

        processor = BatchProcessor(
            files=scan_res["files"],
            enable_ocr=False,
            progress_callback=on_progress,
            stop_event=stop_evt
        )
        result = processor.process()

        assert result["summary"]["was_stopped"] is True
        assert result["summary"]["processed_count"] <= 3
