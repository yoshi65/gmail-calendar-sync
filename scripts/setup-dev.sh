#!/bin/bash
# Development environment setup script for Gmail Calendar Sync

set -e  # Exit on any error

echo "🚀 Setting up Gmail Calendar Sync development environment..."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

echo "📦 Installing dependencies..."
uv sync --all-extras

echo "🪝 Setting up pre-commit hooks..."
uv run pre-commit install

echo "🧪 Running initial tests to verify setup..."
uv run pytest tests/ -v --tb=short -x

echo "🔍 Running type check..."
uv run mypy src/

echo "✨ Formatting code..."
uv run ruff format src/ tests/

echo "🔧 Running linter..."
uv run ruff check src/ tests/

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Copy .env.example to .env and configure your API keys"
echo "   2. Run 'make help' to see available commands"
echo "   3. Use 'make dev' to run in development mode"
echo "   4. Use 'make test-watch' for continuous testing"
echo ""
echo "🛠️  Available make commands:"
make help
