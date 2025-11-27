# Copilot Instructions for workflow-backups

## Project Overview

This is a centralized workflow for backing up QuantEcon repositories to AWS S3. It runs from this single repository and backs up all matching repositories across the organization.

## Development Guidelines

### Testing with Nox

Use `nox` for all testing and development tasks:

```bash
nox -s tests        # Run full test suite
nox -s tests_quick  # Run tests without coverage
nox -s lint         # Run linting (ruff)
nox -s format       # Format code (black, isort)
nox -s typecheck    # Type checking (mypy)
nox -s coverage     # Run tests with coverage report
```

### Documentation Standards

1. **Do NOT create SUMMARY files for changes**
   - Update existing documentation (README.md, CHANGELOG.md, docs/)
   - Maintain a single source of truth

2. **Release notes go in `docs/releases/`**
   - Use version-specific files: `v0.1.0.md`, `v1.0.0.md`
   - Follow semantic versioning

3. **Use `/tmp/` for `gh` CLI outputs**
   - Example: `gh repo list quantecon --json name > /tmp/gh-repos.json`

## Code Standards

### Python
- Follow PEP 8, max line length 100
- Use type hints for function signatures
- Google-style docstrings for public functions
- Explicit imports (no wildcards)

### Testing
- Write tests for new features (>80% coverage)
- Use pytest, mock external services
- Tests go in `tests/` directory
- Run tests with `nox -s tests`

### Error Handling
- Use specific exception types
- Log errors with context
- Fail gracefully with cleanup

## Project-Specific Guidelines

### AWS S3
- Use boto3 for S3 operations
- Verify uploads with checksums
- Support OIDC authentication (recommended)

### GitHub API
- Use PyGithub library
- Respect rate limits
- Handle pagination

### Configuration
- YAML format
- Validate on load
- Document all options

## File Organization

```
workflow-backups/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   └── backup/
│       ├── backup_manager.py
│       ├── repo_matcher.py
│       └── s3_handler.py
├── tests/
├── docs/
│   ├── releases/
│   ├── architecture.md
│   └── example_report.md
├── .github/
│   ├── workflows/backup.yml
│   └── copilot-instructions.md
├── config.example.yml
├── noxfile.py               # Test/dev automation
├── requirements.txt
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## CLI Usage

```bash
python -m src.main --config config.yml --task backup           # Run backup
python -m src.main --config config.yml --task backup --dry-run # Preview only
python -m src.main --config config.yml --task backup --force   # Force re-backup
python -m src.main --config config.yml --task report           # Generate report
python -m src.main --config config.yml --task backup --verbose # Debug logging
```

## Git Workflow

- Feature branches from `main`
- Update CHANGELOG.md with each PR
- Tag releases with version numbers

## Security

- Never commit credentials
- Use GitHub Secrets for sensitive data
- Prefer OIDC over static AWS credentials
