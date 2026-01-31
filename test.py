#!/usr/bin/env python3
"""
Districts Diagnostic Script
Run this to check if districts_ux.py can be imported and routes are defined
"""

print("=" * 50)
print("DISTRICTS DIAGNOSTICS")
print("=" * 50)

# Test 1: Can we import districts_ux?
print("\n[Test 1] Importing districts_ux...")
try:
    import districts_ux
    print("✓ districts_ux imported successfully")
except Exception as e:
    print(f"✗ Failed to import districts_ux: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2: Does it have a router?
print("\n[Test 2] Checking for router...")
if hasattr(districts_ux, 'router'):
    print("✓ Router found")
    router = districts_ux.router
else:
    print("✗ No router attribute found")
    exit(1)

# Test 3: What routes are defined?
print("\n[Test 3] Checking routes...")
if hasattr(router, 'routes'):
    print(f"✓ Found {len(router.routes)} routes:")
    for route in router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f"  - {list(route.methods)[0] if route.methods else 'GET'} {route.path}")
else:
    print("✗ Router has no routes")

# Test 4: Can we import auth?
print("\n[Test 4] Checking auth dependency...")
try:
    from auth import get_db, get_player_from_session
    print("✓ Auth module imported successfully")
except Exception as e:
    print(f"✗ Failed to import auth: {e}")

# Test 5: Can we import districts?
print("\n[Test 5] Checking districts module dependency...")
try:
    from districts import get_player_districts, DISTRICT_TYPES
    print("✓ Districts module imported successfully")
except Exception as e:
    print(f"✗ Failed to import districts: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Can we import ux (for shell)?
print("\n[Test 6] Checking ux dependency...")
try:
    from ux import shell
    print("✓ UX shell imported successfully")
except Exception as e:
    print(f"⚠ Failed to import ux.shell (will use fallback): {e}")

print("\n" + "=" * 50)
print("DIAGNOSTICS COMPLETE")
print("=" * 50)
