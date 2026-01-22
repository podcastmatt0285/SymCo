#!/usr/bin/env python3
"""
PROPER FIX - Restore backup and fix correctly
==============================================
"""

import shutil
from datetime import datetime

def fix_ux_properly():
    """Restore from backup and apply proper fix"""
    
    # First, restore from the backup
    print("Step 1: Restoring from backup...")
    try:
        shutil.copy('ux.py.orderbook_backup', 'ux.py')
        print("✓ Restored ux.py from ux.py.orderbook_backup")
    except FileNotFoundError:
        print("✗ Backup not found. Cannot restore.")
        return False
    
    # Now read the file
    with open('ux.py', 'r') as f:
        content = f.read()
    
    print("\nStep 2: Applying proper fixes...")
    
    # Find the market_page function and remove order book code from it
    lines = content.split('\n')
    fixed_lines = []
    skip_until_else = False
    in_order_book_block = False
    indent_to_match = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is an order book reference in market display
        if "order_book['bids']:" in line or "order_book['asks']:" in line:
            # This is the start of an order book display block
            in_order_book_block = True
            indent_to_match = len(line) - len(line.lstrip())
            print(f"✓ Found order book block at line {i+1}")
            
            # Skip this line and all indented lines after it
            i += 1
            while i < len(lines):
                next_line = lines[i]
                next_indent = len(next_line) - len(next_line.lstrip()) if next_line.strip() else indent_to_match + 1
                
                # If we hit an else block or another statement at the same or lower indent, stop
                if next_line.strip() and next_indent <= indent_to_match:
                    # Check if it's an else clause
                    if next_line.strip().startswith('else:'):
                        # Skip the else block too
                        i += 1
                        continue
                    else:
                        # We've reached the end of the block
                        break
                
                i += 1
            
            in_order_book_block = False
            continue
        
        fixed_lines.append(line)
        i += 1
    
    # Write fixed content
    content = '\n'.join(fixed_lines)
    
    # Make another backup before writing
    backup = f"ux.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy('ux.py', backup)
    
    with open('ux.py', 'w') as f:
        f.write(content)
    
    print(f"✓ Fixed ux.py (backup: {backup})")
    print("\n✓ Done! Try starting your server now:")
    print("  python3 app.py")
    
    return True

if __name__ == '__main__':
    print("Fixing ux.py properly...")
    print("=" * 60)
    
    try:
        success = fix_ux_properly()
        if not success:
            print("\nTo manually fix:")
            print("1. Restore: cp ux.py.orderbook_backup ux.py")
            print("2. Manually remove order_book display sections")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
