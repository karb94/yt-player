Feature: Update channels

  Scenario: Update channels with no existing channels
    Given no channels in the channel table
    When the channels are updated with channel A
    Then the channel A should be in the channel table

  Scenario: Update channels with new channel when database already contains a video from a different channel
    Given channel A is in the channel table
    And video A1 from channel A is in the video table
    When the channels are updated with channel B
    Then the channel A should not be in the channel table
    And the video A1 should not be in the video table
    And the channel B should be in the channel table

  Scenario: Update channels with an existing channel with video
    Given channel A is in the channel table
    And video A1 from channel A is in the video table
    When the channels are updated with channel A
    Then the channel A should be in the channel table
    And the video A1 should be in the video table
