#!/usr/bin/env python3
"""Configuration validation script for Gmail Calendar Sync."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from utils.config import Settings, get_settings
except ImportError as e:
    print(f"❌ Failed to import project modules: {e}")
    print("   Make sure you're running this from the project root.")
    sys.exit(1)


def validate_environment_file(env_path: Path) -> dict[str, str]:
    """Validate and load environment file."""
    if not env_path.exists():
        print(f"❌ Environment file not found: {env_path}")
        return {}

    env_vars = {}
    with open(env_path) as f:
        for _line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip("\"'")

    print(f"✅ Found {len(env_vars)} environment variables in {env_path}")
    return env_vars


def check_required_variables(env_vars: dict[str, str]) -> list[str]:
    """Check for required environment variables."""
    required_vars = [
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
        "GMAIL_REFRESH_TOKEN",
        "CALENDAR_CLIENT_ID",
        "CALENDAR_CLIENT_SECRET",
        "CALENDAR_REFRESH_TOKEN",
        "OPENAI_API_KEY",
    ]

    missing_vars = []
    for var in required_vars:
        if var not in env_vars or not env_vars[var]:
            missing_vars.append(var)
        else:
            # Mask sensitive values for display
            masked_value = (
                env_vars[var][:10] + "..." if len(env_vars[var]) > 10 else "***"
            )
            print(f"  ✅ {var}: {masked_value}")

    return missing_vars


def check_optional_variables(env_vars: dict[str, str]) -> None:
    """Check and display optional variables."""
    optional_vars = [
        "SLACK_WEBHOOK_URL",
        "SYNC_PERIOD_HOURS",
        "SYNC_PERIOD_DAYS",
        "SYNC_START_DATE",
        "SYNC_END_DATE",
        "LOG_LEVEL",
        "GMAIL_LABEL",
    ]

    print("\n📋 Optional Configuration:")
    for var in optional_vars:
        if var in env_vars and env_vars[var]:
            value = env_vars[var]
            if "webhook" in var.lower() or "url" in var.lower():
                value = value[:20] + "..." if len(value) > 20 else value
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚪ {var}: Not set (using default)")


def validate_settings() -> Settings | None:
    """Validate settings loading."""
    try:
        settings = get_settings()
        print("\n✅ Settings loaded successfully!")

        print(
            f"  📧 Gmail domains: {len(settings.flight_domains + settings.carshare_domains)} configured"
        )
        print(f"  🛡️  Log level: {settings.log_level}")
        print(
            f"  ⏰ Sync period: {settings.sync_period_hours or 'N/A'}h / {settings.sync_period_days}d"
        )

        return settings
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return None


def check_dependencies() -> None:
    """Check if all required dependencies are installed."""
    print("\n🔍 Checking dependencies...")

    required_packages = [
        "pydantic",
        "pydantic_settings",
        "structlog",
        "httpx",
        "openai",
        "google-auth",
        "google-api-python-client",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")

    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("   Run 'make install' to install dependencies")
    else:
        print("\n✅ All required packages are installed!")


def main():
    """Main validation function."""
    print("🔧 Gmail Calendar Sync Configuration Validator")
    print("=" * 50)

    # Check project structure
    project_files = [
        "pyproject.toml",
        "src/main.py",
        "src/utils/config.py",
    ]

    print("\n📁 Project Structure:")
    for file_path in project_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            print("     Make sure you're running this from the project root.")
            sys.exit(1)

    # Check dependencies
    check_dependencies()

    # Check environment files
    print("\n📄 Environment Files:")
    env_files = [".env", ".env.example"]
    for env_file in env_files:
        env_path = Path(env_file)
        if env_path.exists():
            print(f"  ✅ {env_file} found")
            if env_file == ".env":
                # Validate main env file
                env_vars = validate_environment_file(env_path)

                print("\n🔑 Required Configuration:")
                missing_vars = check_required_variables(env_vars)

                if missing_vars:
                    print(f"\n❌ Missing required variables: {', '.join(missing_vars)}")
                    print("   Please set these in your .env file")
                else:
                    print("\n✅ All required variables are set!")

                check_optional_variables(env_vars)
        else:
            print(f"  ⚪ {env_file} not found")

    # Validate settings loading
    settings = validate_settings()

    # Summary
    print("\n" + "=" * 50)
    env_check_result = []
    if Path(".env").exists():
        env_check_result = check_required_variables(
            validate_environment_file(Path(".env"))
        )

    if settings and not env_check_result:
        print("✅ Configuration validation passed!")
        print("\n🚀 Ready for development:")
        print("   make dev      # Run in development mode")
        print("   make test     # Run tests")
        print("   make help     # See all commands")
    else:
        print("❌ Configuration validation failed!")
        print("\n📝 Next steps:")
        print("   1. Copy .env.example to .env")
        print("   2. Configure your API keys in .env")
        print("   3. Run this script again to validate")
        sys.exit(1)


if __name__ == "__main__":
    main()
