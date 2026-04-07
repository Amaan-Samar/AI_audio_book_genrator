#!/usr/bin/env python3
"""
Setup script for PDF Audio Extractor
Run this to install dependencies and verify setup
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Packages installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False
    return True

def verify_setup():
    """Verify folder structure and files"""
    print("\n🔍 Verifying setup...")
    
    required_dirs = ['input_pdfs', 'output_text', 'scripts', 'config', 'logs']
    required_files = ['requirements.txt', 'run_extractor.py', 'config/settings.json']
    
    all_ok = True
    
    # Check directories
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"  ✓ {dir_name}/ exists")
        else:
            print(f"  ✗ {dir_name}/ missing - creating...")
            os.makedirs(dir_name, exist_ok=True)
    
    # Check files
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"  ✓ {file_name} exists")
        else:
            print(f"  ✗ {file_name} missing")
            all_ok = False
    
    return all_ok

    # def create_sample_pdf_note():
    #     """Create a README about adding PDFs"""
    #     readme_content = """# PDF Audio Extractor

    #     ## Quick Start

    #     1. **Place your PDF files** in the `input_pdfs/` folder
    #     2. **Run the extractor**:
    #     ```bash
    #     python run_extractor.py input_pdfs/your_file.pdf