Feature: One-chapter review asks questions and never writes the manuscript
  The chapter is the page. The model asks questions and never writes,
  inserts, or scores the manuscript. A review that did not run must say so.
  It must not look like a chapter with no gaps.

  Background:
    Given I am writing chapter "Dawn" of "Quiet Valley" as "mira"
    And that chapter body is "The river kept its course through the quiet valley."

  Scenario: Flag off leaves no review control and stores only the writer's edit
    Given the AI assist flag is off
    And the OpenAI client is stubbed to return the rewrite "A model wrote this chapter instead of the writer."
    When I open that chapter in the editor
    Then the chapter page has no review control
    And the chapter page does not say there are no gaps
    When I edit the chapter body to "The river kept its course through the quiet valley. The water was cold." and autosave
    Then the stored chapter body is exactly "The river kept its course through the quiet valley. The water was cold."
    And the OpenAI client was not called

  Scenario: There is no insert, replace, or accept control or route for model text
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the rewrite "A model wrote this chapter instead of the writer."
    When I open that chapter in the editor
    Then the chapter page has no insert, replace, or accept control
    And there is no route that writes model text into the chapter
    And the stored chapter body is exactly "The river kept its course through the quiet valley."
    And the OpenAI client was not called

  Scenario: Autosave still saves while the model is unavailable
    Given the AI assist flag is on
    And the OpenAI client is stubbed to be unavailable
    When I edit the chapter body to "The river kept its course through the quiet valley. The water was cold." and autosave
    Then the autosave response is "Saved"
    And the stored chapter body is exactly "The river kept its course through the quiet valley. The water was cold."
    And the live OpenAI API was not called

  Scenario: A stubbed review stores one open finding and dismiss only changes its status
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" anchored at "The river kept its course"
    When I request a review of that chapter
    Then the review records one open finding "Does the river stay in the valley?"
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    When I dismiss that finding through the review API
    Then that finding is dismissed without rewriting the chapter
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  Scenario: An unavailable review is recorded as a provider error and changes nothing
    Given the AI assist flag is on
    And the OpenAI client is stubbed to be unavailable
    When I request a review of that chapter
    Then the review is recorded as a provider error
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    And the live OpenAI API was not called

  Scenario: A stubbed rewrite is stored as a gap note and the chapter body is unchanged
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the rewrite "A model wrote this chapter instead of the writer."
    When I request a review of that chapter
    Then the rewrite "A model wrote this chapter instead of the writer." is stored only as a gap note
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    And the live OpenAI API was not called

  # Panel (#5). The review API is already on main.
  @pending-review-panel
  Scenario: The panel shows a question and keyboard jump and dismiss leave the chapter unchanged
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" anchored at "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then the review panel shows "Does the river stay in the valley?"
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    When I jump to that finding from the keyboard
    Then the manuscript focus is the place "The river kept its course"
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    When I dismiss that finding from the keyboard
    Then the review panel does not show "Does the river stay in the valley?"
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-panel
  Scenario: A review that did not run says so in the panel and never says there are no gaps
    Given the AI assist flag is on
    And the OpenAI client is stubbed to be unavailable
    When I open that chapter in the editor
    And I run the review from the keyboard in the browser
    Then the review panel says exactly "The review did not run. Your chapter hasn't changed."
    And the chapter page does not say there are no gaps
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-panel
  Scenario: A rewrite never appears in the review panel
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the rewrite "A model wrote this chapter instead of the writer."
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then the rewrite "A model wrote this chapter instead of the writer." is not in the chapter or the review panel
    And the chapter page does not say there are no gaps
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-panel
  Scenario: An empty chapter says there is nothing to review yet
    Given that chapter body is empty
    And the AI assist flag is on
    And the OpenAI client is stubbed to invent "INVENTED_DRAGON_HARBOR"
    When I open that chapter in the editor
    And I run the review from the keyboard in the browser
    Then the review panel says exactly "There's nothing to review yet."
    And the chapter page does not say there are no gaps
    And the chapter shows no invented finding "INVENTED_DRAGON_HARBOR"
    And the stored chapter body is empty

  @pending-review-panel
  Scenario: A quiet run shows no question row and only the no-questions line
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return no findings
    When I open that chapter in the editor
    And I run the review from the keyboard in the browser
    Then the review panel says exactly "No questions this time. Your chapter hasn't changed."
    And the review panel shows no question row and no Dismiss
    And the quiet run stores no finding row
    And the review panel does not say "The review did not run. Your chapter hasn't changed."
    And the chapter page does not say there are no gaps
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-panel
  Scenario: Each finding row has only the question, Jump, and Dismiss
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" anchored at "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then each finding row has only the question, Jump, and Dismiss

  # PR #28 is not on main. These fail closed on quote, start_offset, and anchor_status.
  @pending-review-panel
  Scenario: Jump with an ok anchor puts the caret at the browser offset
    Given each finding returns quote, start_offset, and anchor_status
    And the AI assist flag is on
    And that chapter places "The river kept its course through the quiet valley." below the fold
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then that finding's anchor_status is "ok"
    When I jump to that finding from the keyboard in the browser
    Then the browser caret is at that finding's start offset
    And the manuscript caret is scrolled into view
    And focus stays in the chapter
    And the chapter text is unchanged

  @pending-review-panel
  Scenario: Jump counts an emoji before the quote as two browser characters
    Given each finding returns quote, start_offset, and anchor_status
    And the AI assist flag is on
    And that chapter places "café 😀 The river kept its course and then the valley." below the fold
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then that finding's anchor_status is "ok"
    When I jump to that finding from the keyboard in the browser
    Then the browser caret is at that finding's start offset
    And the browser caret counts the emoji before the quote as two characters
    And the manuscript caret is scrolled into view
    And focus stays in the chapter
    And the chapter text is unchanged

  @pending-review-panel
  Scenario: A gone quote keeps the question and Dismiss and has no Jump control
    Given each finding returns quote, start_offset, and anchor_status
    And the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    And I edit the chapter body to "The morning stayed with one sentence." and autosave
    Then that finding's anchor_status is "changed"
    And the finding row shows "This passage has changed"
    And the finding row keeps the question and Dismiss and has no Jump control
    And the stored chapter body is exactly "The morning stayed with one sentence."

  @pending-review-panel
  Scenario: A finding with no anchor keeps the question and Dismiss and has no Jump control
    Given each finding returns quote, start_offset, and anchor_status
    And the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "A harbor the chapter never names"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then that finding's anchor_status is "none"
    And the finding row shows "Can't find this passage in the chapter"
    And the finding row keeps the question and Dismiss and has no Jump control
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  # UX is confirming this. The quote is still at its stored offset and also
  # appears later, so the status is ok and Jump uses that stored offset.
  # Flip the expected result if UX disagrees.
  @pending-review-panel
  Scenario: A quote that is still at its stored offset stays ok when it also appears elsewhere
    Given each finding returns quote, start_offset, and anchor_status
    And the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    And I edit the chapter body to "The river kept its course through the quiet valley. The river kept its course." and autosave
    Then that finding's anchor_status is "ok"
    And Jump lands at the stored offset
    And the stored chapter body is exactly "The river kept its course through the quiet valley. The river kept its course."

  @pending-review-panel
  Scenario: A quote that moved and appears more than once has no Jump control
    Given each finding returns quote, start_offset, and anchor_status
    And the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    And I edit the chapter body to "Morning came. The river kept its course. The river kept its course." and autosave
    Then that finding's anchor_status is "none"
    And the finding row shows "Can't find this passage in the chapter"
    And the finding row keeps the question and Dismiss and has no Jump control
    And the stored chapter body is exactly "Morning came. The river kept its course. The river kept its course."

  @pending-review-panel
  Scenario: Running Review again replaces the loaded rows when the response arrives
    Given the AI assist flag is on
    And an open finding "Does the river stay in the valley?" is already stored on that chapter
    And the OpenAI client is stubbed to hold the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard in the browser
    Then no finding is shown twice while the review is running
    When the held review response is released
    Then the open finding "Does the river stay in the valley?" is shown once

  @pending-review-panel
  Scenario: Review waits for a pending save and uses the on-screen text
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I type "Later " at the start of the chapter while the save is held
    And I run the review from the keyboard in the browser
    Then the save finishes before the review request
    And the review offset matches the on-screen text

  @pending-review-panel
  Scenario: Review says Reviewing and ignores a second press
    Given the AI assist flag is on
    And the OpenAI client is stubbed to hold the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard in the browser
    And I run the review from the keyboard in the browser again
    Then the status line says "Reviewing…" and only one review request was sent
    When the held review response is released
    Then the review panel shows "Does the river stay in the valley?"

  @pending-review-panel
  Scenario: A review that returns questions leaves the status line blank
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard in the browser
    Then the review status line is blank
    And the review status line does not say "This is assistance, not authorship."
    And "This is assistance, not authorship." stays under the Review heading
    And the review panel shows "Does the river stay in the valley?"

  @pending-review-panel
  Scenario: A failed save stops the review before it starts
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I open that chapter in the editor
    And I type "Later " at the start of the chapter and the save will fail
    And I run the review from the keyboard in the browser
    Then the review status line says "Your chapter didn't save, so the review didn't run."
    And no review request was sent

  @pending-review-panel
  Scenario: Dismiss moves focus and a failed dismiss keeps the row
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return two open questions
    When I open that chapter in the editor
    And I run the review from the keyboard in the browser
    And the next dismiss request will fail
    And I dismiss the finding "Does the river stay in the valley?" from the keyboard in the browser
    Then that finding is still in the review panel
    And the review status line says "Couldn't dismiss. Try again."
    When dismiss requests succeed again
    And I dismiss the finding "Does the river stay in the valley?" from the keyboard in the browser
    Then keyboard focus is on the finding "Does the morning stay quiet?"
    When I dismiss the finding "Does the morning stay quiet?" from the keyboard in the browser
    Then keyboard focus is on the Review heading

  # PR #28 is not on main. Responses carry state. These fail closed until it is.
  @pending-review-api
  Scenario: An unavailable review returns state failed
    Given a review response carries state
    And the AI assist flag is on
    And the OpenAI client is stubbed to be unavailable
    When I request a review of that chapter
    Then the review state is "failed"
    And the review stores no new finding row
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    And the live OpenAI API was not called

  @pending-review-api
  Scenario: A successful review supersedes the chapter's earlier open findings
    Given a review response carries state
    And the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I request a review of that chapter
    Then the review state is "ran"
    And the review records one open finding for "Does the river stay in the valley?"
    When the OpenAI client is stubbed to return the question "Does the morning stay quiet?" quoted as "the quiet valley"
    And I request a review of that chapter
    Then the review state is "ran"
    And the review returns only the open finding "Does the morning stay quiet?"
    And the finding "Does the river stay in the valley?" is superseded
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-api
  Scenario: A quiet run returns no findings and supersedes earlier open findings
    Given a review response carries state
    And the AI assist flag is on
    And an open finding "Does the river stay in the valley?" is already stored on that chapter
    And the OpenAI client is stubbed to return no findings
    When I request a review of that chapter
    Then the review state is "ran"
    And the review returns no findings
    And the review stores no new finding row
    And the finding "Does the river stay in the valley?" is superseded
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-api
  Scenario: A review that does not run does not supersede open findings
    Given a review response carries state
    And the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I request a review of that chapter
    Then the review records one open finding for "Does the river stay in the valley?"
    When the OpenAI client is stubbed to be unavailable
    And I request a review of that chapter
    Then the review state is "failed"
    And the review stores no new finding row
    And the finding "Does the river stay in the valley?" is still open
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-api
  Scenario: A dismissed finding stays dismissed after a later successful review
    Given a review response carries state
    And the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" quoted as "The river kept its course"
    When I request a review of that chapter
    Then the review records one open finding for "Does the river stay in the valley?"
    When I dismiss that finding through the review API
    Then that finding is dismissed without rewriting the chapter
    When the OpenAI client is stubbed to return the question "Does the morning stay quiet?" quoted as "the quiet valley"
    And I request a review of that chapter
    Then the review state is "ran"
    And the review returns only the open finding "Does the morning stay quiet?"
    And the finding "Does the river stay in the valley?" is still dismissed
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-api
  Scenario: An empty chapter returns state empty and does not call the model
    Given a review response carries state
    And the AI assist flag is on
    And an open finding "Does the river stay in the valley?" is already stored on that chapter
    And that chapter body is empty
    And the OpenAI client is stubbed to invent "INVENTED_DRAGON_HARBOR"
    When I request a review of that chapter
    Then the review state is "empty"
    And the OpenAI client was not called
    And the finding "Does the river stay in the valley?" is still open
    And the review invents no finding "INVENTED_DRAGON_HARBOR"
    And the stored chapter body is empty

  @pending-review-api
  Scenario: A review while assist is off returns state off
    Given a review response carries state
    And the AI assist flag is off
    And the OpenAI client is stubbed to invent "INVENTED_DRAGON_HARBOR"
    When I request a review of that chapter
    Then the review state is "off"
    And the OpenAI client was not called
    And the review invents no finding "INVENTED_DRAGON_HARBOR"
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-panel
  Scenario: Autosave still saves while the review panel is open
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" anchored at "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then the review panel shows "Does the river stay in the valley?"
    When I edit the chapter body to "The river kept its course through the quiet valley. The water was cold." and autosave
    Then the autosave response is "Saved"
    And the review panel shows "Does the river stay in the valley?"
    And the stored chapter body is exactly "The river kept its course through the quiet valley. The water was cold."
