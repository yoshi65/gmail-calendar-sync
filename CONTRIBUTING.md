# Contributing to Gmail Calendar Sync

Thank you for your interest in contributing to Gmail Calendar Sync! 🎉

## 🚀 Quick Start

1. **Fork** this repository
2. **Clone** your fork locally
3. **Set up** development environment
4. **Make** your changes
5. **Test** thoroughly
6. **Submit** a pull request

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

### Local Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/gmail-calendar-sync.git
cd gmail-calendar-sync

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API credentials

# Install pre-commit hooks (optional but recommended)
uv run pre-commit install
```

## 📋 Development Guidelines

### Code Style

- **Python**: Follow PEP 8
- **Type Hints**: Required for all functions
- **Formatting**: Use `ruff format`
- **Linting**: Use `ruff check`

```bash
# Format code
uv run ruff format src/ tests/

# Check linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### Testing

- **Write tests** for new features
- **Maintain coverage** above 40%
- **Test all email types** if adding new processors

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Specific tests
uv run pytest tests/test_models.py -v
```

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add hotel booking processor
fix: resolve calendar timezone issue
docs: update setup instructions
test: add carshare processor tests
```

## 🏗️ Architecture Overview

```
src/
├── models/           # Pydantic data models
├── processors/       # Email processing logic
├── services/         # External API clients
└── utils/           # Utilities and configuration
```

### Adding New Email Types

1. **Create model** in `src/models/new_type.py`
2. **Implement processor** in `src/processors/new_type_processor.py`
3. **Register processor** in `src/processors/factory.py`
4. **Add configuration** in `src/utils/config.py`
5. **Write tests** in `tests/test_models.py` and `tests/test_processors.py`

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment**: OS, Python version, uv version
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Log output** (with sensitive data removed)
- **Email sample** (anonymized)

## ✨ Feature Requests

For new features, please:

1. **Check existing issues** first
2. **Describe the use case** clearly
3. **Provide examples** if possible
4. **Consider backward compatibility**

## 🔧 Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated if needed
- [ ] No secrets or personal data in commits

### PR Checklist

- [ ] Descriptive title and description
- [ ] Link to related issue (if any)
- [ ] Screenshots/examples for UI changes
- [ ] Updated CHANGELOG.md (if significant)

### Review Process

1. **Automated checks** must pass (CI, tests, linting)
2. **Code review** by maintainers
3. **Testing** in review environment
4. **Merge** after approval

## 📚 Documentation

- **README.md**: User-facing documentation
- **CLAUDE.md**: Technical implementation details
- **Docstrings**: Required for all public functions
- **Type hints**: Required for all functions

## 🚨 Security

- **Never commit** API keys or secrets
- **Use `.env` files** for local development
- **Report security issues** privately via Security tab
- **Review** SECURITY.md for guidelines

## 📝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help newcomers get started
- Follow GitHub's Community Guidelines

## 🎯 Areas for Contribution

### High Priority
- New email type processors (hotels, restaurants)
- Improved error handling
- Performance optimizations
- Additional test coverage

### Medium Priority
- Documentation improvements
- UI/CLI enhancements
- Internationalization
- More email providers

### Good First Issues
- Fix typos in documentation
- Add test cases
- Improve error messages
- Refactor small functions

## 🤝 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **README.md**: For setup and usage help

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Gmail Calendar Sync! 🙏
