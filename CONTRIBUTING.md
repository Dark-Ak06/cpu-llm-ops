# Contributing to cpu-llm-ops

Thank you for your interest in contributing to `cpu-llm-ops`! This repository demonstrates production DevOps and MLOps best practices for resource-efficient LLM inference.

## Development Workflow

1. Fork the repository and create a descriptive feature branch from `main`.
2. Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for all commit messages:
   - `feat:` new feature or endpoint
   - `fix:` bug fix
   - `ci:` CI/CD pipeline changes
   - `docs:` documentation improvements
   - `test:` test coverage additions or fixes
   - `chore:` maintenance tasks or dependency updates
3. Ensure all local tests and linters pass:
   ```bash
   make lint
   make test
   ```
4. Submit a Pull Request targeting `main`.

## Code Style & Standards

- **Python**: Formatted and linted with `ruff` (`ruff format` and `ruff check`), strictly type-annotated with `mypy`.
- **Docker**: Adheres to Dockerfile best practices validated by `hadolint`.
- **Kubernetes**: Helm charts validated by `helm lint` and `kubeconform`.
- **Terraform**: Formatted with `terraform fmt -check` and validated with `tflint`.
- **Security**: No secrets or credentials committed; all weights externalized.

## Pull Request Guidelines

- Provide a concise explanation of what the change accomplishes.
- Reference any relevant GitHub issues.
- Confirm all CI checks pass.
