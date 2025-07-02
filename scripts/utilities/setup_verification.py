#!/usr/bin/env python3
"""
GeopolMonitor Setup Verification Script

This script verifies that all necessary dependencies and configurations
are properly set up for the Telegram Live Feed Integration feature.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Tuple
import importlib


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        return True, f"✅ Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"❌ Python {version.major}.{version.minor}.{version.micro} (requires Python 3.8+)"


def check_virtual_environment() -> Tuple[bool, str]:
    """Check if running in a virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    venv_path = os.environ.get('VIRTUAL_ENV', 'Not detected')
    
    if in_venv:
        return True, f"✅ Virtual environment active: {venv_path}"
    else:
        return False, "❌ No virtual environment detected (recommended for development)"


def check_required_packages() -> List[Tuple[str, bool, str]]:
    """Check if all required packages are installed"""
    required_packages = [
        # Core web framework
        ('fastapi', 'FastAPI web framework'),
        ('uvicorn', 'ASGI server'),
        ('websockets', 'WebSocket support'),
        
        # Database and caching
        ('sqlalchemy', 'Database ORM'),
        ('redis', 'Redis client'),
        ('alembic', 'Database migrations'),
        
        # Telegram clients
        ('pyrogram', 'Current Telegram client'),
        ('telethon', 'Alternative Telegram client for large-scale monitoring'),
        
        # AI and processing
        ('google.generativeai', 'Google Gemini AI'),
        ('aiohttp', 'Async HTTP client'),
        ('beautifulsoup4', 'HTML parsing'),
        
        # Utilities
        ('python_dotenv', 'Environment variable management'),
        ('pytest', 'Testing framework'),
    ]
    
    results = []
    for package, description in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            results.append((package, True, f"✅ {description}"))
        except ImportError:
            results.append((package, False, f"❌ {description} - Not installed"))
    
    return results


def check_environment_variables() -> List[Tuple[str, bool, str]]:
    """Check if required environment variables are set"""
    required_env_vars = [
        ('TELEGRAM_API_ID', 'Telegram API ID from my.telegram.org'),
        ('TELEGRAM_API_HASH', 'Telegram API Hash from my.telegram.org'),
        ('REDIS_URL', 'Redis connection URL'),
        ('GEMINI_API_KEY', 'Google Gemini API key'),
    ]
    
    results = []
    for var_name, description in required_env_vars:
        value = os.getenv(var_name)
        if value and value.strip():
            # Don't show the actual value for security
            masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
            results.append((var_name, True, f"✅ {description} (set: {masked_value})"))
        else:
            results.append((var_name, False, f"❌ {description} - Not set"))
    
    return results


def check_redis_connection() -> Tuple[bool, str]:
    """Check if Redis is accessible"""
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, socket_connect_timeout=5)
        r.ping()
        return True, f"✅ Redis connection successful ({redis_url})"
    except ImportError:
        return False, "❌ Redis package not installed"
    except Exception as e:
        return False, f"❌ Redis connection failed: {e}"


def check_project_structure() -> List[Tuple[str, bool, str]]:
    """Check if project directories and files exist"""
    required_paths = [
        ('src/', 'Main source directory'),
        ('src/telegram/', 'Telegram client directory'),
        ('src/telegram/telegram_client.py', 'Telegram client implementation'),
        ('src/database/', 'Database models directory'),
        ('src/utils/', 'Utilities directory'),
        ('config/', 'Configuration directory'),
        ('config/settings.py', 'Settings configuration'),
        ('requirements.txt', 'Python dependencies'),
    ]
    
    results = []
    for path, description in required_paths:
        path_obj = Path(path)
        if path_obj.exists():
            results.append((path, True, f"✅ {description}"))
        else:
            results.append((path, False, f"❌ {description} - Missing"))
    
    return results


def check_git_repository() -> Tuple[bool, str]:
    """Check if Git repository is initialized"""
    try:
        result = subprocess.run(['git', 'status'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, "✅ Git repository initialized"
        else:
            return False, "❌ Git repository not initialized"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "❌ Git not available or repository not initialized"


def main():
    """Main verification function"""
    print("🚀 GeopolMonitor Setup Verification")
    print("=" * 60)
    
    # Python version check
    python_ok, python_msg = check_python_version()
    print(f"\n📋 Python Version:")
    print(f"   {python_msg}")
    
    # Virtual environment check
    venv_ok, venv_msg = check_virtual_environment()
    print(f"\n📋 Virtual Environment:")
    print(f"   {venv_msg}")
    
    # Git repository check
    git_ok, git_msg = check_git_repository()
    print(f"\n📋 Git Repository:")
    print(f"   {git_msg}")
    
    # Project structure check
    print(f"\n📋 Project Structure:")
    structure_results = check_project_structure()
    structure_ok = all(result[1] for result in structure_results)
    for path, status, msg in structure_results:
        print(f"   {msg}")
    
    # Package installation check
    print(f"\n📋 Required Packages:")
    package_results = check_required_packages()
    packages_ok = all(result[1] for result in package_results)
    for package, status, msg in package_results:
        print(f"   {msg}")
    
    # Environment variables check
    print(f"\n📋 Environment Variables:")
    env_results = check_environment_variables()
    env_ok = all(result[1] for result in env_results)
    for var, status, msg in env_results:
        print(f"   {msg}")
    
    # Redis connection check
    redis_ok, redis_msg = check_redis_connection()
    print(f"\n📋 Redis Connection:")
    print(f"   {redis_msg}")
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_checks = [
        ("Python Version", python_ok),
        ("Virtual Environment", venv_ok),
        ("Git Repository", git_ok),
        ("Project Structure", structure_ok),
        ("Required Packages", packages_ok),
        ("Environment Variables", env_ok),
        ("Redis Connection", redis_ok),
    ]
    
    passed_checks = sum(1 for _, status in all_checks if status)
    total_checks = len(all_checks)
    
    for check_name, status in all_checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")
    
    print(f"\nResult: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("\n🎉 Perfect! Your GeopolMonitor setup is complete and ready for Telegram integration!")
        print("\n📋 Next Steps:")
        print("   1. Run the existing Telegram client tests: python src/tests/test_telegram_client.py")
        print("   2. Start working on Task 2: Database Models for Telegram Data")
    else:
        print("\n⚠️  Some setup issues detected. Please address the failed checks above.")
        print("\n🔧 Common Solutions:")
        
        if not packages_ok:
            print("   📦 Install missing packages: pip install -r requirements.txt")
        
        if not env_ok:
            print("   🔧 Create .env file with required variables (see config/settings.py)")
            print("   🔑 Get Telegram API credentials from: https://my.telegram.org/apps")
            print("   🔑 Get Google Gemini API key from: https://makersuite.google.com/app/apikey")
        
        if not redis_ok:
            print("   🔴 Install and start Redis:")
            print("     macOS: brew install redis && brew services start redis")
            print("     Ubuntu: sudo apt install redis-server && sudo systemctl start redis")
            print("     Docker: docker run -d -p 6379:6379 redis:alpine")
    
    print(f"\n💡 For detailed setup instructions, see the project documentation.")
    return passed_checks == total_checks


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 