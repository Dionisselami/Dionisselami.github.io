#!/usr/bin/env python3
"""
Setup script for Twitter Bot
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """Run a command and handle errors."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        return None

def check_python_version():
    """Check Python version."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    
    # Check if pip is available
    pip_version = run_command("pip --version", check=False)
    if not pip_version:
        print("Error: pip is not installed")
        sys.exit(1)
    
    # Install dependencies
    requirements_file = Path("twitter_bot/requirements.txt")
    if requirements_file.exists():
        cmd = f"pip install -r {requirements_file}"
        result = run_command(cmd, check=False)
        if result is not None:
            print("✓ Dependencies installed successfully")
        else:
            print("Error: Failed to install dependencies")
            sys.exit(1)
    else:
        print("Error: requirements.txt not found")
        sys.exit(1)

def setup_config():
    """Setup configuration file."""
    config_path = Path("twitter_bot/config.py")
    example_config_path = Path("twitter_bot/example_config.py")
    
    if config_path.exists():
        print("✓ Configuration file already exists")
        return
    
    if example_config_path.exists():
        shutil.copy(example_config_path, config_path)
        print("✓ Configuration file created from example")
        print("  Please edit twitter_bot/config.py with your settings")
    else:
        print("Error: example_config.py not found")

def check_webdriver():
    """Check if webdriver is available."""
    print("Checking WebDriver...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        # Try to create a Chrome driver
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.quit()
            print("✓ Chrome WebDriver is available")
        except Exception as e:
            print(f"Warning: Chrome WebDriver not available: {e}")
            print("  You may need to install ChromeDriver")
            print("  Download from: https://chromedriver.chromium.org/")
    
    except ImportError:
        print("Error: Selenium not installed")

def create_directories():
    """Create necessary directories."""
    directories = [
        "logs",
        "backups",
        "temp",
    ]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created directory: {dir_name}")

def main():
    """Main setup function."""
    print("Twitter Bot Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_dependencies()
    
    # Setup configuration
    setup_config()
    
    # Check WebDriver
    check_webdriver()
    
    # Create directories
    create_directories()
    
    print("\nSetup completed!")
    print("\nNext steps:")
    print("1. Edit twitter_bot/config.py with your Twitter credentials")
    print("2. Review and adjust the configuration settings")
    print("3. Run the bot with: python twitter_bot/twitter_bot.py")
    print("\nImportant:")
    print("- Start with conservative rate limits")
    print("- Test with a secondary account first")
    print("- Monitor the bot's activity regularly")
    print("- Respect Twitter's terms of service")

if __name__ == "__main__":
    main()