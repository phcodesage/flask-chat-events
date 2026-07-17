# Contributing to flask-chat-events

Thanks for your interest in improving flask-chat-events! Contributions of all
kinds are welcome — bug reports, documentation fixes, new features, and tests.

## Ground rules

- Be respectful. This project follows a [Code of Conduct](CODE_OF_CONDUCT.md).
- Keep the public API stable. Additions should be backward-compatible; anything
  that changes existing event **names** or **payloads** is a breaking change and
  needs a version bump discussion first (open an issue).
- Every behavior change ships with a test.

## Development setup

Requires **Python 3.11+**.

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/flask-chat-events.git
cd flask-chat-events

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install the package with dev + test extras (editable)
pip install -e ".[dev]"
```

## Running the checks

The same checks run in CI, so run them locally before pushing:

```bash
# Tests
pytest -q

# Formatting (Black, line length 88)
black flask_chat_events tests examples
black --check .          # what CI-style verification would see
```

CI runs the test suite on Python 3.11, 3.12, and 3.13. Please make sure your
change passes on your local interpreter at minimum.

## Making a change

1. Create a branch off `main`: `git checkout -b fix/short-description`.
2. Make your change and add or update tests under `tests/`.
3. Run `pytest` and `black` (see above).
4. Commit with a clear message. We loosely follow
   [Conventional Commits](https://www.conventionalcommits.org/)
   (`fix:`, `feat:`, `docs:`, `chore:`, `test:`).
5. Push to your fork and open a Pull Request against `main`.

## Pull request expectations

- Describe **what** changed and **why**. Link any related issue.
- Keep PRs focused — one logical change per PR is easiest to review.
- Update the README/examples if you changed or added public behavior.
- The CI test job must be green before a maintainer merges.

## Releases (maintainers)

Releases are automated. On a push to `main` that passes tests, CI bumps the
patch version, tags it, and publishes to PyPI via Trusted Publishing. You do not
need to bump the version in your PR — leave `version` in `pyproject.toml` alone.

## Reporting bugs & requesting features

Open an issue using the provided templates. For security issues, please follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.

Thanks again for contributing! 🎉
