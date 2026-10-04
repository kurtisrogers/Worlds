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

AI tests stub the OpenAI provider. Do not call the live OpenAI API from tests or CI.
