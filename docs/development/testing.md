# Testing

## pytest (functional tests)

```bash
pytest
pytest --cov=. --cov-report=term-missing
```

## behave (BDD)

```bash
behave features/
```

## Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## CI

GitHub Actions runs pytest, behave, and pre-commit on every push.
