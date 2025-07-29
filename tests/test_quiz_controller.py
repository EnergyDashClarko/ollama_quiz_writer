"""
Unit tests for QuizController session state management.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List
import threading
import time

from src.quiz_controller import QuizController, SessionState
from src.models import Question, QuizSettings, QuizSession
from src.data_manager import DataManager
from src.config_manager import ConfigManager
from tests.test_fixtures import TestFixtures, TestDataValidation


class TestQuizControllerSessionState(unittest.TestCase):
    """Test cases for QuizController session state management."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_data_manager = Mock(spec=DataManager)
        self.mock_config_manager = Mock(spec=ConfigManager)
        
        # Create sample questions
        self.sample_questions = [
            Question("What is 2+2?", "4"),
            Question("What is the capital of France?", "Paris"),
            Question("What is Python?", "Programming language")
        ]
        
        # Create sample settings
        self.sample_settings = QuizSettings(
            question_count=2,
            random_order=False,
            timer_duration=10
        )
        
        # Set up mock returns
        self.mock_data_manager.get_quiz_questions.return_value = self.sample_questions
        self.mock_config_manager.get_quiz_settings.return_value = self.sample_settings
        
        # Create controller instance
        self.controller = QuizController(self.mock_data_manager, self.mock_config_manager)
    
    def test_create_session_success(self):
        """Test successful session creation."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        result = self.controller.create_session(channel_id, quiz_name)
        
        self.assertTrue(result)
        self.assertTrue(self.controller.has_active_session(channel_id))
        self.mock_data_manager.get_quiz_questions.assert_called_once_with(quiz_name)
    
    def test_create_session_with_custom_settings(self):
        """Test session creation with custom settings."""
        channel_id = 12345
        quiz_name = "test_quiz"
        custom_settings = QuizSettings(question_count=1, random_order=True, timer_duration=15)
        
        result = self.controller.create_session(channel_id, quiz_name, custom_settings)
        
        self.assertTrue(result)
        session = self.controller.get_session(channel_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.settings.question_count, 1)
        self.assertTrue(session.settings.random_order)
        self.assertEqual(session.settings.timer_duration, 15)
    
    def test_create_session_duplicate_channel(self):
        """Test that creating a session for an existing channel fails."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create first session
        result1 = self.controller.create_session(channel_id, quiz_name)
        self.assertTrue(result1)
        
        # Attempt to create second session for same channel
        result2 = self.controller.create_session(channel_id, quiz_name)
        self.assertFalse(result2)
    
    def test_create_session_no_questions(self):
        """Test session creation fails when no questions are available."""
        channel_id = 12345
        quiz_name = "empty_quiz"
        
        # Mock empty questions list
        self.mock_data_manager.get_quiz_questions.return_value = []
        
        result = self.controller.create_session(channel_id, quiz_name)
        
        self.assertFalse(result)
        self.assertFalse(self.controller.has_active_session(channel_id))
    
    def test_create_session_invalid_quiz(self):
        """Test session creation fails for invalid quiz name."""
        channel_id = 12345
        quiz_name = "nonexistent_quiz"
        
        # Mock exception from data manager
        self.mock_data_manager.get_quiz_questions.side_effect = ValueError("Quiz not found")
        
        result = self.controller.create_session(channel_id, quiz_name)
        
        self.assertFalse(result)
        self.assertFalse(self.controller.has_active_session(channel_id))
    
    def test_get_session(self):
        """Test retrieving an active session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session
        self.controller.create_session(channel_id, quiz_name)
        
        # Retrieve session
        session = self.controller.get_session(channel_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session.channel_id, channel_id)
        self.assertEqual(session.quiz_name, quiz_name)
        self.assertTrue(session.is_active)
        self.assertFalse(session.is_paused)
    
    def test_get_session_nonexistent(self):
        """Test retrieving a session that doesn't exist."""
        channel_id = 99999
        
        session = self.controller.get_session(channel_id)
        
        self.assertIsNone(session)
    
    def test_has_active_session(self):
        """Test checking for active sessions."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Initially no session
        self.assertFalse(self.controller.has_active_session(channel_id))
        
        # Create session
        self.controller.create_session(channel_id, quiz_name)
        self.assertTrue(self.controller.has_active_session(channel_id))
        
        # Stop session
        self.controller.stop_session(channel_id)
        self.assertFalse(self.controller.has_active_session(channel_id))
    
    def test_get_session_state(self):
        """Test getting session state."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Initially inactive
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.INACTIVE)
        
        # Create session - should be active
        self.controller.create_session(channel_id, quiz_name)
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.ACTIVE)
        
        # Pause session
        self.controller.pause_session(channel_id)
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.PAUSED)
        
        # Resume session
        self.controller.resume_session(channel_id)
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.ACTIVE)
        
        # Stop session
        self.controller.stop_session(channel_id)
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.INACTIVE)
    
    def test_pause_session_success(self):
        """Test successfully pausing an active session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create and pause session
        self.controller.create_session(channel_id, quiz_name)
        result = self.controller.pause_session(channel_id)
        
        self.assertTrue(result)
        session = self.controller.get_session(channel_id)
        self.assertTrue(session.is_paused)
        self.assertTrue(session.is_active)
    
    def test_pause_session_no_active_session(self):
        """Test pausing when no active session exists."""
        channel_id = 12345
        
        result = self.controller.pause_session(channel_id)
        
        self.assertFalse(result)
    
    def test_pause_session_already_paused(self):
        """Test pausing an already paused session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create, pause, then pause again
        self.controller.create_session(channel_id, quiz_name)
        self.controller.pause_session(channel_id)
        result = self.controller.pause_session(channel_id)
        
        self.assertTrue(result)  # Should still return True
        session = self.controller.get_session(channel_id)
        self.assertTrue(session.is_paused)
    
    def test_resume_session_success(self):
        """Test successfully resuming a paused session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create, pause, then resume session
        self.controller.create_session(channel_id, quiz_name)
        self.controller.pause_session(channel_id)
        result = self.controller.resume_session(channel_id)
        
        self.assertTrue(result)
        session = self.controller.get_session(channel_id)
        self.assertFalse(session.is_paused)
        self.assertTrue(session.is_active)
    
    def test_resume_session_no_active_session(self):
        """Test resuming when no active session exists."""
        channel_id = 12345
        
        result = self.controller.resume_session(channel_id)
        
        self.assertFalse(result)
    
    def test_resume_session_not_paused(self):
        """Test resuming a session that isn't paused."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session (not paused) and try to resume
        self.controller.create_session(channel_id, quiz_name)
        result = self.controller.resume_session(channel_id)
        
        self.assertTrue(result)  # Should still return True
        session = self.controller.get_session(channel_id)
        self.assertFalse(session.is_paused)
    
    def test_stop_session_success(self):
        """Test successfully stopping an active session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create and stop session
        self.controller.create_session(channel_id, quiz_name)
        result = self.controller.stop_session(channel_id)
        
        self.assertTrue(result)
        self.assertFalse(self.controller.has_active_session(channel_id))
        self.assertIsNone(self.controller.get_session(channel_id))
    
    def test_stop_session_no_session(self):
        """Test stopping when no session exists."""
        channel_id = 12345
        
        result = self.controller.stop_session(channel_id)
        
        self.assertFalse(result)
    
    def test_validate_session_state_valid(self):
        """Test session state validation for valid session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session
        self.controller.create_session(channel_id, quiz_name)
        
        validation = self.controller.validate_session_state(channel_id)
        
        self.assertTrue(validation['valid'])
        self.assertEqual(validation['state'], SessionState.ACTIVE.value)
        self.assertEqual(len(validation['issues']), 0)
        self.assertIsNotNone(validation['session_info'])
    
    def test_validate_session_state_inactive(self):
        """Test session state validation for inactive channel."""
        channel_id = 12345
        
        validation = self.controller.validate_session_state(channel_id)
        
        self.assertTrue(validation['valid'])
        self.assertEqual(validation['state'], SessionState.INACTIVE.value)
        self.assertEqual(len(validation['issues']), 0)
    
    def test_cleanup_inactive_sessions(self):
        """Test cleanup of inactive sessions."""
        channel_id1 = 12345
        channel_id2 = 67890
        quiz_name = "test_quiz"
        
        # Create two sessions
        self.controller.create_session(channel_id1, quiz_name)
        self.controller.create_session(channel_id2, quiz_name)
        
        # Stop one session by marking it inactive
        session1 = self.controller.get_session(channel_id1)
        session1.is_active = False
        
        # Run cleanup
        cleaned_count = self.controller.cleanup_inactive_sessions()
        
        self.assertEqual(cleaned_count, 1)
        self.assertIsNone(self.controller.get_session(channel_id1))
        self.assertIsNotNone(self.controller.get_session(channel_id2))
    
    def test_get_all_active_sessions(self):
        """Test getting all active sessions."""
        channel_id1 = 12345
        channel_id2 = 67890
        quiz_name = "test_quiz"
        
        # Initially no sessions
        active_sessions = self.controller.get_all_active_sessions()
        self.assertEqual(len(active_sessions), 0)
        
        # Create two sessions
        self.controller.create_session(channel_id1, quiz_name)
        self.controller.create_session(channel_id2, quiz_name)
        
        active_sessions = self.controller.get_all_active_sessions()
        self.assertEqual(len(active_sessions), 2)
        self.assertIn(channel_id1, active_sessions)
        self.assertIn(channel_id2, active_sessions)
        
        # Stop one session
        self.controller.stop_session(channel_id1)
        
        active_sessions = self.controller.get_all_active_sessions()
        self.assertEqual(len(active_sessions), 1)
        self.assertNotIn(channel_id1, active_sessions)
        self.assertIn(channel_id2, active_sessions)


