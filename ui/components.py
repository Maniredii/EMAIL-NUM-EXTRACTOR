"""
UI Components and Styling Module
Contains custom CSS, header banners, metric cards, and native Windows folder picker.
"""
import sys
import os
import subprocess
import streamlit as st
from typing import Optional


def open_native_folder_dialog(initial_dir: Optional[str] = None) -> str:
    """
    Spawns a native Windows folder picker using Tkinter in a separate isolated process.
    This guarantees non-blocking execution and eliminates Tkinter thread conflicts in Streamlit.
    """
    if sys.platform != "win32":
        return ""

    initial_clean = ""
    if initial_dir and os.path.isdir(initial_dir):
        initial_clean = os.path.normpath(initial_dir).replace('\\', '\\\\')

    script = (
        "import tkinter as tk; "
        "from tkinter import filedialog; "
        "root = tk.Tk(); "
        "root.withdraw(); "
        "root.attributes('-topmost', True); "
        f"selected = filedialog.askdirectory(title='Select Resume Folder', initialdir='{initial_clean}'); "
        "root.destroy(); "
        "print(selected or '')"
    )

    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=120
        )
        if proc.returncode == 0:
            picked = proc.stdout.strip()
            if picked and os.path.isdir(picked):
                return os.path.normpath(picked)
    except Exception:
        pass
    return ""


def apply_custom_css():
    """Injects custom CSS for clean, professional styling."""
    st.markdown("""
        <style>
        /* Base page adjustments */
        .main .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        /* Header styling */
        .header-container {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            padding: 24px 28px;
            border-radius: 12px;
            color: #FFFFFF;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border-left: 6px solid #2563EB;
        }
        .header-title {
            font-size: 2rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.025em;
            color: #F8FAFC;
        }
        .header-subtitle {
            font-size: 1.05rem;
            color: #94A3B8;
            margin-top: 6px;
            margin-bottom: 12px;
        }
        .privacy-badge {
            display: inline-flex;
            align-items: center;
            background-color: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 5px 12px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.04em;
        }

        /* Metric Cards */
        .metric-card {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 14px 18px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 2px;
        }
        .metric-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            font-weight: 600;
            color: #64748B;
            letter-spacing: 0.05em;
        }

        /* Status Pills */
        .status-pill {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .status-completed {
            background-color: #DEF7EC;
            color: #03543F;
        }
        .status-no-emails {
            background-color: #FEF08A;
            color: #713F12;
        }
        .status-failed {
            background-color: #FDE8E8;
            color: #9B1C1C;
        }

        /* Section containers */
        .section-box {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)


def render_header():
    """Renders the top application branding header with privacy badge."""
    st.markdown("""
        <div class="header-container">
            <h1 class="header-title">Resume Email Extractor</h1>
            <div class="header-subtitle">Bulk email extraction from local resume folders</div>
            <div>
                <span class="privacy-badge">
                    🔒 LOCAL PROCESSING — YOUR FILES STAY ON YOUR PC
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, subtext: str = ""):
    """Renders a styled metric card."""
    subtext_html = f"<div style='font-size: 0.75rem; color: #94A3B8; margin-top: 3px;'>{subtext}</div>" if subtext else ""
    return f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {subtext_html}
        </div>
    """
