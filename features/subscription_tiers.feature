Feature: Subscription tiers
  As a reader
  I want to subscribe to support an author
  So that I can access tier-gated chapters

  Scenario: Tier-gated chapter shows lock prompt
    Given a published story "Gold Tale" with a silver-tier chapter 2
    When I visit chapter 2 of "Gold Tale"
    Then I should see "This chapter is locked"
