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

  Scenario: An unavailable review is recorded as a gap and not as zero findings
    Given the AI assist flag is on
    And the OpenAI client is stubbed to be unavailable
    When I request a review of that chapter
    Then the review is recorded as not run and not as zero findings
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    And the live OpenAI API was not called

  Scenario: A stubbed rewrite is stored as a gap note and the chapter body is unchanged
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the rewrite "A model wrote this chapter instead of the writer."
    When I request a review of that chapter
    Then the rewrite "A model wrote this chapter instead of the writer." is stored only as a gap note
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."
    And the live OpenAI API was not called

  Scenario: An empty chapter stores no invented findings
    Given that chapter body is empty
    And the AI assist flag is on
    And the OpenAI client is stubbed to invent "INVENTED_DRAGON_HARBOR"
    When I request a review of that chapter
    Then the review stores no invented finding "INVENTED_DRAGON_HARBOR"
    And the stored chapter body is empty
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
    And I run the review from the keyboard
    Then the chapter page says the review did not run
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
  Scenario: An empty chapter says there is nothing to check
    Given that chapter body is empty
    And the AI assist flag is on
    And the OpenAI client is stubbed to invent "INVENTED_DRAGON_HARBOR"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then the chapter page says there is nothing to check
    And the chapter shows no invented finding "INVENTED_DRAGON_HARBOR"
    And the stored chapter body is empty

  @pending-review-panel
  Scenario: Each finding row has only the question, Jump, and Dismiss
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" anchored at "The river kept its course"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then each finding row has only the question, Jump, and Dismiss

  @pending-review-panel
  Scenario: Jump puts the caret at the finding's start offset
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" anchored at "The river kept its course"
    And each finding stores a start offset and a short quote
    When I open that chapter in the editor
    And I run the review from the keyboard
    And I jump to that finding from the keyboard
    Then the caret is at that finding's start offset
    And the manuscript was scrolled into view
    And focus stays in the chapter
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  @pending-review-panel
  Scenario: Jump does not move the caret when the quoted passage has changed
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the question "Does the river stay in the valley?" anchored at "The river kept its course"
    And each finding stores a start offset and a short quote
    When I open that chapter in the editor
    And I run the review from the keyboard
    And I edit the chapter body to "The morning stayed with one sentence." and autosave
    Then the finding row says the passage has changed
    And Jump does not move the caret to the wrong place
    And the stored chapter body is exactly "The morning stayed with one sentence."

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
