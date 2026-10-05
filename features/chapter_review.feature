Feature: Chapter review asks questions without writing the manuscript
  As a writer
  I want a review to point at a place in my chapter
  So that I can decide what to do with my own words

  Scenario: Run a review, see a finding, and dismiss it without changing the chapter
    Given the AI flag is on and the review model is stubbed
    And I am logged in as "alice" with password "securepass123"
    And I have a story "Moonlit Paths"
    When I add chapter 1 titled "Dawn" with content "The river kept its course through the quiet valley, and the morning stayed with that one sentence."
    And I open chapter 1 in the editor
    Then the editor offers Review
    And the editor has not called the model
    When I run a review of chapter 1
    Then I see the finding "Does the river stay in the valley?"
    And chapter 1 still reads "The river kept its course through the quiet valley, and the morning stayed with that one sentence."
    When I dismiss that finding
    Then the editor no longer shows "Does the river stay in the valley?"
    And chapter 1 still reads "The river kept its course through the quiet valley, and the morning stayed with that one sentence."
    And the review used the stubbed finding

  Scenario: The chapter page has no review action when AI is off
    Given the AI flag is off
    And I am logged in as "alice" with password "securepass123"
    And I have a story "Moonlit Paths"
    When I add chapter 1 titled "Dawn" with content "The river kept its course through the quiet valley, and the morning stayed with that one sentence."
    And I open chapter 1 in the editor
    Then the editor does not offer Review
    And the editor has not called the model
