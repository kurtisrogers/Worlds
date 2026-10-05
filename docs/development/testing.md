# Testing

## pytest (functional tests)

```bash
pytest
pytest --cov=. --cov-report=term-missing
```

## behave (BDD)

```bash
behave features/
make behave
```

`make behave` excludes `@pending-review-panel` and `@pending-review-api`. Those chapter-review scenarios fail closed until the review panel (#5) and the review API (#6) exist. The default run does not execute them. `make test-review-e2e` does, and they fail while that surface is missing.

```bash
make test-review-e2e
```

That target runs `features/chapter_review.feature` on the host with `config.settings.test`, including the pending scenarios. It does not use the app container. The OpenAI client is stubbed at `editor.assist.get_provider`, and `urllib.request.urlopen` refuses `openai.com`. No API key is required.

When the panel and the API exist, a pending scenario can pass only if the chapter page itself shows the outcome. The review control is a keyboard button, link, or submit input named Review. Its request is a form POST, `formaction`, `hx-post`, or `data-url` to the review route, not the chapter autosave form. After that request, the page has `#review-panel` or a region named with "review". Jump is a keyboard control named Jump that targets `manuscript`. Dismiss is a keyboard control named Dismiss that POSTs somewhere other than autosave. A review that did not run shows "did not run" or "Nothing proved", and the page never says "no gaps". An empty chapter shows "nothing to check".

## Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## CI

GitHub Actions runs pytest, behave, and pre-commit on every push. A separate review-e2e job runs `make test-review-e2e`. Pending scenarios fail there until #5 and #6 land. That job does not fail the default test job.

AI tests stub the OpenAI provider. Do not call the live OpenAI API from tests or CI.
