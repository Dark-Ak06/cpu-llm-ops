# Security Policy

## Supported Versions

Only the latest release running on the `main` branch receives active security updates and vulnerability patches.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of `cpu-llm-ops` seriously. If you discover a vulnerability, please do NOT create a public issue.

Instead, please report security issues through GitHub Private Vulnerability Reporting on the repository:
[Report a vulnerability](https://github.com/Dark-Ak06/cpu-llm-ops/security/advisories/new)

Alternatively, contact the maintainer directly at:
- **Email**: geragulgul@ezdrav.kz

Please include:
1. Description of the vulnerability.
2. Steps or proof-of-concept to reproduce the behavior.
3. Potential impact and attack vectors.

You can expect an initial response acknowledging receipt within 48 hours.

## Container & Infrastructure Security Practices

1. **Non-Root Execution**: Container images run under unprivileged UID `10001` (`appuser`).
2. **Minimal Attack Surface**: Production stages contain no C++ compilers, development headers, or build tools.
3. **Automated Scanning**: Every commit and pull request is scanned with Trivy (vulnerabilities and misconfigurations) and Hadolint.
4. **Read-Only Root Filesystem**: Kubernetes manifests enforce `readOnlyRootFilesystem: true` with strict Linux capabilities dropping (`drop: ["ALL"]`).
