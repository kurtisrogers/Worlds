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

`make behave` excludes `@pending-review-panel` and `@pending-review-api`. The review API from #6 is on main, so those API scenarios run in the default job. Panel scenarios stay pending until #5. Scenarios that need review `state` (`ran`, `failed`, `empty`, or `off`) or the anchor fields stay pending until PR #28 is on main. They fail closed, and the failure names #28. `make test-review-e2e` runs the pending scenarios as well.

```bash
make test-review-e2e
```

That target runs `features/chapter_review.feature` on the host with `config.settings.test`, including the pending scenarios. It does not use the app container. The OpenAI client is stubbed at `editor.assist.get_provider`, and `urllib.request.urlopen` refuses `openai.com`. No API key is required.

When the panel and the API exist, a pending scenario can pass only if the chapter page itself shows the outcome. The review control is a keyboard button, link, or submit input named Review. Its request is a form POST, `formaction`, `hx-post`, or `data-url` to the review route, not the chapter autosave form. After that request, the page has `#review-panel` or a region named with "review". With `anchor_status: ok`, Jump is a keyboard control that puts the caret at `start_offset` in the manuscript. That offset is read from the browser caret (UTF-16 code units), the caret is scrolled into view, and focus stays in the chapter. When `anchor_status` is not `ok`, `start_offset` is absent or null, and the row keeps the question and Dismiss and has no Jump control, including a disabled one. `changed` shows "This passage has changed". `none` shows "Can't find this passage in the chapter". A quote that is still at its stored offset is `ok` even when it also appears elsewhere, and Jump lands on that stored offset. A quote that has moved and appears exactly once is `ok` at that new UTF-16 offset, and Jump puts the caret there and scrolls it into view. A quote that has moved and now appears more than once is `none`. Running Review again replaces the loaded rows when the response arrives. Those rows may stay visible while the review is running, and a finding is never shown twice. Dismiss is a keyboard control named Dismiss that POSTs somewhere other than autosave. A review that did not run shows exactly "The review did not run. Your chapter hasn't changed." A quiet run shows exactly "No questions this time. Your chapter hasn't changed." and no question row or Dismiss. An empty chapter shows exactly "There's nothing to review yet." The page never says "no gaps". A review that returns questions leaves the status line blank. "This is assistance, not authorship." stays under the Review heading. If the save fails, no review request is sent and the status line says exactly "Your chapter didn't save, so the review didn't run."

## Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## CI

GitHub Actions runs pytest, behave, and pre-commit on every push. A separate review-e2e job runs `make test-review-e2e`. Pending panel scenarios fail there until #5. Anchor scenarios fail there until PR #28 is on main. That job does not fail the default test job.

AI tests stub the OpenAI provider. Do not call the live OpenAI API from tests or CI.
