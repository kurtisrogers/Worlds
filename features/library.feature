Feature: Reader library collection
  As a reader
  I want to save books and follow authors
  So that I can build my personal library

  Scenario: Reader saves a book to their library
    Given a published story "The Harbor" with a free chapter 1
    And I am logged in as "bob" with password "securepass123"
    When I save "The Harbor" to my library
    Then I should see "The Harbor" in my saved library

  Scenario: Reader follows an author
    Given a published story "The Harbor" with a free chapter 1
    And I am logged in as "bob" with password "securepass123"
    When I follow the author of "The Harbor"
    Then I should be following that author
