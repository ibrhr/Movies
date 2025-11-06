#!/usr/bin/env python3
"""
Setup verification script.
Run this to ensure your environment is ready.
"""

import sys
import subprocess

def check_python_version():
    """Check if Python version is 3.11+"""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 11:
        print("   ✅ Python version OK")
        return True
    else:
        print("   ❌ Python 3.11+ required")
        return False

def check_venv():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        print("✅ Running in virtual environment")
        return True
    else:
        print("⚠️  Not in virtual environment (recommended)")
        return True  # Not critical

def check_env_file():
    """Check if .env file exists"""
    from pathlib import Path
    
    if Path(".env").exists():
        print("✅ .env file found")
        return True
    else:
        print("⚠️  .env file not found (copy from .env.example)")
        return False

def check_directories():
    """Check if required directories exist"""
    from pathlib import Path
    
    required_dirs = ["data", "scripts", "app", "tests"]
    all_exist = True
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/ missing")
            all_exist = False
    
    if all_exist:
        print("✅ All directories present")
    
    return all_exist

def main():
    print("🔍 Checking project setup...\n")
    
    checks = [
        check_python_version(),
        check_venv(),
        check_directories(),
        check_env_file(),
    ]
    
    print("\n" + "="*50)
    
    if all(checks):
        print("✅ Setup looks good! You're ready to start.")
        print("\nNext steps:")
        print("1. Add your TMDB API key to .env")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run: python scripts/create_database.py")
    else:
        print("⚠️  Some issues found. Please fix them before continuing.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
