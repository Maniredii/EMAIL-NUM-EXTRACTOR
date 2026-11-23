"""
Resume Email Extractor - Streamlit Main Application
Bulk email extraction from local resume folders with zero cloud upload.
"""
import os
import sys
import time
import zipfile
import tempfile
import threading
from pathlib import Path
import streamlit as st
import pandas as pd

# Core and UI imports
from core.folder_scanner import scan_folder, format_file_size
from core.pdf_reader import is_tesseract_available, find_tesseract_path
from core.processor import BatchProcessor
from core.export_manager import ExportManager
from core.email_extractor import slice_emails_into_batches, format_emails_for_client
from ui.components import (
    apply_custom_css,
    render_header,
    render_metric_card,
    open_native_folder_dialog,
)

# Set page configuration
st.set_page_config(
    page_title="Resume Email Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom UI styling
apply_custom_css()

# Initialize session state variables
if "folder_path" not in st.session_state:
    st.session_state.folder_path = ""
if "output_dir" not in st.session_state:
    # Default to an Email_Extraction_Results folder in user home or current directory
    st.session_state.output_dir = str(Path.cwd() / "Email_Extraction_Results")
if "recursive" not in st.session_state:
    st.session_state.recursive = True
if "include_docx_txt" not in st.session_state:
    st.session_state.include_docx_txt = False
if "enable_ocr" not in st.session_state:
    st.session_state.enable_ocr = False
if "scan_data" not in st.session_state:
    st.session_state.scan_data = None
if "extraction_data" not in st.session_state:
    st.session_state.extraction_data = None
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()
if "is_running" not in st.session_state:
    st.session_state.is_running = False


# Render Header
render_header()

# Sidebar: Configuration and Instructions
with st.sidebar:
    st.markdown("### ⚙️ Extraction Settings")

    # Recursive Scanning Toggle
    st.session_state.recursive = st.toggle(
        "Include Subfolders (Recursive)",
        value=st.session_state.recursive,
        help="Scan all nested directories inside the chosen folder."
    )

    # Optional File Types Toggle
    st.session_state.include_docx_txt = st.toggle(
        "Include DOCX & TXT Files",
        value=st.session_state.include_docx_txt,
        help="Also scan Word (.docx) and plain text (.txt) resumes alongside PDFs."
    )

    # OCR Toggle & Diagnostics
    tesseract_found = is_tesseract_available()
    tesseract_path = find_tesseract_path()

    st.markdown("---")
    st.markdown("### 🔍 Scanned PDFs (OCR)")
    
    ocr_disabled = not tesseract_found
    st.session_state.enable_ocr = st.checkbox(
        "Enable OCR for Scanned PDFs",
        value=st.session_state.enable_ocr and tesseract_found,
        disabled=ocr_disabled,
        help="Attempt Tesseract OCR if PDF has empty or insufficient embedded text."
    )

    if tesseract_found:
        st.caption(f"✅ Tesseract detected at:\n`{tesseract_path}`")
    else:
        st.caption("⚠️ Tesseract not detected. OCR is disabled. Standard text extraction remains fully active.")

    st.markdown("---")
    st.markdown("### 📁 Output Directory")
    custom_output = st.text_input(
        "Export Results Folder",
        value=st.session_state.output_dir,
        help="Where Excel and CSV reports will be saved."
    )
    if custom_output != st.session_state.output_dir:
        st.session_state.output_dir = custom_output

    col_btn_out, _ = st.columns([1, 1])
    with col_btn_out:
        if st.button("📂 Change Output Folder", key="browse_out_btn"):
            chosen_out = open_native_folder_dialog(st.session_state.output_dir)
            if chosen_out:
                st.session_state.output_dir = chosen_out
                st.rerun()

    st.markdown("---")
    st.markdown("### 🛡️ Privacy Guarantee")
    st.caption(
        "• 100% offline local processing\n"
        "• Zero external network requests\n"
        "• No resume text logging\n"
        "• Direct disk reading with PyMuPDF"
    )


# Section 1: Folder Selection / Upload Panel
st.markdown("### 1. Select Resume Source")

source_tab1, source_tab2 = st.tabs([
    "📁 Local Folder Path (Windows / Desktop)",
    "☁️ Upload Resumes (.zip or multiple PDFs)"
])

with source_tab1:
    col_input, col_browse, col_scan = st.columns([5, 1.2, 1.2], gap="small")

    with col_input:
        current_path = st.text_input(
            "Resume Folder Path",
            value=st.session_state.folder_path,
            placeholder=r"e.g. D:\HR\Resumes or C:\Users\User\Desktop\Resumes or Sample_Resumes",
            label_visibility="collapsed"
        )
        if current_path != st.session_state.folder_path:
            st.session_state.folder_path = current_path

    with col_browse:
        if st.button("📁 Browse...", use_container_width=True, help="Open native Windows folder picker (Local desktop only)"):
            picked_dir = open_native_folder_dialog(st.session_state.folder_path)
            if picked_dir:
                st.session_state.folder_path = picked_dir
                st.rerun()

    with col_scan:
        scan_clicked = st.button("🔎 Scan Folder", type="primary", use_container_width=True)

    # Quick shortcut for sample resumes
    if os.path.isdir("Sample_Resumes"):
        col_sample, _ = st.columns([2.5, 4])
        with col_sample:
            if st.button("✨ Quick Test: Load Included Sample Resumes", use_container_width=True):
                st.session_state.folder_path = str(Path("Sample_Resumes").resolve())
                scan_clicked = True

with source_tab2:
    st.caption("Upload a `.zip` archive containing resumes or select multiple PDF/DOCX files directly. Ideal when using Streamlit Cloud.")
    uploaded_files = st.file_uploader(
        "Choose PDF / DOCX resumes or a .ZIP archive",
        type=["pdf", "docx", "txt", "zip"],
        accept_multiple_files=True
    )
    if uploaded_files:
        if st.button("📦 Unpack & Scan Uploaded Resumes", type="primary"):
            temp_upload_dir = tempfile.mkdtemp(prefix="uploaded_resumes_")
            for uf in uploaded_files:
                if uf.name.lower().endswith(".zip"):
                    try:
                        with zipfile.ZipFile(uf) as zf:
                            zf.extractall(temp_upload_dir)
                    except Exception as ze:
                        st.error(f"Error unzipping {uf.name}: {ze}")
                else:
                    save_path = os.path.join(temp_upload_dir, uf.name)
                    with open(save_path, "wb") as f:
                        f.write(uf.getbuffer())

            st.session_state.folder_path = temp_upload_dir
            scan_clicked = True

# Scan Execution Trigger
if scan_clicked:
    st.session_state.stop_event.clear()
    file_types = [".pdf"]
    if st.session_state.include_docx_txt:
        file_types.extend([".docx", ".doc", ".txt"])

    with st.spinner("Scanning directory structure..."):
        scan_res = scan_folder(
            folder_path=st.session_state.folder_path,
            recursive=st.session_state.recursive,
            file_types=file_types
        )
        st.session_state.scan_data = scan_res

        if not scan_res["is_valid"]:
            st.error(f"❌ {scan_res['error_message']}")
        elif scan_res["total_files"] == 0:
            st.warning("⚠️ Directory is valid, but no matching resume files were found.")
        else:
            st.success(f"✅ Discovered {scan_res['total_files']} resume files.")


# Section 2: Scan Results & Discovered Files
if st.session_state.scan_data and st.session_state.scan_data.get("is_valid"):
    scan = st.session_state.scan_data
    total_files = scan["total_files"]

    st.markdown("---")
    st.markdown("### 2. Discovered Files Overview")

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(render_metric_card("Total Resume Files", str(total_files)), unsafe_allow_html=True)
    with m2:
        st.markdown(render_metric_card("Folders Searched", str(scan["total_folders_searched"])), unsafe_allow_html=True)
    with m3:
        st.markdown(render_metric_card("Total Size", scan["total_size_str"]), unsafe_allow_html=True)
    with m4:
        ext_summary = ", ".join(set(f["extension"].upper() for f in scan["files"])) if scan["files"] else "None"
        st.markdown(render_metric_card("File Formats", ext_summary), unsafe_allow_html=True)

    st.write("")
    # Discovered files table
    if total_files > 0:
        with st.expander(f"📋 View Discovered Files List ({total_files} files)", expanded=(total_files <= 20)):
            df_files = pd.DataFrame([
                {
                    "#": idx,
                    "Filename": f["filename"],
                    "Relative Folder": f["parent_folder"],
                    "Size": f["size_str"],
                    "Modified Date": f["modified_time"]
                }
                for idx, f in enumerate(scan["files"], 1)
            ])
            st.dataframe(df_files, use_container_width=True, hide_index=True, height=260)


    # Section 3: Extraction Controls
    st.markdown("---")
    st.markdown("### 3. Extraction Controls")

    ctrl_c1, ctrl_c2, ctrl_c3, ctrl_c4 = st.columns([2, 1.5, 1.5, 1.5])

    with ctrl_c1:
        start_disabled = (total_files == 0) or st.session_state.is_running
        start_btn = st.button("🚀 Start Email Extraction", type="primary", use_container_width=True, disabled=start_disabled)

    with ctrl_c2:
        stop_disabled = not st.session_state.is_running
        stop_btn = st.button("⏹️ Stop Extraction", use_container_width=True, disabled=stop_disabled)

    with ctrl_c3:
        rescan_btn = st.button("🔄 Re-scan Folder", use_container_width=True)

    with ctrl_c4:
        clear_btn = st.button("🗑️ Clear Results", use_container_width=True)

    if stop_btn:
        st.session_state.stop_event.set()
        st.warning("⚠️ Stopping extraction gracefully after current file finishes...")

    if rescan_btn:
        st.session_state.scan_data = None
        st.session_state.extraction_data = None
        st.session_state.stop_event.clear()
        st.rerun()

    if clear_btn:
        st.session_state.extraction_data = None
        st.session_state.stop_event.clear()
        st.rerun()


    # Section 4: Live Processing
    if start_btn:
        st.session_state.is_running = True
        st.session_state.stop_event.clear()

        # Progress containers
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        metrics_placeholder = st.empty()

        def update_ui_progress(p: dict):
            pct = min(max(p["percent"], 0.0), 1.0)
            progress_bar.progress(pct)
            
            elapsed_str = f"{p['elapsed_time']:.1f}s"
            rem_str = f"{p['estimated_remaining']:.1f}s" if p['estimated_remaining'] > 0 else "0s"
            
            status_text.markdown(
                f"**Processing:** `{p['current_filename']}` ({p['current_index']}/{p['total_files']}) "
                f"| Elapsed: `{elapsed_str}` | Est. Remaining: `{rem_str}`"
            )

            metrics_placeholder.markdown(f"""
                <div style="display: flex; gap: 12px; margin-top: 8px; margin-bottom: 12px;">
                    <div style="flex:1; background:#DEF7EC; padding:8px; border-radius:6px; text-align:center;">
                        <b style="color:#03543F;">{p['completed_count']}</b><br><small style="color:#03543F;">With Contacts</small>
                    </div>
                    <div style="flex:1; background:#FEF08A; padding:8px; border-radius:6px; text-align:center;">
                        <b style="color:#713F12;">{p['no_email_count']}</b><br><small style="color:#713F12;">Zero Contacts</small>
                    </div>
                    <div style="flex:1; background:#FDE8E8; padding:8px; border-radius:6px; text-align:center;">
                        <b style="color:#9B1C1C;">{p['failed_count']}</b><br><small style="color:#9B1C1C;">Failed Files</small>
                    </div>
                    <div style="flex:1; background:#EFF6FF; padding:8px; border-radius:6px; text-align:center;">
                        <b style="color:#1E40AF;">{p['unique_emails_count']}</b><br><small style="color:#1E40AF;">Unique Emails</small>
                    </div>
                    <div style="flex:1; background:#F3E8FF; padding:8px; border-radius:6px; text-align:center;">
                        <b style="color:#6B21A8;">{p.get('unique_phones_count', 0)}</b><br><small style="color:#6B21A8;">Unique Phones</small>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        processor = BatchProcessor(
            files=scan["files"],
            enable_ocr=st.session_state.enable_ocr,
            progress_callback=update_ui_progress,
            stop_event=st.session_state.stop_event
        )

        extraction_result = processor.process()
        st.session_state.extraction_data = extraction_result
        st.session_state.is_running = False

        progress_bar.progress(1.0)
        status_text.empty()
        st.success(
            f"🎉 Extraction complete! Processed {extraction_result['summary']['processed_count']} files in "
            f"{extraction_result['summary']['total_duration_seconds']}s. Found {extraction_result['summary']['unique_emails_count']} unique emails."
        )
        st.rerun()


# Section 5: Extraction Results & Export
if st.session_state.extraction_data:
    ext_data = st.session_state.extraction_data
    summary = ext_data["summary"]
    df_unique = ext_data["df_unique_emails"]
    df_unique_phones = ext_data.get("df_unique_phones", pd.DataFrame())
    df_mapping = ext_data["df_resume_mapping"]
    resume_results = ext_data["resume_results"]

    st.markdown("---")
    st.markdown("### 4. Extraction Summary")

    sm1, sm2, sm3, sm4, sm5, sm6 = st.columns(6)
    with sm1:
        st.markdown(render_metric_card("Processed Resumes", f"{summary['processed_count']}/{summary['total_files']}"), unsafe_allow_html=True)
    with sm2:
        st.markdown(render_metric_card("With Contacts", str(summary["completed_count"])), unsafe_allow_html=True)
    with sm3:
        st.markdown(render_metric_card("Zero Contacts", str(summary["no_email_count"])), unsafe_allow_html=True)
    with sm4:
        st.markdown(render_metric_card("Failed Files", str(summary["failed_count"])), unsafe_allow_html=True)
    with sm5:
        st.markdown(render_metric_card("Unique Emails", str(summary["unique_emails_count"])), unsafe_allow_html=True)
    with sm6:
        st.markdown(render_metric_card("Unique Phones", str(summary.get("unique_phones_count", 0))), unsafe_allow_html=True)

    st.write("")

    # Section 6: Results Tables (Tabs)
    tab1, tab2, tab3 = st.tabs([
        f"✉️ Unique Emails ({len(df_unique)})",
        f"📞 Unique Phone Numbers ({len(df_unique_phones)})",
        f"📑 Resume Mapping ({len(df_mapping)})"
    ])

    with tab1:
        st.markdown("#### Table 1: Unique Email Addresses (Globally Deduplicated)")
        if not df_unique.empty:
            search_email = st.text_input("🔍 Search emails or resumes", key="search_email_box", placeholder="Filter by email or filename...")
            filtered_unique = df_unique
            if search_email:
                q = search_email.lower()
                filtered_unique = df_unique[
                    df_unique["Email Address"].str.lower().str.contains(q, na=False) |
                    df_unique["Found in Resume(s)"].str.lower().str.contains(q, na=False)
                ]
            st.dataframe(filtered_unique, use_container_width=True, hide_index=True, height=350)
            st.caption(f"Showing {len(filtered_unique)} of {len(df_unique)} unique emails.")
        else:
            st.info("No emails were extracted from the processed files.")

    with tab2:
        st.markdown("#### Table 2: Unique Phone Numbers (Globally Deduplicated)")
        if not df_unique_phones.empty:
            search_phone = st.text_input("🔍 Search phone numbers or resumes", key="search_phone_box", placeholder="Filter by phone number or filename...")
            filtered_phones = df_unique_phones
            if search_phone:
                qp = search_phone.lower()
                filtered_phones = df_unique_phones[
                    df_unique_phones["Phone Number"].str.lower().str.contains(qp, na=False) |
                    df_unique_phones["Found in Resume(s)"].str.lower().str.contains(qp, na=False)
                ]
            st.dataframe(filtered_phones, use_container_width=True, hide_index=True, height=350)
            st.caption(f"Showing {len(filtered_phones)} of {len(df_unique_phones)} unique phone numbers.")
        else:
            st.info("No phone numbers were extracted from the processed files.")

    with tab3:
        st.markdown("#### Table 3: Resume Extraction Details")
        if not df_mapping.empty:
            f_col1, f_col2 = st.columns([1, 2])
            with f_col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=["All", "Completed", "No Contacts Found", "Failed"],
                    index=0
                )
            with f_col2:
                search_mapping = st.text_input("🔍 Search resume filename, email or phone", key="search_map_box")

            filtered_mapping = df_mapping
            if status_filter != "All":
                filtered_mapping = filtered_mapping[filtered_mapping["Status"] == status_filter]
            if search_mapping:
                qm = search_mapping.lower()
                filtered_mapping = filtered_mapping[
                    filtered_mapping["PDF Filename"].str.lower().str.contains(qm, na=False) |
                    filtered_mapping["Extracted Emails"].str.lower().str.contains(qm, na=False) |
                    filtered_mapping["Extracted Phone Numbers"].str.lower().str.contains(qm, na=False)
                ]

            st.dataframe(filtered_mapping, use_container_width=True, hide_index=True, height=350)
            st.caption(f"Showing {len(filtered_mapping)} of {len(df_mapping)} resume files.")
        else:
            st.info("No resume mapping records available.")


    # Section 7: Mass Mailing & Recruiter BCC Copy
    st.markdown("---")
    st.markdown("### 5. Mass Mailing & Recruiter BCC Copy (Outlook & Gmail)")

    unique_emails_list = df_unique["Email Address"].tolist() if (not df_unique.empty and "Email Address" in df_unique.columns) else []

    if unique_emails_list:
        st.markdown(
            "Quickly copy pre-formatted recipient strings ready to paste directly into your email client's **BCC field**. "
            "Emails are automatically sliced into batches to prevent provider recipient limits and email spam flags."
        )

        bcc_c1, bcc_c2 = st.columns([1.5, 1])
        with bcc_c1:
            target_client = st.radio(
                "Target Email Client Format",
                options=["Outlook / Microsoft 365 (Semicolon ';')", "Gmail / Webmail / Apple Mail (Comma ',')"],
                index=0,
                horizontal=True,
                help="Outlook requires semicolons between addresses; Gmail and standard webmail use commas."
            )
            is_outlook = "Outlook" in target_client

        with bcc_c2:
            batch_choice = st.selectbox(
                "Batch Slicer Size (Recipients per Email)",
                options=["50 recipients (Recommended)", "25 recipients", "75 recipients", "100 recipients", "All in one batch"],
                index=0,
                help="Sending to 50 recipients per email keeps email deliverability high and avoids provider sending blocks."
            )
            if "25" in batch_choice:
                batch_sz = 25
            elif "75" in batch_choice:
                batch_sz = 75
            elif "100" in batch_choice:
                batch_sz = 100
            elif "All" in batch_choice:
                batch_sz = len(unique_emails_list)
            else:
                batch_sz = 50

        email_batches = slice_emails_into_batches(unique_emails_list, batch_size=batch_sz)

        # Batch summary badges
        st.caption(
            f"📦 **{len(unique_emails_list)}** total unique recipients sliced into **{len(email_batches)}** batch(es) "
            f"of up to **{batch_sz}** recipients each."
        )

        # Render Batch Tabs or Expanders
        if len(email_batches) == 1:
            b = email_batches[0]
            copy_text = b["outlook_str"] if is_outlook else b["gmail_str"]
            st.markdown(f"**Ready-to-copy string ({b['total_in_batch']} recipients):** *(Click icon in top-right of box to copy)*")
            st.code(copy_text, language=None)
        else:
            # Create tabs for the batches (show up to 10 tabs cleanly, or selector for very large sets)
            if len(email_batches) <= 12:
                batch_tabs = st.tabs([f"Batch {b['batch_number']} ({b['start_index']}–{b['end_index']})" for b in email_batches])
                for idx, b_tab in enumerate(batch_tabs):
                    with b_tab:
                        b = email_batches[idx]
                        copy_text = b["outlook_str"] if is_outlook else b["gmail_str"]
                        st.markdown(
                            f"**Batch {b['batch_number']} of {len(email_batches)}** — "
                            f"`{b['total_in_batch']}` recipients (Emails {b['start_index']} to {b['end_index']}): "
                            f"*(Click copy icon in top-right of box)*"
                        )
                        st.code(copy_text, language=None)
            else:
                # Dropdown for large batches
                selected_batch_idx = st.selectbox(
                    "Select Batch to Copy",
                    options=list(range(len(email_batches))),
                    format_func=lambda i: f"Batch {email_batches[i]['batch_number']} (Emails {email_batches[i]['start_index']}–{email_batches[i]['end_index']}, {email_batches[i]['total_in_batch']} recipients)"
                )
                b = email_batches[selected_batch_idx]
                copy_text = b["outlook_str"] if is_outlook else b["gmail_str"]
                st.markdown(f"**Batch {b['batch_number']}** — **{b['total_in_batch']} recipients:** *(Click copy icon in top-right)*")
                st.code(copy_text, language=None)

        # Quick expander for all emails combined
        with st.expander("📋 View All Emails Combined (Unbatched)"):
            all_sep = "; " if is_outlook else ", "
            st.code(all_sep.join(unique_emails_list), language=None)

        # Download batch text file
        dl_batch_col1, dl_batch_col2 = st.columns(2)
        with dl_batch_col1:
            outlook_text_content = ExportManager.generate_bcc_batches_text(unique_emails_list, batch_size=batch_sz, client="outlook")
            st.download_button(
                label="📄 Download Outlook Batches (.txt)",
                data=outlook_text_content,
                file_name="bcc_batches_outlook.txt",
                mime="text/plain",
                use_container_width=True
            )
        with dl_batch_col2:
            gmail_text_content = ExportManager.generate_bcc_batches_text(unique_emails_list, batch_size=batch_sz, client="gmail")
            st.download_button(
                label="📄 Download Gmail Batches (.txt)",
                data=gmail_text_content,
                file_name="bcc_batches_gmail.txt",
                mime="text/plain",
                use_container_width=True
            )
    else:
        st.info("No unique email addresses available to format for mass mailing.")


    # Section 8: Export Section
    st.markdown("---")
    st.markdown("### 6. Export Results")

    out_folder = st.session_state.output_dir
    st.info(f"Target Output Directory: `{out_folder}`")

    exp_col1, exp_col2 = st.columns([2, 3])

    with exp_col1:
        st.markdown("#### 💾 Save to Computer")
        if st.button("📁 Export All Files to Folder", type="primary", use_container_width=True):
            with st.spinner("Generating formatted workbooks and CSV files..."):
                save_res = ExportManager.save_all_to_directory(
                    output_directory=out_folder,
                    df_unique=df_unique,
                    df_mapping=df_mapping,
                    summary=summary,
                    resume_results=resume_results,
                    df_unique_phones=df_unique_phones
                )
                if save_res["success"]:
                    st.success(f"✅ Successfully saved {len(save_res['files_saved'])} files to `{save_res['output_dir']}`:")
                    for fpath in save_res["files_saved"]:
                        st.markdown(f"- `{os.path.basename(fpath)}`")
                else:
                    st.error(f"❌ {save_res['error_message']}")

    with exp_col2:
        st.markdown("#### 📥 Direct Browser Download")
        dl_row1_col1, dl_row1_col2 = st.columns(2)
        with dl_row1_col1:
            report_buffer = ExportManager.generate_full_report_workbook(
                df_unique, df_mapping, summary, resume_results, df_unique_phones=df_unique_phones
            )
            st.download_button(
                label="📊 extraction_report.xlsx (Full)",
                data=report_buffer,
                file_name="extraction_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with dl_row1_col2:
            unique_xlsx_buffer = ExportManager.generate_single_excel_bytes(df_unique, sheet_name="Unique Emails")
            st.download_button(
                label="✉️ unique_emails.xlsx",
                data=unique_xlsx_buffer,
                file_name="unique_emails.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        dl_row2_col1, dl_row2_col2 = st.columns(2)
        with dl_row2_col1:
            map_xlsx_buffer = ExportManager.generate_single_excel_bytes(df_mapping, sheet_name="Resume Mapping")
            st.download_button(
                label="📑 resume_email_mapping.xlsx",
                data=map_xlsx_buffer,
                file_name="resume_email_mapping.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with dl_row2_col2:
            csv_unique_bytes = ExportManager.generate_csv_bytes(df_unique)
            st.download_button(
                label="📄 unique_emails.csv",
                data=csv_unique_bytes,
                file_name="unique_emails.csv",
                mime="text/csv",
                use_container_width=True
            )

        if not df_unique_phones.empty:
            dl_row3_col1, dl_row3_col2 = st.columns(2)
            with dl_row3_col1:
                phones_xlsx_buffer = ExportManager.generate_single_excel_bytes(df_unique_phones, sheet_name="Unique Phones")
                st.download_button(
                    label="📞 unique_phones.xlsx",
                    data=phones_xlsx_buffer,
                    file_name="unique_phones.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with dl_row3_col2:
                phones_csv_bytes = ExportManager.generate_csv_bytes(df_unique_phones)
                st.download_button(
                    label="📄 unique_phones.csv",
                    data=phones_csv_bytes,
                    file_name="unique_phones.csv",
                    mime="text/csv",
                    use_container_width=True
                )
