#!/usr/bin/env python3
"""
Run the Twitter Bot
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    try:
        from twitter_bot.twitter_bot import main
        main()
    except ImportError as e:
        print(f"Error importing Twitter bot: {e}")
        print("Make sure you have installed all dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error running Twitter bot: {e}")
        sys.exit(1)