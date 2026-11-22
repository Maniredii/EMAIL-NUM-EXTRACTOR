"""
Core package for Bulk Resume Email Extractor.
"""
from .folder_scanner import scan_folder, format_file_size
from .email_extractor import (
    extract_emails_from_text,
    normalize_email,
    format_emails_for_client,
    slice_emails_into_batches
)
from .phone_extractor import (
    extract_phone_numbers_from_text,
    normalize_phone_number
)
from .pdf_reader import extract_text_from_file, is_tesseract_available
from .processor import BatchProcessor
from .export_manager import ExportManager

__all__ = [
    "scan_folder",
    "format_file_size",
    "extract_emails_from_text",
    "normalize_email",
    "format_emails_for_client",
    "slice_emails_into_batches",
    "extract_phone_numbers_from_text",
    "normalize_phone_number",
    "extract_text_from_file",
    "is_tesseract_available",
    "BatchProcessor",
    "ExportManager",
]
