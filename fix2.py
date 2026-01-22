#!/usr/bin/env python3
"""
NUCLEAR FIX - Remove All Order Book Display Code
=================================================
This script removes ALL order book display code from ux.py
to get your trading page working again.
"""

import shutil
from datetime import datetime

def remove_order_book_display():
    filename = 'ux.py'
    
    # Backup
    backup = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(filename, backup)
    print(f"✓ Backed up to {backup}")
    
    # Read file
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Remove any lines that reference order_book[...] in the brokerage_trading_page function
    in_trading_page = False
    fixed_lines = []
    removed_count = 0
    
    for i, line in enumerate(lines, 1):
        # Track if we're in the brokerage_trading_page function
        if 'def brokerage_trading_page' in line:
            in_trading_page = True
            fixed_lines.append(line)
            continue
        
        # Exit the function when we hit the next function definition
        if in_trading_page and line.startswith('def ') and 'brokerage_trading_page' not in line:
            in_trading_page = False
        
        # If we're in the trading page function and the line references order_book
        if in_trading_page and "order_book[" in line:
            # Skip this line
            print(f"✓ Removed line {i}: {line.strip()[:70]}...")
            removed_count += 1
            continue
        
        fixed_lines.append(line)
    
    if removed_count > 0:
        # Write fixed file
        with open(filename, 'w') as f:
            f.writelines(fixed_lines)
        
        print(f"\n✓ Removed {removed_count} order book display line(s)")
        print("✓ Your trading page will now work without order book display")
        print("✓ Restart your server with: python3 app.py")
        return True
    else:
        print("\n? No order book references found in brokerage_trading_page")
        print("  The error might be somewhere else")
        return False

if __name__ == '__main__':
    print("Removing all order book display code from ux.py...")
    print("-" * 60)
    
    try:
        remove_order_book_display()
    except FileNotFoundError:
        print("ERROR: ux.py not found")
        print("Make sure you're in the SymCo directory")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
