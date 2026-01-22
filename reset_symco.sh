#!/bin/bash
# reset_symco.sh - Properly reset SymCo database
#
# USAGE:
#   ./reset_symco.sh        - Reset with confirmation
#   ./reset_symco.sh --force - Reset without confirmation

echo "═══════════════════════════════════════════════════════"
echo "        SymCo Database Reset Utility"
echo "═══════════════════════════════════════════════════════"

# Files to delete
DB_FILE="./symco.db"
WAL_FILE="./symco.db-wal"
SHM_FILE="./symco.db-shm"

# Check what exists
echo ""
echo "Current database files:"
[ -f "$DB_FILE" ] && echo "  ✓ $DB_FILE ($(du -h $DB_FILE | cut -f1))" || echo "  - $DB_FILE (not found)"
[ -f "$WAL_FILE" ] && echo "  ✓ $WAL_FILE ($(du -h $WAL_FILE | cut -f1))" || echo "  - $WAL_FILE (not found)"
[ -f "$SHM_FILE" ] && echo "  ✓ $SHM_FILE" || echo "  - $SHM_FILE (not found)"
echo ""

# Confirmation (unless --force)
if [ "$1" != "--force" ]; then
    echo "⚠️  WARNING: This will DELETE all game data!"
    echo ""
    read -p "Type 'DELETE' to confirm: " confirm
    
    if [ "$confirm" != "DELETE" ]; then
        echo "Reset cancelled."
        exit 0
    fi
fi

echo ""
echo "Deleting database files..."

# Stop any running uvicorn processes (optional)
# pkill -f "uvicorn app:app" 2>/dev/null && echo "  ✓ Stopped running server"

# Delete files
[ -f "$DB_FILE" ] && rm "$DB_FILE" && echo "  ✓ Deleted $DB_FILE"
[ -f "$WAL_FILE" ] && rm "$WAL_FILE" && echo "  ✓ Deleted $WAL_FILE"
[ -f "$SHM_FILE" ] && rm "$SHM_FILE" && echo "  ✓ Deleted $SHM_FILE"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "✓ Database reset complete!"
echo ""
echo "IMPORTANT: You MUST restart the server for changes to take effect:"
echo ""
echo "  1. Stop the server (Ctrl+C)"
echo "  2. Start fresh: uvicorn app:app --host 0.0.0.0 --port 8000"
echo ""
echo "DO NOT use --reload flag if you want a clean restart."
echo "═══════════════════════════════════════════════════════"
