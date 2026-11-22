"""
Batch Processor Engine
Processes resume files sequentially with low memory overhead, real-time progress callbacks,
cancellation support, and robust error handling.
"""
import time
import threading
from typing import List, Dict, Any, Callable, Optional, Set
import pandas as pd

from .pdf_reader import extract_text_from_file
from .email_extractor import extract_emails_from_text
from .phone_extractor import extract_phone_numbers_from_text


class BatchProcessor:
    """
    Orchestrates the batch processing of resume files to extract emails and phone numbers.
    """

    def __init__(
        self,
        files: List[Dict[str, Any]],
        enable_ocr: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        stop_event: Optional[threading.Event] = None
    ):
        self.files = files
        self.enable_ocr = enable_ocr
        self.progress_callback = progress_callback
        self.stop_event = stop_event or threading.Event()

        # State and results
        self.resume_results: List[Dict[str, Any]] = []
        self.email_to_resumes: Dict[str, List[str]] = {}
        self.phone_to_resumes: Dict[str, List[str]] = {}
        self.is_running = False
        self.is_stopped = False

    def process(self) -> Dict[str, Any]:
        """
        Executes the batch processing loop.
        
        Returns:
            Dict containing summary stats, resume_results, email_to_resumes, phone_to_resumes,
            and prepared pandas DataFrames.
        """
        self.is_running = True
        self.is_stopped = False
        self.resume_results.clear()
        self.email_to_resumes.clear()
        self.phone_to_resumes.clear()

        total_files = len(self.files)
        start_time = time.time()

        completed_count = 0
        no_contact_count = 0
        failed_count = 0

        for idx, file_info in enumerate(self.files, 1):
            if self.stop_event.is_set():
                self.is_stopped = True
                break

            file_start = time.time()
            filename = file_info.get("filename", "")
            full_path = file_info.get("full_path", "")

            resume_record: Dict[str, Any] = {
                "filename": filename,
                "full_path": full_path,
                "relative_path": file_info.get("relative_path", filename),
                "emails": [],
                "emails_str": "",
                "email_count": 0,
                "phones": [],
                "phones_str": "",
                "phone_count": 0,
                "status": "Failed",
                "extraction_method": "None",
                "duration_seconds": 0.0,
                "error_details": "",
                "is_scanned": False
            }

            try:
                # 1. Extract text
                doc_result = extract_text_from_file(full_path, enable_ocr=self.enable_ocr)
                resume_record["extraction_method"] = doc_result.get("extraction_method", "None")
                resume_record["is_scanned"] = doc_result.get("is_scanned", False)

                if doc_result.get("status") == "Completed":
                    raw_text = doc_result.get("text", "")
                    
                    # 2. Extract emails and phone numbers from text
                    emails = extract_emails_from_text(raw_text)
                    phones = extract_phone_numbers_from_text(raw_text)

                    resume_record["emails"] = emails
                    resume_record["emails_str"] = ", ".join(emails) if emails else ""
                    resume_record["email_count"] = len(emails)

                    resume_record["phones"] = phones
                    resume_record["phones_str"] = ", ".join(phones) if phones else ""
                    resume_record["phone_count"] = len(phones)

                    if emails or phones:
                        resume_record["status"] = "Completed"
                        completed_count += 1

                        # Map emails to this resume
                        for em in emails:
                            if em not in self.email_to_resumes:
                                self.email_to_resumes[em] = []
                            if filename not in self.email_to_resumes[em]:
                                self.email_to_resumes[em].append(filename)

                        # Map phones to this resume
                        for ph in phones:
                            if ph not in self.phone_to_resumes:
                                self.phone_to_resumes[ph] = []
                            if filename not in self.phone_to_resumes[ph]:
                                self.phone_to_resumes[ph].append(filename)
                    else:
                        resume_record["status"] = "No Contacts Found"
                        no_contact_count += 1
                else:
                    resume_record["status"] = "Failed"
                    resume_record["error_details"] = doc_result.get("error_message", "Unknown read error")
                    failed_count += 1

            except Exception as e:
                resume_record["status"] = "Failed"
                resume_record["error_details"] = str(e)
                failed_count += 1

            file_duration = round(time.time() - file_start, 3)
            resume_record["duration_seconds"] = file_duration
            self.resume_results.append(resume_record)

            # Timing metrics
            elapsed = time.time() - start_time
            avg_per_file = elapsed / idx if idx > 0 else 0
            remaining_files = total_files - idx
            estimated_remaining = remaining_files * avg_per_file

            # Fire callback for UI updates
            if self.progress_callback:
                progress_payload = {
                    "current_index": idx,
                    "total_files": total_files,
                    "percent": idx / total_files if total_files > 0 else 1.0,
                    "current_filename": filename,
                    "elapsed_time": elapsed,
                    "estimated_remaining": estimated_remaining,
                    "processed_count": idx,
                    "completed_count": completed_count,
                    "no_email_count": no_contact_count,
                    "failed_count": failed_count,
                    "unique_emails_count": len(self.email_to_resumes),
                    "unique_phones_count": len(self.phone_to_resumes),
                    "last_result": resume_record,
                    "is_stopped": self.is_stopped
                }
                try:
                    self.progress_callback(progress_payload)
                except Exception:
                    pass

        self.is_running = False
        total_duration = time.time() - start_time

        # Build dataframes
        df_unique_emails = self.build_unique_emails_dataframe()
        df_unique_phones = self.build_unique_phones_dataframe()
        df_mapping = self.build_resume_mapping_dataframe()

        summary = {
            "total_files": total_files,
            "processed_count": len(self.resume_results),
            "completed_count": completed_count,
            "no_email_count": no_contact_count,
            "failed_count": failed_count,
            "unique_emails_count": len(self.email_to_resumes),
            "unique_phones_count": len(self.phone_to_resumes),
            "total_duration_seconds": round(total_duration, 2),
            "was_stopped": self.is_stopped
        }

        return {
            "summary": summary,
            "resume_results": self.resume_results,
            "email_to_resumes": self.email_to_resumes,
            "phone_to_resumes": self.phone_to_resumes,
            "df_unique_emails": df_unique_emails,
            "df_unique_phones": df_unique_phones,
            "df_resume_mapping": df_mapping
        }

    def build_unique_emails_dataframe(self) -> pd.DataFrame:
        """Constructs Table 1: Unique Email Addresses DataFrame."""
        rows = []
        for idx, (email, filenames) in enumerate(sorted(self.email_to_resumes.items()), 1):
            rows.append({
                "Serial Number": idx,
                "Email Address": email,
                "Found in Resume(s)": ", ".join(filenames),
                "Number of Resumes": len(filenames)
            })

        if not rows:
            return pd.DataFrame(columns=[
                "Serial Number", "Email Address", "Found in Resume(s)", "Number of Resumes"
            ])
        return pd.DataFrame(rows)

    def build_unique_phones_dataframe(self) -> pd.DataFrame:
        """Constructs Unique Phone Numbers DataFrame."""
        rows = []
        for idx, (phone, filenames) in enumerate(sorted(self.phone_to_resumes.items()), 1):
            rows.append({
                "Serial Number": idx,
                "Phone Number": phone,
                "Found in Resume(s)": ", ".join(filenames),
                "Number of Resumes": len(filenames)
            })

        if not rows:
            return pd.DataFrame(columns=[
                "Serial Number", "Phone Number", "Found in Resume(s)", "Number of Resumes"
            ])
        return pd.DataFrame(rows)

    def build_resume_mapping_dataframe(self) -> pd.DataFrame:
        """Constructs Table 2: Resume Extraction Results DataFrame."""
        rows = []
        for r in self.resume_results:
            rows.append({
                "PDF Filename": r["filename"],
                "Full File Path": r["full_path"],
                "Extracted Emails": r["emails_str"],
                "Extracted Phone Numbers": r["phones_str"],
                "Email Count": r["email_count"],
                "Phone Count": r["phone_count"],
                "Status": r["status"],
                "Method": r["extraction_method"],
                "Duration (s)": r["duration_seconds"],
                "Error Details": r["error_details"]
            })

        if not rows:
            return pd.DataFrame(columns=[
                "PDF Filename", "Full File Path", "Extracted Emails", "Extracted Phone Numbers",
                "Email Count", "Phone Count", "Status", "Method", "Duration (s)", "Error Details"
            ])
        return pd.DataFrame(rows)
