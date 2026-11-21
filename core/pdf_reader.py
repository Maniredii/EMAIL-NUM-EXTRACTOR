"""
PDF and Document Reader Module
Extracts text from PDF (PyMuPDF / fitz), with fallback OCR via Tesseract,
as well as optional DOCX and TXT file support.
"""
import io
import os
import shutil
from typing import Dict, Any, Optional
import fitz  # PyMuPDF

# Optional OCR imports
try:
    import pytesseract
    from PIL import Image
    HAS_OCR_LIBS = True
except ImportError:
    HAS_OCR_LIBS = False

# Optional docx import
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def find_tesseract_path() -> Optional[str]:
    """Finds the tesseract executable on Windows or system PATH."""
    cmd = shutil.which("tesseract")
    if cmd:
        return cmd
    
    # Common Windows installation directories
    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for p in win_paths:
        if os.path.isfile(p):
            return p
    return None


def is_tesseract_available() -> bool:
    """Checks if pytesseract and the Tesseract binary are both available."""
    if not HAS_OCR_LIBS:
        return False
    path = find_tesseract_path()
    return path is not None


# Initialize tesseract path if found
if HAS_OCR_LIBS:
    _t_path = find_tesseract_path()
    if _t_path:
        pytesseract.pytesseract.tesseract_cmd = _t_path


def extract_text_from_pdf(
    file_path: str,
    enable_ocr: bool = False,
    min_text_threshold: int = 25,
    ocr_max_pages: int = 5
) -> Dict[str, Any]:
    """
    Extracts text from a PDF file using PyMuPDF and optional Tesseract OCR.

    Args:
        file_path: Path to the PDF file.
        enable_ocr: Whether to attempt OCR if text is empty or insufficient.
        min_text_threshold: Minimum character count to consider text non-empty.
        ocr_max_pages: Maximum pages to OCR (prevents huge OCR delays on long PDFs).

    Returns:
        Dict with text, page_count, status, extraction_method, error_message, is_scanned.
    """
    result: Dict[str, Any] = {
        "text": "",
        "page_count": 0,
        "status": "Failed",
        "extraction_method": "None",
        "error_message": "",
        "is_scanned": False
    }

    doc = None
    try:
        doc = fitz.open(file_path)
        result["page_count"] = len(doc)

        if doc.is_encrypted:
            # Attempt blank password
            auth_ok = doc.authenticate("")
            if not auth_ok:
                result["error_message"] = "PDF is password protected and cannot be opened."
                return result

        extracted_text_parts = []
        links_text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Standard text extraction
            page_text = page.get_text()
            if page_text:
                extracted_text_parts.append(page_text)

            # Inspect hyperlink annotations (e.g. mailto: in modern resumes)
            try:
                for link in page.get_links():
                    uri = link.get("uri", "")
                    if uri and uri.lower().startswith("mailto:"):
                        links_text_parts.append(uri)
            except Exception:
                pass

        full_extracted_text = "\n".join(extracted_text_parts + links_text_parts).strip()
        result["text"] = full_extracted_text

        # Check if text is sufficient
        if len(full_extracted_text) >= min_text_threshold:
            result["status"] = "Completed"
            result["extraction_method"] = "Text"
            return result

        # Text is sparse or empty; could be a scanned document
        result["is_scanned"] = True

        if enable_ocr:
            if not is_tesseract_available():
                result["status"] = "Completed"
                result["extraction_method"] = "Text (OCR unavailable)"
                result["error_message"] = "OCR enabled but Tesseract binary is not installed or detected."
                return result

            # Run OCR on pages
            ocr_text_parts = []
            pages_to_ocr = min(len(doc), ocr_max_pages)
            for page_idx in range(pages_to_ocr):
                page = doc[page_idx]
                # Render page to 150 DPI pixmap for OCR
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                page_ocr_text = pytesseract.image_to_string(img)
                if page_ocr_text:
                    ocr_text_parts.append(page_ocr_text)

            ocr_full_text = "\n".join(ocr_text_parts).strip()
            combined_text = f"{full_extracted_text}\n{ocr_full_text}".strip()
            result["text"] = combined_text
            result["status"] = "Completed"
            result["extraction_method"] = "OCR"
            return result
        else:
            result["status"] = "Completed"
            result["extraction_method"] = "Text (Low/Empty - Scanned?)"
            return result

    except fitz.FileDataError as fde:
        result["error_message"] = f"Corrupted or invalid PDF file: {str(fde)}"
        return result
    except Exception as e:
        result["error_message"] = f"Error reading PDF: {str(e)}"
        return result
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def extract_text_from_docx(file_path: str) -> Dict[str, Any]:
    """Extracts text from a DOCX document."""
    result: Dict[str, Any] = {
        "text": "",
        "page_count": 1,
        "status": "Failed",
        "extraction_method": "Docx",
        "error_message": "",
        "is_scanned": False
    }
    if not HAS_DOCX:
        result["error_message"] = "python-docx package is not installed."
        return result

    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text:
                full_text.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        full_text.append(cell.text)
        result["text"] = "\n".join(full_text)
        result["status"] = "Completed"
        return result
    except Exception as e:
        result["error_message"] = f"Error reading DOCX: {str(e)}"
        return result


def extract_text_from_txt(file_path: str) -> Dict[str, Any]:
    """Extracts text from a plain TXT file."""
    result: Dict[str, Any] = {
        "text": "",
        "page_count": 1,
        "status": "Failed",
        "extraction_method": "Txt",
        "error_message": "",
        "is_scanned": False
    }
    try:
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                    result["text"] = f.read()
                result["status"] = "Completed"
                return result
            except UnicodeDecodeError:
                continue
        result["error_message"] = "Failed to decode text file."
        return result
    except Exception as e:
        result["error_message"] = f"Error reading TXT: {str(e)}"
        return result


def extract_text_from_file(
    file_path: str,
    enable_ocr: bool = False,
    min_text_threshold: int = 25
) -> Dict[str, Any]:
    """Unified file reader supporting PDF, DOCX, and TXT."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path, enable_ocr=enable_ocr, min_text_threshold=min_text_threshold)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    elif ext == ".txt":
        return extract_text_from_txt(file_path)
    else:
        return {
            "text": "",
            "page_count": 0,
            "status": "Failed",
            "extraction_method": "Unsupported",
            "error_message": f"Unsupported file format: {ext}",
            "is_scanned": False
        }
