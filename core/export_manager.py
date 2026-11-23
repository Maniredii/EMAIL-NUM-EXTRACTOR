"""
Export Manager Module
Exports extraction results to Excel (.xlsx) and CSV (.csv) formats,
including the multi-sheet extraction_report.xlsx.
"""
import os
import io
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ExportManager:
    """Handles Excel and CSV exports with automated styling and safe directory handling."""

    HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    THIN_BORDER = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    @classmethod
    def format_worksheet(cls, ws, min_width=12, max_width=60):
        """Applies headers styling and auto-fits column widths."""
        for col in ws.columns:
            header_cell = col[0]
            header_cell.fill = cls.HEADER_FILL
            header_cell.font = cls.HEADER_FONT
            header_cell.alignment = Alignment(horizontal="center", vertical="center")

            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            col_width = max(min_width, min(max_len + 3, max_width))
            ws.column_dimensions[col_letter].width = col_width

            for cell in col:
                cell.border = cls.THIN_BORDER
                if cell.row > 1:
                    cell.alignment = Alignment(vertical="center")

    @classmethod
    def generate_full_report_workbook(
        cls,
        df_unique: pd.DataFrame,
        df_mapping: pd.DataFrame,
        summary: Dict[str, Any],
        resume_results: List[Dict[str, Any]],
        df_unique_phones: Optional[pd.DataFrame] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> io.BytesIO:
        """
        Creates extraction_report.xlsx with customizable sheets and columns:
        1. Unique Emails (customizable columns)
        2. Unique Phone Numbers (customizable columns)
        3. Resume Mapping (customizable columns)
        4. Summary (optional)
        5. Failed Files (optional)
        """
        cfg = config or {}
        include_emails = cfg.get("include_unique_emails", True)
        include_phones = cfg.get("include_unique_phones", True)
        include_mapping = cfg.get("include_resume_mapping", True)
        include_summary = cfg.get("include_summary", True)
        include_failed = cfg.get("include_failed_files", True)

        # Fallback: ensure at least one sheet is included so workbook is valid
        if not any([include_emails, include_phones, include_mapping, include_summary, include_failed]):
            include_emails = True
            include_mapping = True

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Unique Emails
            if include_emails:
                email_cols = cfg.get("email_columns")
                df_u = df_unique[[c for c in email_cols if c in df_unique.columns]] if email_cols else df_unique
                df_u.to_excel(writer, sheet_name="Unique Emails", index=False)

            # Sheet 2: Unique Phone Numbers
            if include_phones and df_unique_phones is not None and not df_unique_phones.empty:
                phone_cols = cfg.get("phone_columns")
                df_p = df_unique_phones[[c for c in phone_cols if c in df_unique_phones.columns]] if phone_cols else df_unique_phones
                df_p.to_excel(writer, sheet_name="Unique Phone Numbers", index=False)

            # Sheet 3: Resume Mapping
            if include_mapping:
                mapping_cols = cfg.get("mapping_columns")
                df_m = df_mapping[[c for c in mapping_cols if c in df_mapping.columns]] if mapping_cols else df_mapping
                df_m.to_excel(writer, sheet_name="Resume Mapping", index=False)

            # Sheet 4: Summary
            if include_summary:
                summary_data = [
                    {"Metric": "Total Resumes Discovered", "Value": summary.get("total_files", 0)},
                    {"Metric": "Total Resumes Processed", "Value": summary.get("processed_count", 0)},
                    {"Metric": "Resumes with Contacts Found", "Value": summary.get("completed_count", 0)},
                    {"Metric": "Resumes with Zero Contacts", "Value": summary.get("no_email_count", 0)},
                    {"Metric": "Failed / Corrupted Files", "Value": summary.get("failed_count", 0)},
                    {"Metric": "Total Unique Emails Extracted", "Value": summary.get("unique_emails_count", 0)},
                    {"Metric": "Total Unique Phone Numbers Extracted", "Value": summary.get("unique_phones_count", 0)},
                    {"Metric": "Total Processing Time (seconds)", "Value": summary.get("total_duration_seconds", 0)},
                    {"Metric": "Process Stopped Early", "Value": "Yes" if summary.get("was_stopped") else "No"}
                ]
                df_sum = pd.DataFrame(summary_data)
                df_sum.to_excel(writer, sheet_name="Summary", index=False)

            # Sheet 5: Failed Files
            if include_failed:
                failed_records = [
                    {
                        "Filename": r["filename"],
                        "Path": r["full_path"],
                        "Extraction Method": r["extraction_method"],
                        "Error Details": r["error_details"]
                    }
                    for r in resume_results if r.get("status") == "Failed"
                ]
                if failed_records:
                    df_failed = pd.DataFrame(failed_records)
                else:
                    df_failed = pd.DataFrame(columns=["Filename", "Path", "Extraction Method", "Error Details"])
                df_failed.to_excel(writer, sheet_name="Failed Files", index=False)

            # Apply styling to all sheets
            for sheetname in writer.book.sheetnames:
                ws = writer.book[sheetname]
                cls.format_worksheet(ws)

        output.seek(0)
        return output

    @classmethod
    def generate_single_excel_bytes(cls, df: pd.DataFrame, sheet_name: str = "Sheet1") -> io.BytesIO:
        """Generates a styled single-sheet Excel workbook in-memory."""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.book[sheet_name]
            cls.format_worksheet(ws)
        output.seek(0)
        return output

    @classmethod
    def generate_csv_bytes(cls, df: pd.DataFrame) -> bytes:
        """Generates UTF-8 encoded CSV with BOM for Excel compatibility."""
        return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

    @classmethod
    def generate_bcc_batches_text(cls, emails: List[str], batch_size: int = 50, client: str = "outlook") -> str:
        """
        Generates formatted text content split into batches for BCC copy-pasting.
        client can be 'outlook' (semicolon) or 'gmail' (comma).
        """
        from .email_extractor import slice_emails_into_batches
        batches = slice_emails_into_batches(emails, batch_size=batch_size)
        if not batches:
            return "No email addresses available."

        sep_name = "Outlook / Microsoft 365 (Semicolon ';')" if client == "outlook" else "Gmail / General Webmail (Comma ',')"
        lines = [
            f"# BULK BCC EMAIL BATCHES",
            f"# Target Format: {sep_name}",
            f"# Total Emails: {len(emails)} | Total Batches: {len(batches)} | Batch Size: {batch_size}",
            f"# Instructions: Copy each batch's recipient string and paste directly into your email's BCC field.",
            ""
        ]

        for b in batches:
            lines.append("=" * 80)
            lines.append(f"BATCH {b['batch_number']} (Emails {b['start_index']} to {b['end_index']} of {len(emails)} - {b['total_in_batch']} recipients)")
            lines.append("=" * 80)
            content_str = b["outlook_str"] if client == "outlook" else b["gmail_str"]
            lines.append(content_str)
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def save_all_to_directory(
        cls,
        output_directory: str,
        df_unique: pd.DataFrame,
        df_mapping: pd.DataFrame,
        summary: Dict[str, Any],
        resume_results: List[Dict[str, Any]],
        batch_size: int = 50,
        df_unique_phones: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Saves all Excel, CSV, and BCC batch text files to the designated local directory.
        
        Returns:
            Dict of status, saved file paths, or error message.
        """
        res = {
            "success": False,
            "output_dir": "",
            "files_saved": [],
            "error_message": ""
        }

        try:
            out_path = Path(output_directory).resolve()
            out_path.mkdir(parents=True, exist_ok=True)
            res["output_dir"] = str(out_path)

            # 1. unique_emails.xlsx
            unique_xlsx_path = out_path / "unique_emails.xlsx"
            unique_bytes = cls.generate_single_excel_bytes(df_unique, sheet_name="Unique Emails")
            with open(unique_xlsx_path, "wb") as f:
                f.write(unique_bytes.getbuffer())
            res["files_saved"].append(str(unique_xlsx_path))

            # 2. unique_emails.csv
            unique_csv_path = out_path / "unique_emails.csv"
            with open(unique_csv_path, "wb") as f:
                f.write(cls.generate_csv_bytes(df_unique))
            res["files_saved"].append(str(unique_csv_path))

            # 3. unique_phones.xlsx & unique_phones.csv (if phones exist)
            if df_unique_phones is not None and not df_unique_phones.empty:
                phones_xlsx_path = out_path / "unique_phones.xlsx"
                phones_bytes = cls.generate_single_excel_bytes(df_unique_phones, sheet_name="Unique Phones")
                with open(phones_xlsx_path, "wb") as f:
                    f.write(phones_bytes.getbuffer())
                res["files_saved"].append(str(phones_xlsx_path))

                phones_csv_path = out_path / "unique_phones.csv"
                with open(phones_csv_path, "wb") as f:
                    f.write(cls.generate_csv_bytes(df_unique_phones))
                res["files_saved"].append(str(phones_csv_path))

            # 4. resume_email_mapping.xlsx
            mapping_xlsx_path = out_path / "resume_email_mapping.xlsx"
            mapping_bytes = cls.generate_single_excel_bytes(df_mapping, sheet_name="Resume Mapping")
            with open(mapping_xlsx_path, "wb") as f:
                f.write(mapping_bytes.getbuffer())
            res["files_saved"].append(str(mapping_xlsx_path))

            # 5. resume_email_mapping.csv
            mapping_csv_path = out_path / "resume_email_mapping.csv"
            with open(mapping_csv_path, "wb") as f:
                f.write(cls.generate_csv_bytes(df_mapping))
            res["files_saved"].append(str(mapping_csv_path))

            # 6. extraction_report.xlsx (Full multi-sheet workbook with Emails + Phones + Mapping)
            report_xlsx_path = out_path / "extraction_report.xlsx"
            report_bytes = cls.generate_full_report_workbook(
                df_unique, df_mapping, summary, resume_results, df_unique_phones=df_unique_phones
            )
            with open(report_xlsx_path, "wb") as f:
                f.write(report_bytes.getbuffer())
            res["files_saved"].append(str(report_xlsx_path))

            # 7. bcc_batches_outlook.txt & bcc_batches_gmail.txt
            unique_emails_list = df_unique["Email Address"].tolist() if not df_unique.empty and "Email Address" in df_unique.columns else []
            if unique_emails_list:
                outlook_txt_path = out_path / "bcc_batches_outlook.txt"
                with open(outlook_txt_path, "w", encoding="utf-8") as f:
                    f.write(cls.generate_bcc_batches_text(unique_emails_list, batch_size=batch_size, client="outlook"))
                res["files_saved"].append(str(outlook_txt_path))

                gmail_txt_path = out_path / "bcc_batches_gmail.txt"
                with open(gmail_txt_path, "w", encoding="utf-8") as f:
                    f.write(cls.generate_bcc_batches_text(unique_emails_list, batch_size=batch_size, client="gmail"))
                res["files_saved"].append(str(gmail_txt_path))

            res["success"] = True
            return res

        except Exception as e:
            res["error_message"] = f"Failed to save exports: {str(e)}"
            return res
