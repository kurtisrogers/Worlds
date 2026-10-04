# AI creative partner

One rule: the writer keeps the words. OpenAI is the only provider. The editor still works when AI is off or when OpenAI is down.

## Product rules

- Suggest, question, and highlight. Do not write the story.
- Never replace chapter text unless the writer takes a separate, explicit action that names that replacement.
- The writer can dismiss or ignore every finding. Dismiss does not edit the chapter.
- No silent rewrite of a draft or a published chapter.
- On-screen copy says this is assistance, not authorship.
- No “generate chapter” as a primary action.
- No second model provider until this OpenAI path is in use and these rules hold.

When an assist succeeds, the response carries the sentence "This is assistance, not authorship." The chapter page has no control that calls a model, and it has no review control.

## The editor

With the AI flag off, opening and editing a chapter makes no call to OpenAI. The editor behaves as it does without AI. Autosave writes the title and the chapter text the writer submitted. It does not apply a model replacement.

There is no API whose effect is to replace a chapter body without a separate writer confirmation that refers to that replacement. Assist does not write the chapter. Dismiss does not edit the chapter.

If OpenAI returns an error or times out, the chapter text is unchanged and the writer can keep editing. The assist shows a failure, not an empty manuscript.

## Prompts

The client cannot set the system prompt. Prompts and policies are assembled on the server from the stored chapter. A request that tries to send a prompt, a model, or replacement text is rejected and OpenAI is not called.

## Credential

The OpenAI credential is read from the environment or from the platform's secrets (`OPENAI_API_KEY`). It is not in the repo and it is not sent to the browser.

## What is recorded

Each AI call records who invoked it, when, which story, which chapter, and which model. The record may also keep token counts and a cost in cents, because that is how a spend cap is enforced. The provider on that record is OpenAI.

Prompt text and response text are not stored. They are not written to the database and they are not written to application logs. They are used to answer that one request and then discarded. This is what happens to prompt and response text before the flag is turned on outside local development. Do not turn the flag on in a shared environment until this still holds.

## Rate limit and spend cap

A configured per-user rate limit and a configured spend cap reject further calls with a visible message. No numeric cap is fixed in this project. Local development may run without the cap. Any shared environment must have both caps before the flag is on.

`WORLDS_ENVIRONMENT=local` is a single writer's machine. Anything else is shared: set `WORLDS_ENVIRONMENT=shared`. If a shared environment turns the flag on without both caps, calls are rejected and OpenAI is not contacted.

Both caps means:

- `AI_USER_RATE_LIMIT` and `AI_USER_RATE_WINDOW_SECONDS` are both set
- `AI_SPEND_CAP_CENTS` is set

A spend cap also needs `OPENAI_INPUT_CENTS_PER_MILLION_TOKENS` and `OPENAI_OUTPUT_CENTS_PER_MILLION_TOKENS`, so a call has a cost. Those prices are configuration. They are not a cap chosen by this project. If a spend cap is set and the prices are missing, the call is rejected and OpenAI is not contacted. If a successful call does not report token use, that call spends the rest of the cap.

`AI_ASSIST_ENABLED` is false by default.
