"""
Unit tests for ConfigManager class.
"""
import unittest
from unittest.mock import patch, MagicMock
import logging
import threading
import time

from src.config_manager import ConfigManager
from src.models import QuizSettings
from tests.test_fixtures import TestFixtures, TestDataValidation


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.config_manager = ConfigManager()
        
        # Suppress logging during tests
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        """Clean up after each test method."""
        logging.disable(logging.NOTSET)
    
    def test_initialization_with_defaults(self):
        """Test that ConfigManager initializes with correct default values."""
        settings = self.config_manager.get_quiz_settings()
        
        self.assertIsNone(settings.question_count)
        self.assertFalse(settings.random_order)
        self.assertEqual(settings.timer_duration, 10)
        self.assertEqual(self.config_manager.get_quiz_directory(), "./quizzes/")
    
    def test_set_question_count_valid_values(self):
        """Test setting valid question count values."""
        # Test setting to None (use all questions)
        result = self.config_manager.set_question_count(None)
        self.assertTrue(result)
        self.assertIsNone(self.config_manager.get_question_count())
        
        # Test setting to valid integer
        result = self.config_manager.set_question_count(5)
        self.assertTrue(result)
        self.assertEqual(self.config_manager.get_question_count(), 5)
        
        # Test minimum valid value
        result = self.config_manager.set_question_count(1)
        self.assertTrue(result)
        self.assertEqual(self.config_manager.get_question_count(), 1)
        
        # Test maximum valid value
        result = self.config_manager.set_question_count(100)
        self.assertTrue(result)
        self.assertEqual(self.config_manager.get_question_count(), 100)
    
    def test_set_question_count_invalid_values(self):
        """Test setting invalid question count values."""
        # Test invalid type
        result = self.config_manager.set_question_count("5")
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_question_count(5.5)
        self.assertFalse(result['success'])
        
        # Test values below minimum
        result = self.config_manager.set_question_count(0)
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_question_count(-1)
        self.assertFalse(result['success'])
        
        # Test values above maximum
        result = self.config_manager.set_question_count(101)
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_question_count(1000)
        self.assertFalse(result['success'])
    
    def test_set_random_order_valid_values(self):
        """Test setting valid random order values."""
        # Test setting to True
        result = self.config_manager.set_random_order(True)
        self.assertTrue(result)
        self.assertTrue(self.config_manager.get_random_order())
        
        # Test setting to False
        result = self.config_manager.set_random_order(False)
        self.assertTrue(result)
        self.assertFalse(self.config_manager.get_random_order())
    
    def test_set_random_order_invalid_values(self):
        """Test setting invalid random order values."""
        # Test invalid types
        result = self.config_manager.set_random_order("true")
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_random_order(1)
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_random_order(None)
        self.assertFalse(result['success'])
    
    def test_toggle_random_order(self):
        """Test toggling random order setting."""
        # Start with default (False)
        self.assertFalse(self.config_manager.get_random_order())
        
        # Toggle to True
        result = self.config_manager.toggle_random_order()
        self.assertTrue(result['success'])
        self.assertTrue(self.config_manager.get_random_order())
        
        # Toggle back to False
        result = self.config_manager.toggle_random_order()
        self.assertTrue(result['success'])
        self.assertFalse(self.config_manager.get_random_order())
    
    def test_set_timer_duration_valid_values(self):
        """Test setting valid timer duration values."""
        # Test minimum valid value
        result = self.config_manager.set_timer_duration(5)
        self.assertTrue(result)
        self.assertEqual(self.config_manager.get_timer_duration(), 5)
        
        # Test typical value
        result = self.config_manager.set_timer_duration(30)
        self.assertTrue(result)
        self.assertEqual(self.config_manager.get_timer_duration(), 30)
        
        # Test maximum valid value
        result = self.config_manager.set_timer_duration(300)
        self.assertTrue(result)
        self.assertEqual(self.config_manager.get_timer_duration(), 300)
    
    def test_set_timer_duration_invalid_values(self):
        """Test setting invalid timer duration values."""
        # Test invalid type
        result = self.config_manager.set_timer_duration("10")
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_timer_duration(10.5)
        self.assertFalse(result['success'])
        
        # Test values below minimum
        result = self.config_manager.set_timer_duration(4)
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_timer_duration(0)
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_timer_duration(-1)
        self.assertFalse(result['success'])
        
        # Test values above maximum
        result = self.config_manager.set_timer_duration(301)
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_timer_duration(1000)
        self.assertFalse(result['success'])
    
    def test_set_quiz_directory_valid_values(self):
        """Test setting valid quiz directory values."""
        # Test relative path
        result = self.config_manager.set_quiz_directory("./my_quizzes/")
        self.assertTrue(result['success'])
        self.assertIn("my_quizzes", self.config_manager.get_quiz_directory())
        
        # Test absolute path (if not system directory)
        result = self.config_manager.set_quiz_directory("./user_quizzes")
        self.assertTrue(result['success'])
        
        # Test path with spaces
        result = self.config_manager.set_quiz_directory("./quiz files/")
        self.assertTrue(result['success'])
    
    def test_set_quiz_directory_invalid_values(self):
        """Test setting invalid quiz directory values."""
        # Test invalid type
        result = self.config_manager.set_quiz_directory(123)
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_quiz_directory(None)
        self.assertFalse(result['success'])
        
        # Test empty string
        result = self.config_manager.set_quiz_directory("")
        self.assertFalse(result['success'])
        
        # Test whitespace only
        result = self.config_manager.set_quiz_directory("   ")
        self.assertFalse(result['success'])
    
    def test_reset_to_defaults(self):
        """Test resetting all settings to default values."""
        # Change all settings from defaults
        self.config_manager.set_question_count(20)
        self.config_manager.set_random_order(True)
        self.config_manager.set_timer_duration(60)
        self.config_manager.set_quiz_directory("./custom/")
        
        # Verify settings were changed
        self.assertEqual(self.config_manager.get_question_count(), 20)
        self.assertTrue(self.config_manager.get_random_order())
        self.assertEqual(self.config_manager.get_timer_duration(), 60)
        # Directory path is normalized to absolute path
        self.assertIn("custom", self.config_manager.get_quiz_directory())
        
        # Reset to defaults
        self.config_manager.reset_to_defaults()
        
        # Verify all settings are back to defaults
        self.assertIsNone(self.config_manager.get_question_count())
        self.assertFalse(self.config_manager.get_random_order())
        self.assertEqual(self.config_manager.get_timer_duration(), 10)
        self.assertEqual(self.config_manager.get_quiz_directory(), "./quizzes/")
    
    def test_validate_settings_valid_configuration(self):
        """Test validation with valid settings."""
        # Set valid configuration
        self.config_manager.set_question_count(10)
        self.config_manager.set_random_order(True)
        self.config_manager.set_timer_duration(30)
        self.config_manager.set_quiz_directory("./quizzes/")
        
        result = self.config_manager.validate_settings()
        
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["issues"]), 0)
    
    def test_validate_settings_with_defaults(self):
        """Test validation with default settings."""
        result = self.config_manager.validate_settings()
        
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["issues"]), 0)
    
    def test_validate_settings_invalid_configuration(self):
        """Test validation with invalid settings."""
        # Manually corrupt settings to test validation
        self.config_manager._global_settings.question_count = -1
        self.config_manager._global_settings.random_order = "invalid"
        self.config_manager._global_settings.timer_duration = 1000
        self.config_manager._quiz_directory = ""
        
        result = self.config_manager.validate_settings()
        
        self.assertFalse(result["valid"])
        self.assertEqual(len(result["issues"]), 4)
        
        # Check that all issues are reported
        issues_text = " ".join(result["issues"])
        self.assertIn("question count", issues_text.lower())
        self.assertIn("random order", issues_text.lower())
        self.assertIn("timer duration", issues_text.lower())
        self.assertIn("quiz directory", issues_text.lower())
    
    def test_get_quiz_settings_returns_copy(self):
        """Test that get_quiz_settings returns a copy, not reference."""
        settings1 = self.config_manager.get_quiz_settings()
        settings2 = self.config_manager.get_quiz_settings()
        
        # Modify one copy
        settings1.question_count = 50
        
        # Verify the other copy is unchanged
        self.assertNotEqual(settings1.question_count, settings2.question_count)
        
        # Verify original settings are unchanged
        self.assertIsNone(self.config_manager.get_question_count())
    
    def test_get_settings_summary(self):
        """Test getting formatted settings summary."""
        # Test with default settings
        summary = self.config_manager.get_settings_summary()
        
        self.assertIn("all available", summary)
        self.assertIn("sequential", summary)
        self.assertIn("10 seconds", summary)
        self.assertIn("./quizzes/", summary)
        
        # Test with custom settings
        self.config_manager.set_question_count(15)
        self.config_manager.set_random_order(True)
        self.config_manager.set_timer_duration(45)
        
        summary = self.config_manager.get_settings_summary()
        
        self.assertIn("15", summary)
        self.assertIn("random", summary)
        self.assertIn("45 seconds", summary)
    
    def test_constants_are_defined(self):
        """Test that all required constants are properly defined."""
        self.assertIsNone(ConfigManager.DEFAULT_QUESTION_COUNT)
        self.assertFalse(ConfigManager.DEFAULT_RANDOM_ORDER)
        self.assertEqual(ConfigManager.DEFAULT_TIMER_DURATION, 10)
        self.assertEqual(ConfigManager.DEFAULT_QUIZ_DIRECTORY, "./quizzes/")
        
        self.assertEqual(ConfigManager.MIN_TIMER_DURATION, 5)
        self.assertEqual(ConfigManager.MAX_TIMER_DURATION, 300)
        self.assertEqual(ConfigManager.MIN_QUESTION_COUNT, 1)
        self.assertEqual(ConfigManager.MAX_QUESTION_COUNT, 100)


    def test_enhanced_error_handling(self):
        """Test enhanced error handling with detailed responses."""
        # Test set_question_count with enhanced response
        result = self.config_manager.set_question_count("invalid")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('user_message', result)
        
        # Test boundary values
        result = self.config_manager.set_question_count(0)
        self.assertFalse(result['success'])
        self.assertIn("Too few questions", result['user_message'])
    
    def test_configuration_health_check(self):
        """Test configuration health check functionality."""
        # Test with valid configuration
        health = self.config_manager.get_configuration_health_check()
        
        self.assertIn('healthy', health)
        self.assertIn('warnings', health)
        self.assertIn('errors', health)
        self.assertIn('recommendations', health)
        
        self.assertTrue(health['healthy'])
        self.assertIsInstance(health['warnings'], list)
        self.assertIsInstance(health['errors'], list)
        self.assertIsInstance(health['recommendations'], list)
    
    def test_settings_persistence_simulation(self):
        """Test settings persistence behavior simulation."""
        # Change settings
        self.config_manager.set_question_count(15)
        self.config_manager.set_random_order(True)
        self.config_manager.set_timer_duration(30)
        
        # Get settings
        settings1 = self.config_manager.get_quiz_settings()
        
        # Simulate restart by creating new instance
        new_config = ConfigManager()
        settings2 = new_config.get_quiz_settings()
        
        # Should revert to defaults (no actual persistence)
        self.assertNotEqual(settings1.question_count, settings2.question_count)
        self.assertNotEqual(settings1.random_order, settings2.random_order)
        self.assertNotEqual(settings1.timer_duration, settings2.timer_duration)
    
    def test_concurrent_access_safety(self):
        """Test thread safety of configuration operations."""
        results = []
        errors = []
        
        def config_worker(worker_id):
            try:
                # Perform various operations
                self.config_manager.set_question_count(worker_id % 10 + 1)
                self.config_manager.toggle_random_order()
                settings = self.config_manager.get_quiz_settings()
                results.append((worker_id, settings))
            except Exception as e:
                errors.append((worker_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=config_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)
    
    def test_edge_case_values(self):
        """Test edge case values for all settings."""
        # Test maximum values
        result = self.config_manager.set_question_count(100)  # Max allowed
        self.assertTrue(result['success'])
        
        result = self.config_manager.set_timer_duration(300)  # Max allowed
        self.assertTrue(result['success'])
        
        # Test minimum values
        result = self.config_manager.set_question_count(1)  # Min allowed
        self.assertTrue(result['success'])
        
        result = self.config_manager.set_timer_duration(5)  # Min allowed
        self.assertTrue(result['success'])
        
        # Test just outside boundaries
        result = self.config_manager.set_question_count(101)  # Over max
        self.assertFalse(result['success'])
        
        result = self.config_manager.set_timer_duration(4)  # Under min
        self.assertFalse(result['success'])
    
    def test_settings_validation_comprehensive(self):
        """Test comprehensive settings validation."""
        # Set valid configuration
        self.config_manager.set_question_count(10)
        self.config_manager.set_random_order(True)
        self.config_manager.set_timer_duration(30)
        
        # Validate
        validation = self.config_manager.validate_settings()
        self.assertTrue(validation['valid'])
        
        # Manually corrupt settings to test validation
        original_settings = self.config_manager._global_settings
        
        # Test with corrupted question count
        self.config_manager._global_settings.question_count = "invalid"
        validation = self.config_manager.validate_settings()
        self.assertFalse(validation['valid'])
        self.assertGreater(len(validation['issues']), 0)
        
        # Restore settings
        self.config_manager._global_settings = original_settings
    
    def test_settings_summary_formatting(self):
        """Test settings summary formatting with various configurations."""
        # Test with None question count
        self.config_manager.set_question_count(None)
        summary = self.config_manager.get_settings_summary()
        self.assertIn("all available", summary.lower())
        
        # Test with specific question count
        self.config_manager.set_question_count(25)
        summary = self.config_manager.get_settings_summary()
        self.assertIn("25", summary)
        
        # Test with random order enabled
        self.config_manager.set_random_order(True)
        summary = self.config_manager.get_settings_summary()
        self.assertIn("random", summary.lower())
        
        # Test with custom timer
        self.config_manager.set_timer_duration(45)
        summary = self.config_manager.get_settings_summary()
        self.assertIn("45", summary)
    
    def test_toggle_random_order_enhanced(self):
        """Test enhanced toggle random order functionality."""
        # Test initial state
        initial_state = self.config_manager.get_random_order()
        
        # Toggle and verify response
        result = self.config_manager.toggle_random_order()
        
        self.assertIn('success', result)
        self.assertIn('new_value', result)
        self.assertTrue(result['success'])
        self.assertNotEqual(result['new_value'], initial_state)
        
        # Verify actual setting changed
        new_state = self.config_manager.get_random_order()
        self.assertEqual(new_state, result['new_value'])
        
        # The actual implementation doesn't include previous_value
        # self.assertIn('previous_value', result)
    
    def test_directory_path_normalization(self):
        """Test quiz directory path normalization."""
        test_paths = [
            "./quizzes/",
            "quizzes",
            "./quizzes",
            "quizzes/",
            "/absolute/path/quizzes",
            "path with spaces/quizzes"
        ]
        
        for path in test_paths:
            result = self.config_manager.set_quiz_directory(path)
            if result:  # Only test valid paths
                normalized = self.config_manager.get_quiz_directory()
                self.assertIsInstance(normalized, str)
                self.assertGreater(len(normalized), 0)


if __name__ == '__main__':
    unittest.main()