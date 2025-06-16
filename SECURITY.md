# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Gmail Calendar Sync, please report it responsibly:

### How to Report

1. **Do NOT create a public issue** for security vulnerabilities
2. Send a detailed report to: [Security Issues](https://github.com/yoshi65/gmail-calendar-sync/security/advisories/new)
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Timeline**: Critical issues within 2 weeks, others within 4 weeks
- **Disclosure**: Coordinated disclosure after fix is released

### Security Considerations

#### API Keys & Credentials
- Never commit API keys to the repository
- Use GitHub Secrets for production deployments
- Rotate credentials regularly

#### Data Handling
- Email content is processed locally and not stored
- Personal information is automatically masked in logs
- OpenAI API calls include only necessary email data

#### Dependencies
- Renovate automatically monitors for security vulnerabilities
- Critical security updates are auto-merged after CI passes
- Regular dependency audits via GitHub security alerts

## Security Features

- **OAuth2 Authentication**: Secure Google API access
- **Minimal Permissions**: Only necessary Gmail/Calendar scopes
- **Environment Isolation**: Production secrets managed via GitHub Environments
- **Audit Logging**: Structured logging with automatic PII masking
- **Dependency Scanning**: Automated vulnerability detection via Renovate + OSV

## Best Practices for Users

1. **Local Development**:
   - Use `.env` files for local credentials (never commit them)
   - Run `LOG_LEVEL=DEBUG` only in secure environments
   - Regularly update dependencies via `uv sync`

2. **Production Deployment**:
   - Use GitHub Environments for secret management
   - Enable branch protection rules
   - Monitor execution logs for anomalies

3. **API Key Management**:
   - Set up Google Cloud Console with minimal required scopes
   - Regularly rotate OAuth2 refresh tokens
   - Monitor OpenAI API usage for unexpected spikes

Thank you for helping keep Gmail Calendar Sync secure!