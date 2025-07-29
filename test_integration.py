#!/usr/bin/env python3
"""
Simple integration test for ConfigManager.
"""
from src.config_manager import ConfigManager
from src.models import QuizSettings

def main():
    print("Testing ConfigManager integration...")
    
    # Test initialization
    config = ConfigManager()
    print("✓ ConfigManager initialized successfully")
    
    # Test default settings
    settings = config.get_quiz_settings()
    assert isinstance(settings, QuizSettings)
    assert settings.question_count is None
    assert settings.random_order is False
    assert settings.timer_duration == 10
    print("✓ Default settings are correct")
    
    # Test setting configurations
    assert config.set_question_count(15) is True
    assert config.set_random_order(True) is True
    assert config.set_timer_duration(30) is True
    print("✓ Configuration settings work correctly")
    
    # Test validation
    validation = config.validate_settings()
    assert validation["valid"] is True
    assert len(validation["issues"]) == 0
    print("✓ Settings validation works correctly")
    
    # Test settings summary
    summary = config.get_settings_summary()
    assert "15" in summary
    assert "random" in summary
    assert "30 seconds" in summary
    print("✓ Settings summary works correctly")
    
    print("\n🎉 All integration tests passed!")

if __name__ == "__main__":
    main()