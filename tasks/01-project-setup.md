# Task 01: Project Setup

## Summary
Set up the Python project structure with pyproject.toml and package skeleton.

## Dependencies
None - this is the foundational task.

## Requirements

### 1. Create pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "bodega"
version = "0.1.0"
description = "A git-native issue/task tracking CLI"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "python-frontmatter>=1.0",
    "pyyaml>=6.0",
]

[project.scripts]
bodega = "bodega.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]
```

### 2. Create Package Structure

```
src/
└── bodega/
    ├── __init__.py
    ├── cli.py
    ├── commands/
    │   └── __init__.py
    ├── models/
    │   └── __init__.py
    ├── storage.py
    ├── config.py
    ├── graph.py
    ├── output.py
    └── utils.py
tests/
    ├── __init__.py
    └── conftest.py
```

### 3. Package Init (`src/bodega/__init__.py`)

```python
__version__ = "0.1.0"
```

### 4. CLI Entry Point Stub (`src/bodega/cli.py`)

```python
import click

@click.group()
@click.version_option()
def main():
    """Bodega - Git-native issue tracking for developers and AI agents."""
    pass

if __name__ == "__main__":
    main()
```

### 5. Test Configuration (`tests/conftest.py`)

Set up pytest fixtures:
- `tmp_bodega_dir`: Temporary `.bodega/` directory for tests
- `sample_ticket`: A sample ticket dict for testing

## Acceptance Criteria

- [ ] `pip install -e .` succeeds
- [ ] `bodega --version` prints `0.1.0`
- [ ] `bodega --help` shows help text
- [ ] `pytest` runs (even with no tests yet)
- [ ] Package structure matches the design

## Notes

- Use `src/` layout for proper package isolation
- All modules should be empty stubs initially (just pass or docstrings)
