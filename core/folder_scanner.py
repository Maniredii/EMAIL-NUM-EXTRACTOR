"""
Folder Scanner Module
Recursively scans local directories for PDF and other resume files.
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime


def format_file_size(size_bytes: int) -> str:
    """Convert bytes into a human-readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def scan_folder(
    folder_path: str,
    recursive: bool = True,
    file_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Scans a folder for resume files with comprehensive validation and metadata.

    Args:
        folder_path: Path string of the local directory to scan.
        recursive: Whether to scan subfolders recursively.
        file_types: List of allowed file extensions (e.g. ['.pdf']). Default: ['.pdf'].

    Returns:
        Dict containing:
            - is_valid (bool)
            - error_message (str)
            - total_files (int)
            - total_folders_searched (int)
            - total_size_bytes (int)
            - total_size_str (str)
            - files (List[Dict[str, Any]])
    """
    if file_types is None:
        file_types = [".pdf"]
    
    # Normalize extensions to lowercase with leading dot
    normalized_types = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in file_types}

    result: Dict[str, Any] = {
        "is_valid": False,
        "error_message": "",
        "total_files": 0,
        "total_folders_searched": 0,
        "total_size_bytes": 0,
        "total_size_str": "0 B",
        "files": []
    }

    if not folder_path or not str(folder_path).strip():
        result["error_message"] = "Folder path cannot be empty."
        return result

    cleaned_path = str(folder_path).strip().strip('"').strip("'")
    
    try:
        resolved_root = Path(cleaned_path).resolve()
    except Exception as e:
        result["error_message"] = f"Invalid folder path format: {str(e)}"
        return result

    if not resolved_root.exists():
        result["error_message"] = f"The directory does not exist: {resolved_root}"
        return result

    if not resolved_root.is_dir():
        result["error_message"] = f"The specified path is a file, not a directory: {resolved_root}"
        return result

    try:
        # Check read permission
        _ = list(os.scandir(resolved_root))
    except PermissionError:
        result["error_message"] = f"Access denied: You do not have permission to read directory {resolved_root}"
        return result
    except Exception as e:
        result["error_message"] = f"Error accessing directory: {str(e)}"
        return result

    discovered_files: List[Dict[str, Any]] = []
    seen_paths: Set[str] = set()
    total_size = 0
    folders_searched = 0

    try:
        if recursive:
            for root, dirs, files in os.walk(resolved_root, topdown=True, followlinks=False):
                folders_searched += 1
                for filename in files:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in normalized_types:
                        full_path = os.path.normpath(os.path.join(root, filename))
                        if full_path in seen_paths:
                            continue
                        seen_paths.add(full_path)
                        
                        try:
                            stat_info = os.stat(full_path)
                            size_bytes = stat_info.st_size
                            mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            size_bytes = 0
                            mtime = "Unknown"

                        try:
                            rel_path = os.path.relpath(full_path, resolved_root)
                        except ValueError:
                            rel_path = filename

                        total_size += size_bytes
                        discovered_files.append({
                            "filename": filename,
                            "full_path": full_path,
                            "relative_path": rel_path,
                            "parent_folder": os.path.basename(root) if root != str(resolved_root) else ".",
                            "extension": ext,
                            "size_bytes": size_bytes,
                            "size_str": format_file_size(size_bytes),
                            "modified_time": mtime
                        })
        else:
            folders_searched = 1
            with os.scandir(resolved_root) as entries:
                for entry in entries:
                    if entry.is_file():
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in normalized_types:
                            full_path = os.path.normpath(entry.path)
                            if full_path in seen_paths:
                                continue
                            seen_paths.add(full_path)
                            
                            try:
                                stat_info = entry.stat()
                                size_bytes = stat_info.st_size
                                mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                size_bytes = 0
                                mtime = "Unknown"

                            total_size += size_bytes
                            discovered_files.append({
                                "filename": entry.name,
                                "full_path": full_path,
                                "relative_path": entry.name,
                                "parent_folder": ".",
                                "extension": ext,
                                "size_bytes": size_bytes,
                                "size_str": format_file_size(size_bytes),
                                "modified_time": mtime
                            })

    except PermissionError as pe:
        result["error_message"] = f"Permission denied while reading subdirectories: {str(pe)}"
        return result
    except Exception as e:
        result["error_message"] = f"Error during folder scan: {str(e)}"
        return result

    result["is_valid"] = True
    result["total_files"] = len(discovered_files)
    result["total_folders_searched"] = folders_searched
    result["total_size_bytes"] = total_size
    result["total_size_str"] = format_file_size(total_size)
    result["files"] = discovered_files
    return result
