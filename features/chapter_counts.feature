Feature: Counts on released chapters
  As an author
  I want counts for chapters I have released
  So that I can see reads, likes, and favourites without seeing who they were

  Scenario: Author sees counts for released chapters only
    Given I am logged in as "alice" with password "securepass123"
    And I have a story "Moonlit Paths"
    And chapter 1 of "Moonlit Paths" is released
    And chapter 2 of "Moonlit Paths" is a draft
    When a reader "sam" records a read of chapter 1 of "Moonlit Paths"
    And a reader "sam" records a read of chapter 1 of "Moonlit Paths"
    And a reader "sam" records a read of chapter 2 of "Moonlit Paths"
    And a reader "sam" likes chapter 1 of "Moonlit Paths"
    And a reader "sam" likes chapter 1 of "Moonlit Paths"
    And I request the chapter counts for "Moonlit Paths"
    Then chapter 1 counts are 1 reads, 1 likes, and 0 favourites
    And the counts do not include chapter 2
    And the counts do not name "sam"
