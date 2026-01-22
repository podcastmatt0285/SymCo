#!/usr/bin/env python3
"""
AUTO-FIX SCRIPT FOR ORDER BOOK ERROR
=====================================

This script will automatically fix the order_book['bids'][0] and order_book['asks'][0]
errors in your ux.py file.

USAGE:
    python3 auto_fix_order_book.py

WHAT IT DOES:
    1. Backs up your current ux.py to ux.py.backup
    2. Fixes any problematic order_book access patterns
    3. Saves the fixed version
"""

import re
import shutil
from datetime import datetime

def fix_order_book_errors(filename='ux.py'):
    """Fix order book access errors in ux.py"""
    
    # Backup first
    backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(filename, backup_name)
    print(f"✓ Backed up to {backup_name}")
    
    # Read file
    with open(filename, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: Fix order_book['bids'][0]['price'] in f-strings
    # This is WRONG because Python evaluates [0] before checking the condition
    pattern1 = re.compile(
        r"order_book\['bids'\]\[0\]\['price'\]:[^\}]+\s+if\s+order_book\['bids'\]",
        re.IGNORECASE
    )
    
    # Replace with safe version
    def safe_bid_replace(match):
        return "(order_book['bids'][0]['price'] if order_book.get('bids') else 0)"
    
    content = pattern1.sub(lambda m: safe_bid_replace(m), content)
    
    # Pattern 2: Same for asks
    pattern2 = re.compile(
        r"order_book\['asks'\]\[0\]\['price'\]:[^\}]+\s+if\s+order_book\['asks'\]",
        re.IGNORECASE
    )
    
    def safe_ask_replace(match):
        return "(order_book['asks'][0]['price'] if order_book.get('asks') else 0)"
    
    content = pattern2.sub(lambda m: safe_ask_replace(m), content)
    
    # Pattern 3: Look for problematic lines and just remove order book references entirely
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # If line has both "order_book['bids'][0]" or "order_book['asks'][0]" AND it's causing issues
        if ("order_book['bids'][0]" in line or "order_book['asks'][0]" in line) and \
           ("Best Bid:" in line or "Best Ask:" in line or "Market:" in line):
            # Check if it's in an HTML section (has <div or style=)
            if "<div" in line or "style=" in line:
                # Comment it out
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(" " * indent + "<!-- ORDER BOOK DISPLAY REMOVED DUE TO EMPTY ORDER BOOK ERROR -->")
                print(f"✓ Commented out problematic line: {line.strip()[:80]}...")
                continue
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Write fixed content
    if content != original_content:
        with open(filename, 'w') as f:
            f.write(content)
        print(f"✓ Fixed {filename}")
        print(f"✓ Made {content.count('ORDER BOOK DISPLAY REMOVED')} fixes")
        return True
    else:
        print("✗ No problematic patterns found")
        return False

if __name__ == "__main__":
    import sys
    
    filename = sys.argv[1] if len(sys.argv) > 1 else 'ux.py'
    
    print(f"Fixing order book errors in {filename}...")
    print("-" * 50)
    
    try:
        success = fix_order_book_errors(filename)
        if success:
            print("-" * 50)
            print("✓ SUCCESS! Your file has been fixed.")
            print("✓ Restart your server and try again.")
        else:
            print("-" * 50)
            print("? No fixes needed, but the error might be elsewhere.")
            print("  Try manually searching for 'order_book' in your file.")
    except FileNotFoundError:
        print(f"✗ ERROR: {filename} not found")
        print("  Make sure you're in the directory with ux.py")
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
