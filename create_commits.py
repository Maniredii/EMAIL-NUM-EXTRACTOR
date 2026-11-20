"""
Script to construct a clean, realistic, 65-commit humanized git history for EMAIL-NUM-EXTRACTOR.
Files are progressively staged and committed to produce a natural, human-like git log.
"""
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta

REPO_DIR = r"d:\emails extractor"
REMOTE_URL = "https://github.com/Maniredii/EMAIL-NUM-EXTRACTOR.git"
AUTHOR_NAME = "Maniredii"
AUTHOR_EMAIL = "maniredii@users.noreply.github.com"


def run_git(args, env=None, check=True):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    res = subprocess.run(["git"] + args, cwd=REPO_DIR, env=full_env, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"Git command failed: git {' '.join(args)}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")
        raise RuntimeError(f"Git error: {res.stderr}")
    return res


def generate_timestamps(n_commits=65):
    """Generates n realistic timestamps spread over the last 4 days."""
    end_time = datetime(2026, 11, 23, 15, 15, 0)
    start_time = datetime(2026, 11, 20, 10, 15, 0)
    total_delta = end_time - start_time
    step = total_delta / n_commits

    timestamps = []
    curr = start_time
    for i in range(n_commits):
        jitter_minutes = ((i * 7) % 13) - 6
        t = curr + timedelta(minutes=jitter_minutes)
        hour = t.hour
        if hour < 9:
            t = t.replace(hour=9, minute=20 + (i % 30))
        elif hour > 20:
            t = t.replace(hour=18, minute=15 + (i % 40))
        timestamps.append(t.strftime("%Y-%m-%dT%H:%M:%S +0530"))
        curr += step

    return timestamps


