"""Nox configuration for workflow-backups testing and automation."""

import nox

# Default sessions to run
nox.options.sessions = ["tests"]

# Python versions to test against
PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    session.install("-e", ".")  # Install package in editable mode
    session.install("pytest", "pytest-cov", "pytest-mock")
    session.run(
        "pytest",
        "tests/",
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        *session.posargs,
    )


@nox.session(python="3.11")
def tests_quick(session: nox.Session) -> None:
    """Run tests quickly on a single Python version."""
    session.install("-e", ".")  # Install package in editable mode
    session.install("pytest", "pytest-mock")
    session.run("pytest", "tests/", "-v", *session.posargs)


@nox.session(python="3.11")
def lint(session: nox.Session) -> None:
    """Run linting checks."""
    session.install("ruff", "black")
    session.run("black", "--check", "src/", "tests/")
    session.run("ruff", "check", "src/", "tests/")


@nox.session(python="3.11")
def format(session: nox.Session) -> None:
    """Format code with black and ruff."""
    session.install("ruff", "black")
    session.run("black", "src/", "tests/")
    session.run("ruff", "check", "--fix", "src/", "tests/")


@nox.session(python="3.11")
def typecheck(session: nox.Session) -> None:
    """Run type checking with mypy."""
    session.install("-e", ".")
    session.install("mypy", "types-PyYAML", "types-python-dateutil")
    session.run("mypy", "src/", "--ignore-missing-imports")


@nox.session(python="3.11")
def coverage(session: nox.Session) -> None:
    """Generate coverage report."""
    session.install("-e", ".")
    session.install("pytest", "pytest-cov", "pytest-mock")
    session.run(
        "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
    )
    session.log("Coverage report generated in htmlcov/")


@nox.session(python="3.11")
def dev(session: nox.Session) -> None:
    """Set up development environment."""
    session.install("-e", ".")
    session.install(
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "black",
        "ruff",
        "mypy",
        "types-PyYAML",
        "types-python-dateutil",
        "nox",
    )
    session.log("Development environment ready!")
    session.log("Run 'nox -s tests_quick' to run tests")
    session.log("Run 'nox -s lint' to check code style")
    session.log("Run 'nox -s format' to format code")
