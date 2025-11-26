# Project Structure

Directory structure for `workflow-backups`.

## Directory Tree

```
workflow-backups/
├── .github/
│   └── workflows/
│       └── backup.yml              # GitHub Actions workflow
│
├── docs/
│   ├── architecture.md             # Architecture documentation
│   ├── PROJECT_STRUCTURE.md        # This file
│   └── releases/
│       └── README.md               # Release notes
│
├── src/
│   ├── __init__.py                 # Package initialization
│   ├── main.py                     # CLI entry point
│   └── backup/
│       ├── __init__.py             # Backup module exports
│       ├── backup_manager.py       # Backup orchestration
│       ├── repo_matcher.py         # Repository pattern matching
│       └── s3_handler.py           # S3 upload handling
│
├── tests/
│   ├── conftest.py                 # Pytest fixtures
│   └── test_repo_matcher.py        # Unit tests
│
├── .gitignore                      # Git ignore patterns
├── CHANGELOG.md                    # Version history
├── config.example.yml              # Example configuration
├── LICENSE                         # MIT License
├── pyproject.toml                  # Python project config
├── QUICKSTART.md                   # Quick start guide
├── README.md                       # Main documentation
├── requirements.txt                # Dependencies
└── setup-dev.sh                    # Dev setup script
```

## Key Files

### Source Code

| File | Purpose |
|------|---------|
| `src/main.py` | CLI parsing, task dispatch |
| `src/backup/backup_manager.py` | Orchestrates backup process |
| `src/backup/repo_matcher.py` | Regex-based repo filtering |
| `src/backup/s3_handler.py` | S3 uploads with verification |

### Configuration

| File | Purpose |
|------|---------|
| `config.example.yml` | Example configuration |
| `pyproject.toml` | Project metadata and tool config |
| `requirements.txt` | Production dependencies |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Main documentation |
| `QUICKSTART.md` | Getting started guide |
| `docs/architecture.md` | Technical architecture |