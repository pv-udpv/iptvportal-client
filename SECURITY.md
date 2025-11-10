# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in IPTVPortal Client, please report it responsibly:

### How to Report

1. **Do NOT** open a public issue
2. Email security concerns to: [Maintainer Email]
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Initial Assessment**: Within 5 business days, we will provide an initial assessment
- **Updates**: We will keep you informed of progress on fixing the issue
- **Disclosure**: We will coordinate disclosure timing with you

### Security Best Practices

When using IPTVPortal Client, follow these security best practices:

#### Credentials Management

- **Never** commit credentials to version control
- Use environment variables or secure secret management
- Store session cache files with restricted permissions (600/700)
- Rotate credentials regularly

```bash
# Set proper permissions for config files
chmod 600 ~/.iptvportal/cli-config.yaml
chmod 700 ~/.iptvportal/session-cache
```

#### Configuration

```bash
# Use environment variables for sensitive data
export IPTVPORTAL_USERNAME=your_username
export IPTVPORTAL_PASSWORD=your_password

# Or use .env file (add to .gitignore!)
echo ".env" >> .gitignore
```

#### API Usage

- Always use HTTPS endpoints
- Validate API responses before processing
- Set appropriate timeouts
- Implement rate limiting in production

```python
from iptvportal import IPTVPortalClient
from iptvportal.config import IPTVPortalSettings

settings = IPTVPortalSettings(
    api_url="https://api.example.com",  # Always HTTPS
    timeout=30,
    max_retries=3
)

client = IPTVPortalClient(settings=settings)
```

#### Database Security

- Restrict access to SQLite cache databases
- Use proper file permissions
- Encrypt sensitive data at rest if needed
- Regular backups of important data

```bash
# Secure cache directory
chmod 700 ~/.iptvportal/cache
chmod 600 ~/.iptvportal/cache/*.db
```

### Known Security Considerations

#### Password Storage

- Passwords are handled using Pydantic's `SecretStr` type
- Session tokens are cached in local files
- Clear session cache on untrusted systems: `iptvportal cache clear`

#### Input Validation

- All user inputs are validated before processing
- SQL queries are transpiled, not executed directly
- JSONSQL queries are validated against schema

#### Network Security

- All API communications should use HTTPS
- Certificate verification is enabled by default
- Configure appropriate timeouts to prevent hanging connections

### Security Updates

We will:
- Release security patches as soon as possible
- Announce security updates in release notes
- Update this document with remediation steps
- Credit security researchers (with permission)

### Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 2**: Acknowledgment sent
3. **Day 7**: Initial assessment and plan
4. **Day 30**: Fix developed and tested (target)
5. **Day 35**: Security advisory published (target)
6. **Day 90**: Full disclosure (if not fixed sooner)

### Bug Bounty

We currently do not have a bug bounty program, but we deeply appreciate responsible disclosure and will credit security researchers in our security advisories.

## Security Checklist for Contributors

When contributing code, ensure:

- [ ] No hardcoded credentials or secrets
- [ ] Input validation for all user inputs
- [ ] Proper error handling without information leakage
- [ ] No SQL injection vulnerabilities (use parameterized queries)
- [ ] No arbitrary code execution (avoid eval/exec)
- [ ] Secure defaults in configuration
- [ ] Proper permission checks where applicable
- [ ] Dependencies are up to date and without known vulnerabilities

## Dependencies

We regularly review and update dependencies to address known vulnerabilities. You can check for vulnerabilities using:

```bash
# Check for known vulnerabilities
pip-audit

# Or with safety
safety check
```

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Secure Coding Guidelines](https://wiki.sei.cmu.edu/confluence/display/seccode/SEI+CERT+Coding+Standards)

## Questions?

If you have questions about security that don't involve reporting a vulnerability, please:
1. Check our documentation
2. Open a GitHub Discussion
3. Contact the maintainers

Thank you for helping keep IPTVPortal Client secure! 🔒
