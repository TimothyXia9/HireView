#!/usr/bin/env python3
"""
Build script to create a standalone executable of the Python backend
"""
import os
import subprocess
import sys
import shutil
from pathlib import Path

def build_executable():
    """Build the Python app using PyInstaller"""

    # Get current directory
    current_dir = Path(__file__).parent

    # Define paths
    app_file = current_dir / "app.py"
    dist_dir = current_dir / "dist"
    build_dir = current_dir / "build"

    # Clean previous builds
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # Create a single executable file
        "--windowed",  # Don't show console window
        "--name", "resume_analyzer",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--add-data", "*.py;.",  # Include all Python files
        "--hidden-import", "gradio",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "pdfplumber",
        "--hidden-import", "gradio_client",
        "--hidden-import", "websockets",
        "--hidden-import", "httpx",
        str(app_file)
    ]

    print(f"Building executable with command: {' '.join(cmd)}")

    try:
        # Run PyInstaller
        result = subprocess.run(cmd, cwd=current_dir, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(f"Executable created at: {dist_dir / 'resume_analyzer.exe'}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)