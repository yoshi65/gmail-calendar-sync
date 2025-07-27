#!/bin/bash
# Clean development environment script for Gmail Calendar Sync

set -e  # Exit on any error

echo "🧹 Cleaning Gmail Calendar Sync development environment..."
echo ""

# Clean generated files
echo "🗑️  Removing generated files..."
make clean

# Optional: Clean test environment (with confirmation)
if [ "$1" = "--test-cleanup" ]; then
    echo ""
    echo "⚠️  WARNING: This will also remove processed Gmail labels and calendar events!"
    echo "   This action is intended for development/testing only."
    echo "   Press Ctrl+C to cancel, or Enter to continue..."
    read -r

    echo "🧪 Cleaning test environment..."
    if [ -f "cleanup_for_test.py" ]; then
        uv run python cleanup_for_test.py
    else
        echo "   cleanup_for_test.py not found, skipping..."
    fi
fi

# Clean uv cache
echo "🗑️  Cleaning uv cache..."
uv cache clean

# Optional: Remove virtual environment
if [ "$1" = "--full" ]; then
    echo ""
    echo "⚠️  WARNING: This will remove the virtual environment!"
    echo "   You'll need to run 'make setup' again after this."
    echo "   Press Ctrl+C to cancel, or Enter to continue..."
    read -r

    echo "🗑️  Removing virtual environment..."
    rm -rf .venv/
fi

echo ""
echo "✅ Development environment cleaned!"
echo ""
echo "📝 Usage:"
echo "   ./scripts/clean-dev.sh                    # Clean generated files only"
echo "   ./scripts/clean-dev.sh --test-cleanup     # Also clean test data"
echo "   ./scripts/clean-dev.sh --full             # Full cleanup including venv"
echo ""
echo "🚀 To restore environment: make setup"