class TestQuizControllerSessionControl(unittest.TestCase):
    """Test cases for QuizController session control operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_data_manager = Mock(spec=DataManager)
        self.mock_config_manager = Mock(spec=ConfigManager)
        
        # Create sample questions
        self.sample_questions = [
            Question("What is 2+2?", "4"),
            Question("What is the capital of France?", "Paris"),
            Question("What is Python?", "Programming language")
        ]
        
        # Create sample settings
        self.sample_settings = QuizSettings(
            question_count=2,
            random_order=False,
            timer_duration=10
        )
        
        # Set up mock returns
        self.mock_data_manager.get_quiz_questions.return_value = self.sample_questions
        self.mock_data_manager.get_available_quizzes.return_value = ["test_quiz", "another_quiz"]
        self.mock_config_manager.get_quiz_settings.return_value = self.sample_settings
        
        # Create controller instance
        self.controller = QuizController(self.mock_data_manager, self.mock_config_manager)
    
    def test_start_quiz_success(self):
        """Test successfully starting a quiz."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        result = self.controller.start_quiz(channel_id, quiz_name)
        
        self.assertTrue(result['success'])
        self.assertIn("Started quiz", result['message'])
        self.assertIsNotNone(result['session_info'])
        self.assertTrue(self.controller.has_active_session(channel_id))
    
    def test_start_quiz_with_custom_settings(self):
        """Test starting a quiz with custom settings."""
        channel_id = 12345
        quiz_name = "test_quiz"
        custom_settings = QuizSettings(question_count=1, random_order=True, timer_duration=15)
        
        result = self.controller.start_quiz(channel_id, quiz_name, custom_settings)
        
        self.assertTrue(result['success'])
        session = self.controller.get_session(channel_id)
        self.assertEqual(session.settings.question_count, 1)
        self.assertTrue(session.settings.random_order)
    
    def test_start_quiz_already_active(self):
        """Test starting a quiz when one is already active."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Start first quiz
        self.controller.start_quiz(channel_id, quiz_name)
        
        # Try to start second quiz
        result = self.controller.start_quiz(channel_id, quiz_name)
        
        self.assertFalse(result['success'])
        self.assertIn("already running", result['message'])
    
    def test_start_quiz_invalid_name(self):
        """Test starting a quiz with invalid name."""
        channel_id = 12345
        quiz_name = "nonexistent_quiz"
        
        result = self.controller.start_quiz(channel_id, quiz_name)
        
        self.assertFalse(result['success'])
        self.assertIn("not found", result['message'])
        self.assertIn("Available quizzes", result['message'])
    
    def test_start_quiz_creation_failure(self):
        """Test starting a quiz when session creation fails."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Mock creation failure
        self.mock_data_manager.get_quiz_questions.return_value = []
        
        result = self.controller.start_quiz(channel_id, quiz_name)
        
        self.assertFalse(result['success'])
        self.assertIn("Failed to start", result['message'])
    
    def test_stop_quiz_success(self):
        """Test successfully stopping a quiz."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Start then stop quiz
        self.controller.start_quiz(channel_id, quiz_name)
        result = self.controller.stop_quiz(channel_id)
        
        self.assertTrue(result['success'])
        self.assertIn("stopped successfully", result['message'])
        self.assertIsNotNone(result['session_info'])
        self.assertFalse(self.controller.has_active_session(channel_id))
    
    def test_stop_quiz_no_active_session(self):
        """Test stopping a quiz when no session is active."""
        channel_id = 12345
        
        result = self.controller.stop_quiz(channel_id)
        
        self.assertFalse(result['success'])
        self.assertIn("No active quiz", result['message'])
    
    def test_pause_quiz_success(self):
        """Test successfully pausing a quiz."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Start then pause quiz
        self.controller.start_quiz(channel_id, quiz_name)
        result = self.controller.pause_quiz(channel_id)
        
        self.assertTrue(result['success'])
        self.assertIn("paused", result['message'])
        self.assertIsNotNone(result['session_info'])
        
        session = self.controller.get_session(channel_id)
        self.assertTrue(session.is_paused)
    
    def test_pause_quiz_no_active_session(self):
        """Test pausing a quiz when no session is active."""
        channel_id = 12345
        
        result = self.controller.pause_quiz(channel_id)
        
        self.assertFalse(result['success'])
        self.assertIn("No active quiz", result['message'])
    
    def test_pause_quiz_already_paused(self):
        """Test pausing a quiz that is already paused."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Start, pause, then pause again
        self.controller.start_quiz(channel_id, quiz_name)
        self.controller.pause_quiz(channel_id)
        result = self.controller.pause_quiz(channel_id)
        
        self.assertTrue(result['success'])
        self.assertIn("already paused", result['message'])
    
    def test_resume_quiz_success(self):
        """Test successfully resuming a paused quiz."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Start, pause, then resume quiz
        self.controller.start_quiz(channel_id, quiz_name)
        self.controller.pause_quiz(channel_id)
        result = self.controller.resume_quiz(channel_id)
        
        self.assertTrue(result['success'])
        self.assertIn("resumed", result['message'])
        self.assertIsNotNone(result['session_info'])
        
        session = self.controller.get_session(channel_id)
        self.assertFalse(session.is_paused)
    
    def test_resume_quiz_no_active_session(self):
        """Test resuming a quiz when no session is active."""
        channel_id = 12345
        
        result = self.controller.resume_quiz(channel_id)
        
        self.assertFalse(result['success'])
        self.assertIn("No active quiz", result['message'])
    
    def test_resume_quiz_not_paused(self):
        """Test resuming a quiz that is not paused."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Start quiz (not paused) and try to resume
        self.controller.start_quiz(channel_id, quiz_name)
        result = self.controller.resume_quiz(channel_id)
        
        self.assertTrue(result['success'])
        self.assertIn("not paused", result['message'])
    
    def test_handle_session_conflicts_no_conflicts(self):
        """Test conflict handling when no conflicts exist."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create valid session
        self.controller.start_quiz(channel_id, quiz_name)
        
        result = self.controller.handle_session_conflicts(channel_id)
        
        self.assertFalse(result['conflicts_found'])
        self.assertFalse(result['conflicts_resolved'])
        self.assertEqual(len(result['issues']), 0)
        self.assertEqual(len(result['actions_taken']), 0)
    
    def test_handle_session_conflicts_with_resolution(self):
        """Test conflict handling with successful resolution."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session and introduce conflict
        self.controller.start_quiz(channel_id, quiz_name)
        session = self.controller.get_session(channel_id)
        session.current_index = -1  # Invalid index
        
        result = self.controller.handle_session_conflicts(channel_id)
        
        self.assertTrue(result['conflicts_found'])
        self.assertTrue(result['conflicts_resolved'])
        self.assertGreater(len(result['actions_taken']), 0)
        
        # Verify fix was applied
        updated_session = self.controller.get_session(channel_id)
        self.assertEqual(updated_session.current_index, 0)
    
    def test_get_session_status_summary_active(self):
        """Test getting status summary for active session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        self.controller.start_quiz(channel_id, quiz_name)
        
        summary = self.controller.get_session_status_summary(channel_id)
        
        self.assertIn("test_quiz", summary)
        self.assertIn("Status: Active", summary)
        self.assertIn("Progress:", summary)
        self.assertIn("Timer:", summary)
    
    def test_get_session_status_summary_paused(self):
        """Test getting status summary for paused session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        self.controller.start_quiz(channel_id, quiz_name)
        self.controller.pause_quiz(channel_id)
        
        summary = self.controller.get_session_status_summary(channel_id)
        
        self.assertIn("Status: Paused", summary)
    
    def test_get_session_status_summary_no_session(self):
        """Test getting status summary when no session exists."""
        channel_id = 12345
        
        summary = self.controller.get_session_status_summary(channel_id)
        
        self.assertEqual(summary, "No active quiz session in this channel.")
    
    def test_session_lifecycle_integration(self):
        """Test complete session lifecycle: start -> pause -> resume -> stop."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Start quiz
        start_result = self.controller.start_quiz(channel_id, quiz_name)
        self.assertTrue(start_result['success'])
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.ACTIVE)
        
        # Pause quiz
        pause_result = self.controller.pause_quiz(channel_id)
        self.assertTrue(pause_result['success'])
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.PAUSED)
        
        # Resume quiz
        resume_result = self.controller.resume_quiz(channel_id)
        self.assertTrue(resume_result['success'])
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.ACTIVE)
        
        # Stop quiz
        stop_result = self.controller.stop_quiz(channel_id)
        self.assertTrue(stop_result['success'])
        self.assertEqual(self.controller.get_session_state(channel_id), SessionState.INACTIVE)
    
    def test_multiple_channel_session_isolation(self):
        """Test that sessions in different channels are properly isolated."""
        channel_id1 = 12345
        channel_id2 = 67890
        quiz_name = "test_quiz"
        
        # Start quiz in first channel
        result1 = self.controller.start_quiz(channel_id1, quiz_name)
        self.assertTrue(result1['success'])
        
        # Start quiz in second channel
        result2 = self.controller.start_quiz(channel_id2, quiz_name)
        self.assertTrue(result2['success'])
        
        # Pause first channel
        self.controller.pause_quiz(channel_id1)
        
        # Verify isolation
        self.assertEqual(self.controller.get_session_state(channel_id1), SessionState.PAUSED)
        self.assertEqual(self.controller.get_session_state(channel_id2), SessionState.ACTIVE)
        
        # Stop second channel
        self.controller.stop_quiz(channel_id2)
        
        # Verify first channel still paused
        self.assertEqual(self.controller.get_session_state(channel_id1), SessionState.PAUSED)
        self.assertEqual(self.controller.get_session_state(channel_id2), SessionState.INACTIVE)
    
    def test_get_next_question_success(self):
        """Test getting next question from active session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        self.controller.start_quiz(channel_id, quiz_name)
        
        # Get first question
        question1 = self.controller.get_next_question(channel_id)
        self.assertIsNotNone(question1)
        self.assertEqual(question1.text, "What is 2+2?")
        
        # Get second question
        question2 = self.controller.get_next_question(channel_id)
        self.assertIsNotNone(question2)
        self.assertEqual(question2.text, "What is the capital of France?")
    
    def test_get_next_question_no_session(self):
        """Test getting next question when no session exists."""
        channel_id = 12345
        
        question = self.controller.get_next_question(channel_id)
        self.assertIsNone(question)
    
    def test_get_next_question_paused_session(self):
        """Test getting next question from paused session."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        self.controller.start_quiz(channel_id, quiz_name)
        self.controller.pause_quiz(channel_id)
        
        question = self.controller.get_next_question(channel_id)
        self.assertIsNone(question)
    
    def test_get_next_question_quiz_complete(self):
        """Test getting next question when quiz is complete."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        self.controller.start_quiz(channel_id, quiz_name)
        
        # Exhaust all questions (2 questions based on settings)
        self.controller.get_next_question(channel_id)
        self.controller.get_next_question(channel_id)
        
        # Try to get another question
        question = self.controller.get_next_question(channel_id)
        self.assertIsNone(question)
    
    def test_is_quiz_complete(self):
        """Test checking if quiz is complete."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # No session - considered complete
        self.assertTrue(self.controller.is_quiz_complete(channel_id))
        
        # Start quiz - not complete
        self.controller.start_quiz(channel_id, quiz_name)
        self.assertFalse(self.controller.is_quiz_complete(channel_id))
        
        # Get all questions - should be complete
        self.controller.get_next_question(channel_id)
        self.controller.get_next_question(channel_id)
        self.assertTrue(self.controller.is_quiz_complete(channel_id))
    
    def test_get_quiz_completion_info(self):
        """Test getting completion info for finished quiz."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # No session - no completion info
        completion_info = self.controller.get_quiz_completion_info(channel_id)
        self.assertIsNone(completion_info)
        
        # Start quiz but don't complete - no completion info
        self.controller.start_quiz(channel_id, quiz_name)
        completion_info = self.controller.get_quiz_completion_info(channel_id)
        self.assertIsNone(completion_info)
        
        # Complete quiz - should have completion info
        self.controller.get_next_question(channel_id)
        self.controller.get_next_question(channel_id)
        
        completion_info = self.controller.get_quiz_completion_info(channel_id)
        self.assertIsNotNone(completion_info)
        self.assertEqual(completion_info['quiz_name'], quiz_name)
        self.assertEqual(completion_info['total_questions'], 2)
        self.assertIn('duration', completion_info)
        self.assertIn('settings', completion_info)


class TestQuizControllerComprehensive(unittest.TestCase):
    """Comprehensive tests for QuizController functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.mock_config_manager = Mock(spec=ConfigManager)
        
        self.sample_questions = TestFixtures.create_sample_questions()
        self.sample_settings = TestFixtures.create_sample_quiz_settings()
        
        self.mock_data_manager.get_quiz_questions.return_value = self.sample_questions
        self.mock_config_manager.get_quiz_settings.return_value = self.sample_settings
        
        self.controller = QuizController(self.mock_data_manager, self.mock_config_manager)
    
    def test_session_timeout_handling(self):
        """Test handling of session timeouts."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session
        self.controller.create_session(channel_id, quiz_name)
        session = self.controller.get_session(channel_id)
        
        # Simulate old session by modifying start time
        session.start_time = datetime.now() - timedelta(hours=2)
        
        # Check if session is considered expired
        validation = self.controller.validate_session_state(channel_id)
        
        # Should detect timeout issues
        self.assertIn('session_info', validation)
    
    def test_concurrent_session_operations(self):
        """Test thread safety of session operations."""
        channel_ids = [12345, 12346, 12347, 12348, 12349]
        quiz_name = "test_quiz"
        
        results = []
        errors = []
        
        def session_worker(channel_id):
            try:
                # Create session
                create_result = self.controller.create_session(channel_id, quiz_name)
                
                # Perform operations
                pause_result = self.controller.pause_session(channel_id)
                resume_result = self.controller.resume_session(channel_id)
                stop_result = self.controller.stop_session(channel_id)
                
                results.append({
                    'channel_id': channel_id,
                    'create': create_result,
                    'pause': pause_result,
                    'resume': resume_result,
                    'stop': stop_result
                })
            except Exception as e:
                errors.append((channel_id, e))
        
        # Start multiple threads
        threads = []
        for channel_id in channel_ids:
            thread = threading.Thread(target=session_worker, args=(channel_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no errors and all operations completed
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), len(channel_ids))
        
        # Verify all sessions were properly cleaned up
        for channel_id in channel_ids:
            self.assertFalse(self.controller.has_active_session(channel_id))
    
    def test_session_data_integrity(self):
        """Test session data integrity during operations."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session
        self.controller.create_session(channel_id, quiz_name)
        original_session = self.controller.get_session(channel_id)
        
        # Verify initial integrity
        self.assertTrue(TestDataValidation.validate_quiz_session(original_session))
        
        # Perform operations and verify integrity is maintained
        operations = [
            lambda: self.controller.pause_session(channel_id),
            lambda: self.controller.resume_session(channel_id),
            lambda: self.controller.get_next_question(channel_id),
            lambda: self.controller.get_next_question(channel_id),
        ]
        
        for operation in operations:
            operation()
            session = self.controller.get_session(channel_id)
            if session:  # Session might be None after completion
                self.assertTrue(TestDataValidation.validate_quiz_session(session))
    
    def test_memory_cleanup_after_sessions(self):
        """Test memory cleanup after session completion."""
        import gc
        import sys
        
        # Create and complete multiple sessions
        for i in range(100):
            channel_id = 10000 + i
            quiz_name = "test_quiz"
            
            # Create session
            self.controller.create_session(channel_id, quiz_name)
            
            # Complete quiz
            while not self.controller.is_quiz_complete(channel_id):
                self.controller.get_next_question(channel_id)
            
            # Stop session
            self.controller.stop_session(channel_id)
        
        # Force garbage collection
        gc.collect()
        
        # Verify no active sessions remain
        active_sessions = self.controller.get_all_active_sessions()
        self.assertEqual(len(active_sessions), 0)
    
    def test_session_state_transitions(self):
        """Test all possible session state transitions."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Test state transition matrix
        transitions = [
            (SessionState.INACTIVE, lambda: self.controller.create_session(channel_id, quiz_name), SessionState.ACTIVE),
            (SessionState.ACTIVE, lambda: self.controller.pause_session(channel_id), SessionState.PAUSED),
            (SessionState.PAUSED, lambda: self.controller.resume_session(channel_id), SessionState.ACTIVE),
            (SessionState.ACTIVE, lambda: self.controller.stop_session(channel_id), SessionState.INACTIVE),
        ]
        
        for initial_state, operation, expected_state in transitions:
            # Verify initial state
            current_state = self.controller.get_session_state(channel_id)
            if current_state != initial_state:
                # Set up the required initial state
                if initial_state == SessionState.ACTIVE and current_state == SessionState.INACTIVE:
                    self.controller.create_session(channel_id, quiz_name)
                elif initial_state == SessionState.PAUSED and current_state == SessionState.ACTIVE:
                    self.controller.pause_session(channel_id)
                elif initial_state == SessionState.INACTIVE and current_state != SessionState.INACTIVE:
                    self.controller.stop_session(channel_id)
            
            # Perform operation
            operation()
            
            # Verify expected state
            final_state = self.controller.get_session_state(channel_id)
            self.assertEqual(final_state, expected_state)
    
    def test_error_recovery_mechanisms(self):
        """Test error recovery mechanisms."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session
        self.controller.create_session(channel_id, quiz_name)
        session = self.controller.get_session(channel_id)
        
        # Introduce data corruption
        session.current_index = -1  # Invalid index
        session.questions = []  # Empty questions
        
        # Test conflict resolution
        conflicts = self.controller.handle_session_conflicts(channel_id)
        
        self.assertTrue(conflicts['conflicts_found'])
        self.assertGreater(len(conflicts['actions_taken']), 0)
    
    def test_session_statistics_tracking(self):
        """Test session statistics and tracking."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create and run session
        start_time = datetime.now()
        self.controller.create_session(channel_id, quiz_name)
        
        # Get some questions
        question_count = 0
        while not self.controller.is_quiz_complete(channel_id) and question_count < 2:
            self.controller.get_next_question(channel_id)
            question_count += 1
        
        # Get completion info
        completion_info = self.controller.get_quiz_completion_info(channel_id)
        
        if completion_info:  # If quiz completed
            self.assertIn('quiz_name', completion_info)
            self.assertIn('total_questions', completion_info)
            self.assertIn('duration', completion_info)
            self.assertIn('settings', completion_info)
            
            # Verify duration is reasonable
            duration = completion_info['duration']
            self.assertGreater(duration, 0)
            self.assertLess(duration, 60)  # Should complete within 60 seconds
    
    def test_bulk_session_operations(self):
        """Test bulk operations on multiple sessions."""
        # Create multiple sessions
        channel_ids = list(range(20000, 20010))
        quiz_name = "test_quiz"
        
        for channel_id in channel_ids:
            result = self.controller.create_session(channel_id, quiz_name)
            self.assertTrue(result)
        
        # Verify all sessions are active
        active_sessions = self.controller.get_all_active_sessions()
        self.assertEqual(len(active_sessions), len(channel_ids))
        
        # Pause all sessions
        for channel_id in channel_ids:
            self.controller.pause_session(channel_id)
        
        # Verify all are paused
        for channel_id in channel_ids:
            self.assertEqual(self.controller.get_session_state(channel_id), SessionState.PAUSED)
        
        # Cleanup all sessions
        cleaned = self.controller.cleanup_inactive_sessions()
        
        # Stop remaining sessions
        for channel_id in channel_ids:
            self.controller.stop_session(channel_id)
        
        # Verify cleanup
        final_active = self.controller.get_all_active_sessions()
        self.assertEqual(len(final_active), 0)
    
    def test_session_persistence_simulation(self):
        """Test session persistence behavior simulation."""
        channel_id = 12345
        quiz_name = "test_quiz"
        
        # Create session and get some questions
        self.controller.create_session(channel_id, quiz_name)
        original_session = self.controller.get_session(channel_id)
        
        # Get first question
        first_question = self.controller.get_next_question(channel_id)
        self.assertIsNotNone(first_question)
        
        # Simulate restart by creating new controller
        new_controller = QuizController(self.mock_data_manager, self.mock_config_manager)
        
        # Session should not exist in new controller (no persistence)
        self.assertFalse(new_controller.has_active_session(channel_id))
        self.assertIsNone(new_controller.get_session(channel_id))


if __name__ == '__main__':
    unittest.main()