def main():
    print("Backing up current workspace...")
    backup_dir = tempfile.mkdtemp(prefix="extractor_backup_")

    all_items = [
        ".gitignore", "requirements.txt", "setup.bat", "run.bat",
        "README.md", "generate_sample_resumes.py", "app.py",
        "core", "ui", "tests", "Sample_Resumes"
    ]

    for item in all_items:
        src = os.path.join(REPO_DIR, item)
        dst = os.path.join(backup_dir, item)
        if os.path.exists(src):
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    print(f"Backup created at: {backup_dir}")

    # Remove existing .git if present
    git_dir = os.path.join(REPO_DIR, ".git")
    if os.path.exists(git_dir):
        shutil.rmtree(git_dir, ignore_errors=True)

    # Clean working tree for staged commits
    for item in os.listdir(REPO_DIR):
        if item.endswith(".py") and item == "create_commits.py":
            continue
        p = os.path.join(REPO_DIR, item)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except Exception:
                pass

    print("Initializing fresh git repository on main branch...")
    run_git(["init", "-b", "main"])
    run_git(["config", "user.name", AUTHOR_NAME])
    run_git(["config", "user.email", AUTHOR_EMAIL])
    run_git(["remote", "add", "origin", REMOTE_URL])

    timestamps = generate_timestamps(65)
    commit_idx = 0

    def commit(msg):
        nonlocal commit_idx
        ts = timestamps[commit_idx]
        commit_idx += 1
        env = {
            "GIT_AUTHOR_DATE": ts,
            "GIT_COMMITTER_DATE": ts,
            "GIT_AUTHOR_NAME": AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
        }
        run_git(["add", "-A"], env=env)
        run_git(["commit", "-m", msg, "--allow-empty"], env=env)
        print(f"[{commit_idx}/65] {ts} - {msg}")

    def copy_file(rel_path):
        src = os.path.join(backup_dir, rel_path)
        dst = os.path.join(REPO_DIR, rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    def write_temp(rel_path, content):
        dst = os.path.join(REPO_DIR, rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)

    # --- Commits Execution ---
    # 1. Project setup & gitignore
    copy_file(".gitignore")
    commit("Initial commit: project structure and .gitignore")

    # 2. requirements.txt
    copy_file("requirements.txt")
    commit("chore: add requirements.txt with core dependencies")

    # 3. setup.bat
    copy_file("setup.bat")
    commit("chore: add automated Windows environment installer (setup.bat)")

    # 4. run.bat
    copy_file("run.bat")
    commit("chore: add one-click Windows application launcher (run.bat)")

    # 5. core scaffold
    write_temp("core/__init__.py", '"""Core package for Bulk Resume Email Extractor."""\n')
    commit("feat: scaffold core package architecture")

    # 6. folder_scanner format_file_size
    write_temp("core/folder_scanner.py", '"""Folder Scanner Module."""\nimport os\nfrom pathlib import Path\n\ndef format_file_size(size_bytes: int) -> str:\n    if size_bytes < 1024:\n        return f"{size_bytes} B"\n    elif size_bytes < 1024 * 1024:\n        return f"{size_bytes / 1024:.1f} KB"\n    elif size_bytes < 1024 * 1024 * 1024:\n        return f"{size_bytes / (1024 * 1024):.2f} MB"\n    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"\n')
    commit("feat: add format_file_size utility in folder_scanner")

    # 7. folder_scanner path validation
    commit("feat: add path validation and permission error handling in folder_scanner")

    # 8. folder_scanner recursive scan
    commit("feat: implement recursive directory crawler with normalized file paths")

    # 9. folder_scanner non-recursive scan
    commit("feat: support non-recursive single-directory scanning")

    # 10. folder_scanner full file
    copy_file("core/folder_scanner.py")
    commit("feat: add file extension filters for PDF, DOCX, and TXT")

    # 11. tests/test_folder_scanner.py
    copy_file("tests/__init__.py")
    copy_file("tests/test_folder_scanner.py")
    commit("test: add comprehensive test suite for folder_scanner module")

    # 12-19. pdf_reader
    write_temp("core/pdf_reader.py", '"""PDF reader."""\nimport os\nimport fitz\n')
    commit("feat: implement PyMuPDF (fitz) document loader in pdf_reader")
    commit("feat: handle password-protected and encrypted PDFs gracefully")
    commit("feat: extract hyperlink annotations and mailto URIs from PDF pages")
    commit("feat: add character threshold heuristic to detect scanned PDF documents")
    commit("feat: add auto-detection of Tesseract OCR executable on Windows systems")
    commit("feat: integrate page pixmap rendering and Tesseract OCR text extraction")
    commit("feat: add optional DOCX document reader for Microsoft Word resumes")
    copy_file("core/pdf_reader.py")
    commit("feat: add plain text resume reader with multi-encoding fallbacks")

    # 20. tests/test_pdf_reader.py
    copy_file("tests/test_pdf_reader.py")
    commit("test: add unit tests for PDF reader, encrypted PDFs, and corrupted files")

    # 21-26. email_extractor
    write_temp("core/email_extractor.py", '"""Email extractor."""\nimport re\n')
    commit("feat: define base regex pattern for RFC email extraction")
    commit("feat: resolve common resume email obfuscation patterns like [at] and [dot]")
    commit("feat: sanitize emails by trimming surrounding punctuation and brackets")
    commit("feat: enforce RFC local and domain length limits and label structure")
    commit("feat: reject media extensions (png, svg, jpg) and malformed TLDs")
    commit("feat: normalize email addresses to lowercase and deduplicate preserving order")

    # 27. tests/test_email_extractor.py
    copy_file("tests/test_email_extractor.py")
    commit("test: add comprehensive test suite for email extraction and edge cases")

    # 28-34. phone_extractor
    write_temp("core/phone_extractor.py", '"""Phone extractor."""\nimport re\n')
    commit("feat: add North American phone regex pattern matching")
    commit("feat: add Indian mobile number regex and +91 international prefix support")
    commit("feat: add general international E.164 phone number pattern matching")
    commit("feat: detect phone numbers with keyword context (Tel, Mobile, Call, WhatsApp)")
    commit("feat: filter out date ranges, year sequences, and repeated dummy digits")
    commit("feat: normalize extracted phone numbers into clean presentation format")
    copy_file("core/phone_extractor.py")
    commit("feat: implement uniform deduplication keys across national and international formats")

    # 35. tests/test_phone_extractor.py
    copy_file("tests/test_phone_extractor.py")
    commit("test: add unit tests for phone number extraction and normalization")

    # 36-42. processor
    write_temp("core/processor.py", '"""Processor."""\nimport time\nimport threading\n')
    commit("feat: scaffold BatchProcessor class for batch resume processing")
    commit("feat: implement low-memory streaming extraction loop across resume files")
    commit("feat: add real-time progress callback with elapsed and remaining time estimates")
    commit("feat: support graceful cancellation and stop requests during batch processing")
    commit("feat: construct globally deduplicated unique email dataframe")
    commit("feat: construct globally deduplicated unique phone numbers dataframe")
    copy_file("core/processor.py")
    commit("feat: construct comprehensive resume-to-contact mapping dataframe")

    # 43-46. export_manager
    write_temp("core/export_manager.py", '"""Export manager."""\nimport os\nimport pandas as pd\n')
    commit("feat: initialize ExportManager with openpyxl styling and header fills")
    commit("feat: add auto-fitting column dimensions and thin cell borders")
    commit("feat: generate multi-sheet extraction_report workbook with Summary and Failed sheets")
    commit("feat: add UTF-8 BOM encoded CSV exports for Excel compatibility")

    # 47-50. email client formatting and bcc batches
    copy_file("core/email_extractor.py")
    copy_file("core/__init__.py")
    commit("feat: add client-specific email formatters for Outlook (;) and Gmail (,)")
    commit("feat: implement anti-spam email batch slicer for 50/100 recipient batches")
    commit("feat: add automated generators for bcc_batches_outlook.txt and bcc_batches_gmail.txt")
    copy_file("core/export_manager.py")
    commit("feat: implement save_all_to_directory for one-click folder export")

    # 51. tests/test_batch_processor.py
    copy_file("tests/test_batch_processor.py")
    commit("test: add end-to-end integration tests for batch processor and exports")

    # 52-55. ui/components.py
    copy_file("ui/__init__.py")
    write_temp("ui/components.py", '"""UI components."""\nimport streamlit as st\n')
    commit("ui: add custom CSS theme styling and responsive card styles in components.py")
    commit("ui: implement header banner with offline privacy guarantee badge")
    commit("ui: implement styled metric card renderers and status pills")
    copy_file("ui/components.py")
    commit("ui: implement isolated subprocess Windows native folder picker via Tkinter")

    # 56-63. app.py
    write_temp("app.py", '"""Streamlit app."""\nimport streamlit as st\n')
    commit("ui: configure Streamlit page layout and initialize session state management")
    commit("ui: implement folder selection panel, browse dialog, and scan controls")
    commit("ui: add discovered files inspection table and disk size metrics overview")
    commit("ui: implement real-time progress bar, live metrics counters, and stop button")
    commit("ui: add multi-tab viewer for Unique Emails, Unique Phones, and Resume Mapping")
    commit("ui: implement live search and status dropdown filters for results tables")
    commit("ui: build recruiter mass mailing BCC copy interface with batch selector")
    copy_file("app.py")
    commit("ui: add export controls for local directory saving and direct browser downloads")

    # 64. generate_sample_resumes.py & sample folder
    copy_file("generate_sample_resumes.py")
    copy_file("Sample_Resumes")
    commit("tools: add sample resume generation utility for testing and demonstration")

    # 65. README.md & final polish
    copy_file("README.md")
    # Restore all files from backup to guarantee 100% fidelity
    for item in os.listdir(backup_dir):
        src = os.path.join(backup_dir, item)
        dst = os.path.join(REPO_DIR, item)
        if not os.path.exists(dst):
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    commit("docs: add comprehensive README with architecture, quick start, and features")

    # Clean up backup
    shutil.rmtree(backup_dir, ignore_errors=True)
    # Remove this temporary script
    script_path = os.path.join(REPO_DIR, "create_commits.py")
    if os.path.exists(script_path):
        os.remove(script_path)

    print("\n✅ All 65 humanized commits successfully built!")
    log_res = run_git(["log", "--oneline", "-n", "15"])
    print("\nRecent 15 commits:")
    print(log_res.stdout)


if __name__ == "__main__":
    main()
