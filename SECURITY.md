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
- Store the deploy credential in GitHub Secrets; runtime secrets are injected from GCP Secret Manager
- Rotate credentials regularly

#### Data Handling
- Email content is processed transiently and not persisted
- Personal data (passenger/user names, raw model output) is kept out of application logs
- OpenAI API calls include only the email content needed for extraction, and email text is treated as untrusted input

#### Dependencies
- Renovate monitors dependencies for known vulnerabilities
- Dependency update PRs run the full CI suite before merging
- Regular dependency audits via GitHub security alerts

## Security Features

- **OAuth2 Authentication**: Secure Google API access
- **Minimal Permissions**: `gmail.modify` and `calendar.events` scopes only
- **Secret Management**: Production credentials stored in GCP Secret Manager and injected at runtime
- **Untrusted-Input Handling**: Email text is treated as untrusted; OpenAI responses are constrained to JSON and check-in URLs are validated
- **Audit Logging**: Structured JSON logging that excludes personal data
- **Dependency Scanning**: Automated vulnerability detection via Renovate + OSV

## Best Practices for Users

1. **Local Development**:
   - Use `.env` files for local credentials (never commit them)
   - Run `LOG_LEVEL=DEBUG` only in secure environments
   - Regularly update dependencies via `uv sync`

2. **Production Deployment**:
   - Runtime secrets are managed in GCP Secret Manager and injected into the Cloud Run Job
   - Enable branch protection rules
   - Monitor execution logs for anomalies

3. **API Key Management**:
   - Set up Google Cloud Console with minimal required scopes
   - Regularly rotate OAuth2 refresh tokens
   - Monitor OpenAI API usage for unexpected spikes

Thank you for helping keep Gmail Calendar Sync secure!
