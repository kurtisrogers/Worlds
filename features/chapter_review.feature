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

  # Pending until the review panel (#5) and the review API (#6) are on main.
  @pending-review-panel @pending-review-api
  Scenario: A stubbed review leaves the chapter byte-for-byte unchanged
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

  # Pending until the review panel (#5) and the review API (#6) are on main.
  @pending-review-panel @pending-review-api
  Scenario: A failed review says it did not run and not that there are no gaps
    Given the AI assist flag is on
    And the OpenAI client is stubbed to be unavailable
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then the chapter page says the review did not run
    And the chapter page does not say there are no gaps
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  # Pending until the review panel (#5) and the review API (#6) are on main.
  @pending-review-panel @pending-review-api
  Scenario: A stubbed rewrite never reaches the chapter body
    Given the AI assist flag is on
    And the OpenAI client is stubbed to return the rewrite "A model wrote this chapter instead of the writer."
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then the rewrite "A model wrote this chapter instead of the writer." is not in the chapter or the review panel
    And the chapter page does not say there are no gaps
    And the stored chapter body is byte-for-byte "The river kept its course through the quiet valley."

  # Pending until the review panel (#5) and the review API (#6) are on main.
  @pending-review-panel @pending-review-api
  Scenario: An empty chapter yields no invented findings
    Given that chapter body is empty
    And the AI assist flag is on
    And the OpenAI client is stubbed to invent "INVENTED_DRAGON_HARBOR"
    When I open that chapter in the editor
    And I run the review from the keyboard
    Then the chapter page says there is nothing to check
    And the chapter shows no invented finding "INVENTED_DRAGON_HARBOR"
    And the stored chapter body is empty
