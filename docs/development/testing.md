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

GitHub Actions runs pytest, behave, and pre-commit on every push. The `openai-key-gate` job runs `make check-openai-key` on the same commit. That job is separate from the test job, so it still runs when another job is added to `.github/workflows/ci.yml`, including `review-e2e` (`make test-review-e2e`).

CI does not set `OPENAI_API_KEY` and does not call the live API. `AI_ASSIST_ENABLED` is `"false"` on the workflow, so every job inherits it, including a review job added later. Do not turn the flag on in CI.

AI tests stub the OpenAI provider. Do not call the live OpenAI API from tests or CI.

### OpenAI key fixture

`scripts/no_openai_key.py --self-test` writes an OpenAI-style key into a temporary file and checks that the scan exits non-zero. It also checks that an empty `OPENAI_API_KEY`, the Stripe `sk_test_` shape, and `sk-test-not-a-real-key` do not fail. The temporary file is the fixture. It is not committed: a key in tracked content fails pre-commit and fails `openai-key-gate`. The report names the file and line and does not print the key. `tests/test_no_openai_key.py` runs the same gate.
