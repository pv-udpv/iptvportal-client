# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

### GitHub Security Advisories (Preferred)

1. Go to the [Security tab](https://github.com/pv-udpv/iptvportal-client/security/advisories)
2. Click "Report a vulnerability"
3. Fill in the details of the vulnerability

### Email

Alternatively, you can email security concerns to: pv@example.com

Please include:

- Type of vulnerability
- Full path of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Communication**: We will keep you informed of the progress toward fixing the vulnerability
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)
- **Timeline**: We aim to release a fix within 90 days of the initial report

## Security Best Practices

When using IPTVPortal Client:

### Credentials Management

- **Never commit credentials** to version control
- Use environment variables or `.env` files (ensure `.env` is in `.gitignore`)
- Set appropriate file permissions on configuration files:
  ```bash
  chmod 600 ~/.iptvportal/cli-config.yaml
  chmod 600 .env
  ```

### Configuration Files

- Store sensitive configuration files outside of web-accessible directories
- Use the configuration system's encryption features when available
- Regularly rotate API credentials and session tokens

### Network Security

- Use HTTPS/TLS for all API communications
- Validate SSL certificates (avoid disabling certificate verification)
- Consider using a VPN when accessing sensitive endpoints

### Session Management

- Session tokens are cached in `~/.iptvportal/session-cache/`
- These files contain sensitive authentication data
- Ensure proper file permissions:
  ```bash
  chmod 700 ~/.iptvportal/session-cache
  chmod 600 ~/.iptvportal/session-cache/*
  ```

### Dependencies

- Keep dependencies up to date
- Regularly run security audits:
  ```bash
  pip-audit
  # or
  safety check
  ```

### Production Deployment

- Do not run with debug mode in production
- Implement rate limiting for API calls
- Use read-only database connections where possible
- Implement proper logging and monitoring
- Follow the principle of least privilege

## Known Security Considerations

### Authentication

- Session tokens are stored in the local cache directory
- Tokens expire based on server configuration
- Use `iptvportal auth --renew` to refresh expired sessions

### SQL Injection

- The transpiler uses parameterized queries and sqlglot for SQL parsing
- Direct SQL execution is not performed on the backend
- All SQL is transpiled to JSONSQL before transmission

### Data Privacy

- Cached data may contain sensitive information
- Clear cache regularly if working with sensitive data:
  ```bash
  rm -rf ~/.iptvportal/cache/*
  rm -rf ~/.iptvportal/session-cache/*
  ```

## Security Updates

Security updates will be released as patch versions and announced via:

- GitHub Security Advisories
- Release notes
- README changelog section

## Scope

The following are **in scope** for security reports:

- Authentication bypass
- SQL injection via transpiler
- Credential exposure in logs or cache
- Session hijacking
- Dependency vulnerabilities
- Code execution vulnerabilities
- Information disclosure

The following are **out of scope**:

- Vulnerabilities in third-party dependencies (report to the respective maintainers)
- Issues in the IPTVPortal server itself (this is a client library)
- Social engineering attacks
- DoS attacks requiring excessive resources

## Attribution

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. We will acknowledge contributors in our security advisories unless they prefer to remain anonymous.
