"""
Desktop Executable Entrypoint for Resume Email & Phone Extractor
"""
import os
import sys
from pathlib import Path
import streamlit.web.cli as stcli

def main():
    # Ensure current working directory is the app directory
    base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)

    app_script = str(base_dir / "app.py")

    sys.argv = [
        "streamlit",
        "run",
        app_script,
        "--global.developmentMode=false",
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
