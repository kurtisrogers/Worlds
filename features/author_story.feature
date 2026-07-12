Feature: Author creates and publishes a story
  As an emerging author
  I want to create a story and add chapters
  So that readers can discover my work

  Scenario: Author registers and creates a story
    Given I am on the home page
    When I register as "alice" with password "securepass123"
    And I create a story titled "Moonlit Paths" with synopsis "A journey under starlight"
    Then I should see "Moonlit Paths" on my dashboard

  Scenario: Author adds a chapter via the editor
    Given I am logged in as "alice" with password "securepass123"
    And I have a story "Moonlit Paths"
    When I add chapter 1 titled "Dawn" with content "The path began at dawn."
    Then chapter 1 should be readable on the story page
