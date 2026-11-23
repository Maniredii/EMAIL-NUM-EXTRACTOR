# Local Bulk Resume Email & Phone Extractor

A robust, private, and high-performance Windows desktop application to extract email addresses and phone numbers in bulk from hundreds or thousands of PDF, DOCX, and TXT resumes stored locally on your machine.

---

## 🔒 100% Local and Private

- **No Cloud Uploads**: Resumes are read directly from your local folders via Python filesystem APIs.
- **No External APIs or AI Calls**: Operates completely offline with zero data leakage.
- **No Resume Content Logging**: Only extracted contact info (emails, phones) and processing metadata are retained.
- **Safe Path Handling**: Output exports are saved in a dedicated external folder to prevent accidental recursive re-scanning.

---

## 🚀 Key Features

1. **Direct Local Folder Scanning**:
   - Provide any local folder path (e.g. `D:\HR\Resumes` or `C:\Users\Name\Desktop\Resumes`).
   - Native Windows folder selection dialog (`Browse...` button).
   - Recursive scanning toggle to detect PDFs in nested subfolders.
   - Discovered files pre-flight inspection (shows file count, folder count, total size, filenames).

2. **Ultra-Fast PDF Text Extraction**:
   - High-performance C-backed engine via **PyMuPDF** (`fitz`).
   - Handles multi-page resumes, embedded links, and `mailto:` hyperlinked anchors.
   - Low memory footprint: files are processed sequentially without buffering entire documents into RAM.

3. **Intelligent Email & Phone Extraction**:
   - **Email Detection**: Normalizes to lowercase, resolves obfuscations (`user [at] domain.com`), trims punctuation, and filters out media false positives (`photo@2x.png`).
   - **Phone Number Detection**: Supports US/Canada `(555) 010-1234`, India `+91 98765 43210`, UK/International `+44...`, `+61...`, and keyword-prefixed formats (`Tel:`, `Mobile:`, `Cell:`).
   - **Smart Filtering**: Rejects date ranges (`2018 - 2022`), salary numbers, zip codes, and repeated dummy digits (`0000000000`).
   - **Global Deduplication**: Provides unique email and phone lists with complete source file mapping.

4. **Resilient Batch Processing**:
   - Graceful fault tolerance: corrupted or password-protected PDFs do not crash the batch.
   - Real-time progress updates: progress bar, elapsed time, estimated remaining time, processed count, zero-contact count, failed count.
   - Interactive Stop/Cancel button to halt extraction safely without losing already processed results.

5. **Multi-Tab Result Tables**:
   - **Table 1: Unique Email Addresses** (Serial number, Email, Found in resume(s), Number of resumes).
   - **Table 2: Unique Phone Numbers** (Serial number, Phone Number, Found in resume(s), Number of resumes).
   - **Table 3: Resume Extraction Results** (Filename, Full path, Extracted emails, Extracted phone numbers, Counts, Status, Method, Duration).
   - Live search filters and status filter dropdown.

6. **Mass Mailing & Recruiter BCC Copy (Outlook & Gmail)**:
   - **Client-Specific Formatting**: Formats recipients with semicolons (`; `) for Outlook / Microsoft 365 or commas (`, `) for Gmail / Apple Mail.
   - **Anti-Spam Batch Slicer**: Automatically splits hundreds of emails into ready-to-copy chunks (25, 50, 75, or 100 recipients per batch) to bypass email provider recipient limits and keep deliverability high.
   - **1-Click Copy**: Built-in clipboard copy boxes for each batch and full unbatched list.
   - **Batch Text Files**: Generates `bcc_batches_outlook.txt` and `bcc_batches_gmail.txt` for easy reference.

7. **Comprehensive Exports**:
   - `unique_emails.xlsx` & `unique_emails.csv`: Deduplicated email list.
   - `unique_phones.xlsx` & `unique_phones.csv`: Deduplicated phone list.
   - `resume_email_mapping.xlsx` & `resume_email_mapping.csv`: Complete resume-to-contacts mapping.
   - `extraction_report.xlsx`: Multi-sheet workbook (`Unique Emails`, `Unique Phone Numbers`, `Resume Mapping`, `Summary`, `Failed Files`) with styled headers and auto-fitted columns.
   - `bcc_batches_outlook.txt` & `bcc_batches_gmail.txt`: Pre-formatted BCC recipient batches.
   - Direct browser download buttons AND automated "Save to Folder" export.

8. **Optional Scanned PDF (OCR) Support**:
   - Automatically detects low-text/image-only PDFs.
   - Seamlessly uses Tesseract OCR (if installed) to extract emails from scanned documents.
   - Disabled by default for maximum processing speed.

---

## 🛠️ Project Structure

```text
ResumeEmailExtractor/
│
├── app.py                      # Main Streamlit dashboard application
├── requirements.txt            # Python dependencies
├── setup.bat                   # 1-click Windows installer script
├── run.bat                     # 1-click application launcher
├── README.md                   # Full documentation
│
├── core/
│   ├── __init__.py
│   ├── folder_scanner.py       # os.walk directory crawler & validation
│   ├── pdf_reader.py           # PyMuPDF & Tesseract OCR text reader
│   ├── email_extractor.py      # Regex, obfuscation cleaner & normalizer
│   ├── processor.py            # Batch streaming engine with callbacks
│   └── export_manager.py       # Excel (openpyxl) and CSV report builder
│
├── ui/
│   ├── __init__.py
│   └── components.py           # Custom styling & native folder picker
│
└── tests/
    ├── __init__.py
    ├── test_email_extractor.py  # Unit tests for email extraction
    ├── test_pdf_reader.py       # Unit tests for PDF text & OCR reader
    ├── test_folder_scanner.py   # Unit tests for directory crawler
    └── test_batch_processor.py  # End-to-end batch processing tests
```

---

## ⚡ Quick Start (Windows)

### Option A: 1-Click Launchers (Recommended)

1. **Install Dependencies**:
   Double-click `setup.bat`. This will:
   - Verify Python 3.10+ is installed.
   - Create a local virtual environment (`.venv`).
   - Install all required packages.

2. **Launch Application**:
   Double-click `run.bat`.
   Your browser will automatically open: `http://localhost:8501`.

---

### Option B: Manual Terminal Execution

```bash
# 1. Open PowerShell or Command Prompt in the project folder
cd "d:\emails extractor"

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Launch Streamlit
streamlit run app.py
```

---

## 📖 Step-by-Step User Workflow

1. **Enter Folder Path**:
   - Type your folder path into the input field (e.g. `D:\HR\Resumes`) OR click **Browse...** to pick the folder using the native Windows Explorer picker.
2. **Scan Directory**:
   - Click **Scan Folder**. The app will scan all PDFs (and nested folders if enabled) and display the count, total size, and a file list.
3. **Start Extraction**:
   - Click **Start Email Extraction**.
   - Monitor real-time progress, elapsed time, and live counters.
4. **Inspect Results**:
   - Switch between **Unique Emails** and **Resume Mapping** tabs.
   - Use search and status filters to locate specific candidates.
5. **Export Results**:
   - Click **Export All Files to Folder** to write all spreadsheets to your designated output directory, or click the individual browser download buttons.

---

## 🧪 Running Automated Tests

Run the full automated test suite using `pytest`:

```bash
pytest tests/ -v
```
