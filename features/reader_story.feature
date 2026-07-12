Feature: Reader discovers and reads free chapters
  As a reader
  I want to browse and read free chapters
  So that I can support authors I enjoy

  Scenario: Reader views the home page
    Given I am on the home page
    Then I should see "Stories worth telling"

  Scenario: Reader reads a free chapter
    Given a published story "The Harbor" with a free chapter 1
    When I visit chapter 1 of "The Harbor"
    Then I should see the chapter content
