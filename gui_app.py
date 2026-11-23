"""
Ultra-Lightweight Native Windows GUI for Bulk Resume Email & Phone Extractor.
Designed specifically for older, low-spec laptops (requires < 30 MB RAM, no browser needed).
Includes Duplicate Count tracking, Tabbed Views, Live Search/Filter, and Excel/CSV exports.
"""
import os
import sys
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.folder_scanner import scan_folder
from core.processor import BatchProcessor
from core.export_manager import ExportManager
from core.email_extractor import format_emails_for_client, slice_emails_into_batches


class LightweightExtractorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Resume Email & Phone Extractor - Desktop Edition")
        self.root.geometry("960x680")
        self.root.minsize(800, 540)

        self.folder_path = tk.StringVar(value="")
        self.recursive_var = tk.BooleanVar(value=True)
        self.docx_var = tk.BooleanVar(value=True)
        self.search_var = tk.StringVar(value="")

        self.processor = None
        self.stop_event = threading.Event()
        self.is_processing = False
        self.result_data = None
        self.msg_queue = queue.Queue()

        # Cache data for instant live search/filtering
        self.all_email_rows = []
        self.all_phone_rows = []
        self.all_file_rows = []

        self._apply_styles()
        self._build_ui()

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#1E3A8A")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#4B5563")
        style.configure("Metric.TLabel", font=("Segoe UI", 11, "bold"), foreground="#0F766E")
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[10, 4])

    def _build_ui(self):
        # 1. Header Frame
        header_frame = ttk.Frame(self.root, padding="15 10 15 5")
        header_frame.pack(fill=tk.X)

        title = ttk.Label(header_frame, text="⚡ Resume Email & Phone Extractor", style="Header.TLabel")
        title.pack(anchor=tk.W)
        subtitle = ttk.Label(
            header_frame,
            text="High-speed, offline desktop resume scanner with duplicate counting and 1-click export.",
            style="SubHeader.TLabel"
        )
        subtitle.pack(anchor=tk.W, pady=(2, 0))

        # 2. Folder Selection Frame
        input_frame = ttk.LabelFrame(self.root, text=" 1. Select Resume Folder ", padding="10")
        input_frame.pack(fill=tk.X, padx=15, pady=4)

        path_row = ttk.Frame(input_frame)
        path_row.pack(fill=tk.X, pady=(2, 6))

        ttk.Label(path_row, text="Resume Folder:").pack(side=tk.LEFT, padx=(0, 8))
        self.path_entry = ttk.Entry(path_row, textvariable=self.folder_path, font=("Segoe UI", 10))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        browse_btn = ttk.Button(path_row, text="📁 Browse...", command=self._browse_folder)
        browse_btn.pack(side=tk.RIGHT)

        # Options Row
        opt_row = ttk.Frame(input_frame)
        opt_row.pack(fill=tk.X)

        rec_check = ttk.Checkbutton(opt_row, text="Search subfolders recursively", variable=self.recursive_var)
        rec_check.pack(side=tk.LEFT, padx=(0, 20))

        docx_check = ttk.Checkbutton(opt_row, text="Include DOCX and TXT files", variable=self.docx_var)
        docx_check.pack(side=tk.LEFT)

        if os.path.isdir("Sample_Resumes"):
            sample_btn = ttk.Button(opt_row, text="✨ Load Sample Resumes", command=self._load_sample_resumes)
            sample_btn.pack(side=tk.RIGHT)

        # 3. Execution & Progress Bar
        action_frame = ttk.Frame(self.root, padding="15 4")
        action_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(
            action_frame,
            text="🚀 Start Extraction",
            style="Action.TButton",
            command=self._start_extraction
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(
            action_frame,
            text="⏹ Stop",
            state=tk.DISABLED,
            command=self._stop_extraction
        )
        self.stop_btn.pack(side=tk.LEFT)

        self.status_label = ttk.Label(action_frame, text="Ready. Select folder and click Start Extraction.", foreground="#374151")
        self.status_label.pack(side=tk.RIGHT)

        self.progress_bar = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, padx=15, pady=(2, 4))

        # 4. Metrics Summary Bar
        metrics_frame = ttk.Frame(self.root, padding="15 2")
        metrics_frame.pack(fill=tk.X)

        self.metric_files = ttk.Label(metrics_frame, text="Files: 0", style="Metric.TLabel")
        self.metric_files.pack(side=tk.LEFT, padx=(0, 25))

        self.metric_emails = ttk.Label(metrics_frame, text="Unique Emails: 0", style="Metric.TLabel")
        self.metric_emails.pack(side=tk.LEFT, padx=(0, 25))

        self.metric_phones = ttk.Label(metrics_frame, text="Unique Phones: 0", style="Metric.TLabel")
        self.metric_phones.pack(side=tk.LEFT, padx=(0, 25))

        # 5. Tabbed Results View
        table_frame = ttk.LabelFrame(self.root, text=" 2. Extracted Results ", padding="8")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=4)

        # Live Search & Filter Bar
        search_row = ttk.Frame(table_frame)
        search_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(search_row, text="🔍 Search / Filter:").pack(side=tk.LEFT, padx=(0, 6))
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=32)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 6))
        self.search_var.trace_add("write", lambda *args: self._filter_active_table())

        clear_btn = ttk.Button(search_row, text="Clear", command=lambda: self.search_var.set(""))
        clear_btn.pack(side=tk.LEFT)

        self.match_count_label = ttk.Label(search_row, text="", foreground="#6B7280")
        self.match_count_label.pack(side=tk.RIGHT)

        # Notebook with 3 tabs
        self.notebook = ttk.Notebook(table_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._filter_active_table())

        # Tab 1: Unique Emails
        self.frame_emails = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_emails, text="  📧 Unique Emails (0)  ")
        self.tree_emails = self._create_tree(
            self.frame_emails,
            columns=("sn", "email", "count", "resumes"),
            headings={"sn": "#", "email": "Email Address", "count": "Duplicate Count", "resumes": "Found in Resume(s)"},
            widths={"sn": 50, "email": 280, "count": 120, "resumes": 420}
        )

        # Tab 2: Unique Phones
        self.frame_phones = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_phones, text="  📱 Unique Phones (0)  ")
        self.tree_phones = self._create_tree(
            self.frame_phones,
            columns=("sn", "phone", "count", "resumes"),
            headings={"sn": "#", "phone": "Phone Number", "count": "Duplicate Count", "resumes": "Found in Resume(s)"},
            widths={"sn": 50, "phone": 220, "count": 120, "resumes": 480}
        )

        # Tab 3: Resume Files Mapping
        self.frame_files = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_files, text="  📄 Resume Files Mapping (0)  ")
        self.tree_files = self._create_tree(
            self.frame_files,
            columns=("filename", "emails", "phones", "status"),
            headings={"filename": "Resume Filename", "emails": "Extracted Email(s)", "phones": "Extracted Phone(s)", "status": "Status"},
            widths={"filename": 240, "emails": 280, "phones": 220, "status": 90}
        )

        # 6. Export Actions Frame
        export_frame = ttk.LabelFrame(self.root, text=" 3. Export & Recruiter Tools ", padding="8")
        export_frame.pack(fill=tk.X, padx=15, pady=(4, 10))

        self.btn_excel = ttk.Button(
            export_frame, text="📊 Save Excel Report (.xlsx)", state=tk.DISABLED, command=self._export_excel
        )
        self.btn_excel.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_csv = ttk.Button(
            export_frame, text="📄 Save CSV (.csv)", state=tk.DISABLED, command=self._export_csv
        )
        self.btn_csv.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_copy_phones = ttk.Button(
            export_frame, text="📱 Copy All Phones", state=tk.DISABLED, command=self._copy_phones
        )
        self.btn_copy_phones.pack(side=tk.RIGHT, padx=(4, 0))

        self.btn_bcc_outlook = ttk.Button(
            export_frame, text="📋 Copy Outlook BCC (;)", state=tk.DISABLED, command=lambda: self._copy_bcc(";")
        )
        self.btn_bcc_outlook.pack(side=tk.RIGHT, padx=(4, 0))

        self.btn_bcc_gmail = ttk.Button(
            export_frame, text="📋 Copy Gmail BCC (,)", state=tk.DISABLED, command=lambda: self._copy_bcc(",")
        )
        self.btn_bcc_gmail.pack(side=tk.RIGHT)

    def _create_tree(self, parent, columns, headings, widths):
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            tree.heading(col, text=headings[col], anchor=tk.W)
            tree.column(col, width=widths[col], minwidth=widths[col] // 2)

        scroll_y = ttk.Scrollbar(container, orient=tk.VERTICAL, command=tree.yview)
        scroll_x = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Style tag for rows with duplicate count > 1
        tree.tag_configure("duplicate", background="#EFF6FF", foreground="#1E40AF")
        return tree

    def _browse_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self.folder_path.get() or os.getcwd(),
            title="Select Resume Folder"
        )
        if chosen:
            self.folder_path.set(chosen)

    def _load_sample_resumes(self):
        sample_dir = str(Path("Sample_Resumes").resolve())
        self.folder_path.set(sample_dir)

    def _start_extraction(self):
        path = self.folder_path.get().strip()
        if not path or not os.path.isdir(path):
            messagebox.showerror("Invalid Folder", "Please choose a valid existing folder containing resumes.")
            return

        # Prepare file types
        file_types = [".pdf"]
        if self.docx_var.get():
            file_types.extend([".docx", ".doc", ".txt"])

        # Scan folder
        scan_res = scan_folder(folder_path=path, recursive=self.recursive_var.get(), file_types=file_types)
        if not scan_res["is_valid"]:
            messagebox.showerror("Error Scanning Folder", scan_res["error_message"])
            return

        if scan_res["total_files"] == 0:
            messagebox.showwarning("No Resumes Found", "No matching PDF/DOCX files were found in this folder.")
            return

        # Clear existing tables & caches
        for t in (self.tree_emails, self.tree_phones, self.tree_files):
            for item in t.get_children():
                t.delete(item)

        self.all_email_rows.clear()
        self.all_phone_rows.clear()
        self.all_file_rows.clear()
        self.search_var.set("")

        # Switch to Files tab during processing
        self.notebook.select(self.frame_files)

        # Set up processor
        self.stop_event.clear()
        self.processor = BatchProcessor(
            files=scan_res["files"],
            enable_ocr=False,
            progress_callback=self._on_progress_callback,
            stop_event=self.stop_event
        )

        self.is_processing = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.btn_excel.config(state=tk.DISABLED)
        self.btn_csv.config(state=tk.DISABLED)
        self.btn_bcc_gmail.config(state=tk.DISABLED)
        self.btn_bcc_outlook.config(state=tk.DISABLED)
        self.btn_copy_phones.config(state=tk.DISABLED)

        self.progress_bar["maximum"] = scan_res["total_files"]
        self.progress_bar["value"] = 0

        # Start queue processing on main thread
        self.root.after(40, self._process_queue)

        # Run extraction in worker thread
        threading.Thread(target=self._run_worker, daemon=True).start()

    def _on_progress_callback(self, payload: dict):
        self.msg_queue.put(("progress", payload))

    def _process_queue(self):
        while not self.msg_queue.empty():
            try:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "progress":
                    self._update_ui_progress(data)
                elif msg_type == "finished":
                    self._extraction_finished(data)
                elif msg_type == "error":
                    self._extraction_error(data)
            except queue.Empty:
                break

        if self.is_processing:
            self.root.after(40, self._process_queue)

    def _update_ui_progress(self, payload: dict):
        current = payload.get("current_index", 0)
        total = payload.get("total_files", 0)
        filename = payload.get("current_filename", "")
        self.progress_bar["value"] = current
        self.status_label.config(text=f"Processing ({current}/{total}): {filename[:32]}...")

        self.metric_files.config(text=f"Files Processed: {current}/{total}")
        self.metric_emails.config(text=f"Unique Emails: {payload.get('unique_emails_count', 0)}")
        self.metric_phones.config(text=f"Unique Phones: {payload.get('unique_phones_count', 0)}")

        # Append last processed resume to files table
        last_res = payload.get("last_result")
        if last_res:
            emails_str = "; ".join(last_res.get("emails", [])) if last_res.get("emails") else "—"
            phones_list = last_res.get("phones", [])
            phones_str = "; ".join(phones_list) if phones_list else "—"
            status = last_res.get("status", "Completed")

            row_tuple = (last_res.get("filename", ""), emails_str, phones_str, status)
            self.all_file_rows.append(row_tuple)
            self.tree_files.insert("", tk.END, values=row_tuple)
            children = self.tree_files.get_children()
            if children:
                self.tree_files.see(children[-1])

    def _run_worker(self):
        try:
            final_res = self.processor.process()
            self.msg_queue.put(("finished", final_res))
        except Exception as e:
            self.msg_queue.put(("error", str(e)))

    def _extraction_error(self, err_msg: str):
        self.is_processing = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="❌ Error occurred during extraction.")
        messagebox.showerror("Extraction Error", f"An error occurred during extraction:\n{err_msg}")

    def _extraction_finished(self, final_res):
        self.result_data = final_res
        self.is_processing = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        summary = final_res.get("summary", {})
        df_emails = final_res.get("df_unique_emails")
        df_phones = final_res.get("df_unique_phones")
        total_files = summary.get("processed_count", len(final_res.get("resume_results", [])))

        emails_count = len(df_emails) if df_emails is not None else 0
        phones_count = len(df_phones) if df_phones is not None else 0

        self.metric_files.config(text=f"Files Processed: {total_files}")
        self.metric_emails.config(text=f"Unique Emails: {emails_count}")
        self.metric_phones.config(text=f"Unique Phones: {phones_count}")

        # 1. Populate Tab 1: Unique Emails (No duplicates! Shows duplicate count)
        self.all_email_rows.clear()
        if df_emails is not None and not df_emails.empty:
            for _, r in df_emails.iterrows():
                sn = r.get("Serial Number", "")
                em = r.get("Email Address", "")
                cnt = r.get("Number of Resumes", 1)
                res = r.get("Found in Resume(s)", "")
                row = (sn, em, f"{cnt} resume{'s' if cnt > 1 else ''}", res)
                self.all_email_rows.append(row)

        # 2. Populate Tab 2: Unique Phones (No duplicates! Shows duplicate count)
        self.all_phone_rows.clear()
        if df_phones is not None and not df_phones.empty:
            for _, r in df_phones.iterrows():
                sn = r.get("Serial Number", "")
                ph = r.get("Phone Number", "")
                cnt = r.get("Number of Resumes", 1)
                res = r.get("Found in Resume(s)", "")
                row = (sn, ph, f"{cnt} resume{'s' if cnt > 1 else ''}", res)
                self.all_phone_rows.append(row)

        # Refresh tables
        self._refresh_table(self.tree_emails, self.all_email_rows)
        self._refresh_table(self.tree_phones, self.all_phone_rows)

        # Update Tab headers
        self.notebook.tab(0, text=f"  📧 Unique Emails ({emails_count})  ")
        self.notebook.tab(1, text=f"  📱 Unique Phones ({phones_count})  ")
        self.notebook.tab(2, text=f"  📄 Resume Files ({total_files})  ")

        # Automatically switch to Unique Emails view
        self.notebook.select(self.frame_emails)

        # Enable export & action buttons
        if emails_count > 0 or phones_count > 0:
            self.btn_excel.config(state=tk.NORMAL)
            self.btn_csv.config(state=tk.NORMAL)
            if emails_count > 0:
                self.btn_bcc_gmail.config(state=tk.NORMAL)
                self.btn_bcc_outlook.config(state=tk.NORMAL)
            if phones_count > 0:
                self.btn_copy_phones.config(state=tk.NORMAL)

        self.status_label.config(
            text=f"✅ Done! Extracted {emails_count} unique emails & {phones_count} unique phone numbers."
        )

        messagebox.showinfo(
            "Extraction Complete",
            f"Successfully processed {total_files} resume files!\n\n"
            f"• Unique Emails Found: {emails_count}\n"
            f"• Unique Phone Numbers Found: {phones_count}\n\n"
            f"Each email and phone number is deduplicated with duplicate counts shown in the table.\n"
            f"You can now export reports or copy contact lists below."
        )

    def _refresh_table(self, tree, rows):
        for item in tree.get_children():
            tree.delete(item)
        for r in rows:
            # Highlight duplicate count > 1
            is_dup = False
            if len(r) > 2 and ("resumes" in str(r[2]).lower()):
                try:
                    num = int(str(r[2]).split()[0])
                    if num > 1:
                        is_dup = True
                except Exception:
                    pass
            tag = ("duplicate",) if is_dup else ()
            tree.insert("", tk.END, values=r, tags=tag)

    def _filter_active_table(self):
        query = self.search_var.get().strip().lower()
        active_tab = self.notebook.index("current")

        if active_tab == 0:
            tree = self.tree_emails
            dataset = self.all_email_rows
        elif active_tab == 1:
            tree = self.tree_phones
            dataset = self.all_phone_rows
        else:
            tree = self.tree_files
            dataset = self.all_file_rows

        if not query:
            self._refresh_table(tree, dataset)
            self.match_count_label.config(text="")
            return

        filtered = [row for row in dataset if any(query in str(col).lower() for col in row)]
        self._refresh_table(tree, filtered)
        self.match_count_label.config(text=f"Showing {len(filtered)} of {len(dataset)} matches")

    def _stop_extraction(self):
        if self.stop_event and self.is_processing:
            self.stop_event.set()
            self.status_label.config(text="Stopping process gracefully...")

    def _export_excel(self):
        if not self.result_data:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="Resume_Extraction_Report.xlsx",
            title="Save Excel Report"
        )
        if save_path:
            try:
                wb_io = ExportManager.generate_full_report_workbook(
                    df_unique=self.result_data["df_unique_emails"],
                    df_mapping=self.result_data["df_resume_mapping"],
                    summary=self.result_data["summary"],
                    resume_results=self.result_data["resume_results"],
                    df_unique_phones=self.result_data.get("df_unique_phones")
                )
                with open(save_path, "wb") as f:
                    f.write(wb_io.getbuffer())

                # Offer to open the folder location immediately!
                if messagebox.askyesno(
                    "Export Successful",
                    f"Excel report saved successfully to:\n{save_path}\n\nDo you want to open the file location now?"
                ):
                    abs_path = os.path.abspath(save_path)
                    os.system(f'explorer /select,"{abs_path}"')

            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not save Excel file: {e}")

    def _export_csv(self):
        if not self.result_data:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile="Resume_Emails_and_Phones.csv",
            title="Save CSV Report"
        )
        if save_path:
            try:
                # Export the full mapping dataframe with Filename, Emails, and Phone numbers
                df_export = self.result_data.get("df_resume_mapping")
                if df_export is None or df_export.empty:
                    df_export = self.result_data.get("df_unique_emails")
                csv_bytes = ExportManager.generate_csv_bytes(df_export)
                with open(save_path, "wb") as f:
                    f.write(csv_bytes)

                if messagebox.askyesno(
                    "Export Successful",
                    f"CSV report saved successfully to:\n{save_path}\n\nDo you want to open the file location now?"
                ):
                    abs_path = os.path.abspath(save_path)
                    os.system(f'explorer /select,"{abs_path}"')

            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not save CSV file: {e}")

    def _copy_phones(self):
        if not self.result_data:
            return
        df_phones = self.result_data.get("df_unique_phones")
        if df_phones is not None and not df_phones.empty and "Phone Number" in df_phones.columns:
            phones = df_phones["Phone Number"].dropna().tolist()
        else:
            phones = []

        if not phones:
            messagebox.showinfo("No Phone Numbers", "No phone numbers were found to copy.")
            return

        phones_str = ", ".join(phones)
        self.root.clipboard_clear()
        self.root.clipboard_append(phones_str)
        self.root.update()
        messagebox.showinfo("Copied to Clipboard", f"Copied {len(phones)} unique phone numbers to clipboard!")

    def _copy_bcc(self, separator: str):
        if not self.result_data:
            return
        df_emails = self.result_data.get("df_unique_emails")
        emails = df_emails["Email Address"].dropna().tolist() if df_emails is not None and "Email Address" in df_emails.columns else []
        if not emails:
            messagebox.showinfo("No Emails", "No email addresses found to copy.")
            return

        bcc_string = separator.join(emails)
        self.root.clipboard_clear()
        self.root.clipboard_append(bcc_string)
        self.root.update()

        client_name = "Outlook" if separator == ";" else "Gmail"
        messagebox.showinfo(
            "Copied to Clipboard",
            f"Copied {len(emails)} unique email addresses formatted for {client_name} BCC field!"
        )


def main():
    root = tk.Tk()
    app = LightweightExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
