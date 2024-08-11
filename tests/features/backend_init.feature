Feature: Backend initialization

  Scenario: Initialize backend with empty database
    When the backend is initialized:
      - with empty database
      - with empty thumbnail and video directories
      - without channels
    Then the channel and video tables should be created
    And the thumbnail and video directories should be created
    And the thumbnail and video directories should be stored in the Backend object
