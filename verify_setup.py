#!/usr/bin/env python3
"""
Quick Setup Verification Script
Run this to verify your environment is properly configured
"""

import sys
import subprocess
import os

def check_python_version():
    """Verify Python version"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python version too old: {version.major}.{version.minor}")
        print("  Please install Python 3.7 or newer")
        return False

def check_package(package_name):
    """Check if a Python package is installed"""
    try:
        __import__(package_name)
        print(f"✓ {package_name} installed")
        return True
    except ImportError:
        print(f"✗ {package_name} NOT installed")
        return False

def check_ffmpeg():
    """Check if ffmpeg is installed"""
    print("Checking for ffmpeg...")
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ {version}")
            return True
        else:
            print("✗ ffmpeg found but returned error")
            return False
    except FileNotFoundError:
        print("✗ ffmpeg NOT found")
        print("  Install instructions:")
        print("    Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("    macOS: brew install ffmpeg")
        print("    Windows: Download from https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"✗ Error checking ffmpeg: {e}")
        return False

def check_files():
    """Verify all required files exist"""
    print("\nChecking project files...")
    required_files = [
        'generate_stimuli.py',
        'index.html',
        'experiment.js',
        'google-apps-script.gs',
        'README.md'
    ]
    
    all_exist = True
    for filename in required_files:
        if os.path.exists(filename):
            print(f"✓ {filename}")
        else:
            print(f"✗ {filename} NOT FOUND")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("PSYCHOACOUSTIC EXPERIMENT SETUP VERIFICATION")
    print("=" * 60)
    print()
    
    checks = []
    
    # Check Python
    checks.append(check_python_version())
    print()
    
    # Check Python packages
    print("Checking Python packages...")
    checks.append(check_package('numpy'))
    checks.append(check_package('librosa'))
    checks.append(check_package('pydub'))
    print()
    
    # Check ffmpeg
    checks.append(check_ffmpeg())
    print()
    
    # Check files
    checks.append(check_files())
    print()
    
    # Summary
    print("=" * 60)
    if all(checks):
        print("✓ ALL CHECKS PASSED - You're ready to generate stimuli!")
        print()
        print("Next steps:")
        print("1. Run: python generate_stimuli.py")
        print("2. Set up Google Sheets (see README.md)")
        print("3. Configure experiment.js with your Google Apps Script URL")
        print("4. Deploy to web hosting (GitHub Pages or Netlify)")
    else:
        print("✗ SOME CHECKS FAILED - Please fix issues above")
        print()
        print("Quick fixes:")
        print("  Missing packages: pip install -r requirements.txt")
        print("  Missing ffmpeg: See installation instructions above")
    print("=" * 60)

if __name__ == "__main__":
    main()
