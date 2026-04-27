# Contributing to Plector

We love your input! We want to make contributing as easy and transparent as possible.

---

## Development Process

We use GitHub Flow. All changes happen through pull requests:

1. Fork the repo and create your branch from `master`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes (pre-commit hooks must pass)
5. Make sure your code lints (`ruff check`)
6. Issue that pull request!

---

## Pull Request Process

1. Update the relevant documentation if you change/remove features
2. Update CHANGELOG.md with a note describing your changes
3. The PR will be merged once you have the sign-off of at least one maintainer

---

## Code Style

We follow the project's code standards defined in `docs/standards/`:

- [Code Standard](../docs/standards/Code_Standard_Plector.md) - Python code style
- [Naming Convention](../docs/standards/Naming_Convention_Plector.md) - Naming rules
- [Skill Development](../docs/standards/Skill_Development_Plector.md) - Skill development guidelines

---

## Commit Message Format

We follow Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Example

```
feat(skills): add memory skill for knowledge storage

- Add VectorMemory class with 8 recall modes
- Implement Ebbinghaus decay curve
- Add LLM auto-association on save

Closes #123
```

---

## Setting Up Development Environment

```bash
# Clone your fork
git clone https://github.com/<your-username>/Plector.git
cd Plector

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
python -m pytest

# Run linter
ruff check core/ skills/ channels/
```

---

## Testing

We use pytest for unit tests. Run:

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_closure_engine.py -v
```

---

## Skills Development

See the [Skill Development Guide](../docs/standards/Skill_Development_Plector.md) for detailed instructions on creating new skills.

### Quick Start

```bash
# Generate skill scaffold
python scripts/generate_skill.py my_new_skill

# Validate skill format
python scripts/validate_skills.py
```

---

## Bug Reports

Please include:

1. A clear description of the problem
2. Steps to reproduce
3. Expected vs actual behavior
4. Python version and OS
5. Relevant logs or error messages

---

## Feature Requests

We welcome feature requests! Please:

1. Check if a similar feature already exists
2. Describe the problem you're trying to solve
3. Explain why this feature would benefit the project

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

- Open an issue for bugs/feature requests
- Check the [documentation](../docs/DOCS_INDEX.md) for guides
- Join discussions in GitHub Issues
