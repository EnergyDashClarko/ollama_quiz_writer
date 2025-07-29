"""
Comprehensive integration tests for Discord Quiz Bot.
Tests complete quiz session flows and component interactions.
"""
import unittest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.data_manager import DataManager
from src.config_manager import ConfigManager
from src.quiz_controller import QuizController
from src.quiz_engine import QuizEngine
from src.models import Question, QuizSettings, QuizSession
from tests.test_fixtures import TestFixtures, TestDataValidation


class TestCompleteQuizFlow(unittest.TestCase):
    """Test complete quiz flow from start to finish."""
    
    def setUp(self):
        """Set up integration test environment."""
        # Create temporary directory for quiz files
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize components
        self.data_manager = DataManager(self.temp_dir)
        self.config_manager = ConfigManager()
        self.quiz_controller = QuizController(self.data_manager, self.config_manager)
        self.quiz_engine = QuizEngine()
        
        # Create test quiz files
        self._create_test_quiz_files()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_quiz_files(self):
        """Create test quiz files for integration testing."""
        # Math quiz
        math_quiz = {
            "quiz": [
                {"question": "What is 2+2?", "answer": "4"},
                {"question": "What is 5*3?", "answer": "15"},
                {"question": "What is 10-7?", "answer": "3"},
                {"question": "What is 8/2?", "answer": "4"},
                {"question": "What is 3^2?", "answer": "9"}
            ]
        }
        
        # Science quiz with options
        science_quiz = {
            "quiz": [
                {
                    "question": "What is the chemical symbol for water?",
                    "answer": "H2O",
                    "options": ["H2O", "CO2", "O2", "NaCl"]
                },
                {
                    "question": "How many planets are in our solar system?",
                    "answer": "8",
                    "options": ["7", "8", "9", "10"]
                },
                {
                    "question": "What gas do plants absorb from the atmosphere?",
                    "answer": "Carbon dioxide",
                    "options": ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"]
                }
            ]
        }
        
        # Write quiz files
        with open(Path(self.temp_dir) / "math_quiz.json", 'w') as f:
            json.dump(math_quiz, f)
        
        with open(Path(self.temp_dir) / "science_quiz.json", 'w') as f:
            json.dump(science_quiz, f)
    
    def test_complete_quiz_session_flow(self):
        """Test complete quiz session from start to finish."""
        channel_id = 12345
        quiz_name = "math_quiz"
        
        # Step 1: Load quiz data
        loaded_quizzes = self.data_manager.load_quiz_files()
        self.assertIn(quiz_name, loaded_quizzes)
        self.assertEqual(len(loaded_quizzes[quiz_name]), 5)
        
        # Step 2: Configure settings
        self.config_manager.set_question_count(3)
        self.config_manager.set_random_order(False)
        self.config_manager.set_timer_duration(15)
        
        settings = self.config_manager.get_quiz_settings()
        self.assertEqual(settings.question_count, 3)
        self.assertFalse(settings.random_order)
        self.assertEqual(settings.timer_duration, 15)
        
        # Step 3: Start quiz session
        result = self.quiz_controller.start_quiz(channel_id, quiz_name)
        self.assertTrue(result['success'])
        self.assertIn('session_info', result)
        
        # Verify session was created
        self.assertTrue(self.quiz_controller.has_active_session(channel_id))
        session = self.quiz_controller.get_session(channel_id)
        self.assertIsNotNone(session)
        self.assertTrue(TestDataValidation.validate_quiz_session(session))
        
        # Step 4: Get questions one by one
        questions_received = []
        for i in range(3):  # Should get 3 questions based on settings
            question = self.quiz_controller.get_next_question(channel_id)
            self.assertIsNotNone(question)
            self.assertTrue(TestDataValidation.validate_question(question))
            questions_received.append(question)
        
        # Step 5: Verify quiz completion
        self.assertTrue(self.quiz_controller.is_quiz_complete(channel_id))
        
        # Step 6: Get completion info
        completion_info = self.quiz_controller.get_quiz_completion_info(channel_id)
        self.assertIsNotNone(completion_info)
        self.assertEqual(completion_info['quiz_name'], quiz_name)
        self.assertEqual(completion_info['total_questions'], 3)
        
        # Step 7: Clean up
        stop_result = self.quiz_controller.stop_quiz(channel_id)
        self.assertTrue(stop_result['success'])
        self.assertFalse(self.quiz_controller.has_active_session(channel_id))
    
    def test_quiz_session_with_pause_resume(self):
        """Test quiz session with pause and resume functionality."""
        channel_id = 12345
        quiz_name = "science_quiz"
        
        # Load data and start quiz
        self.data_manager.load_quiz_files()
        self.config_manager.set_question_count(2)
        
        start_result = self.quiz_controller.start_quiz(channel_id, quiz_name)
        self.assertTrue(start_result['success'])
        
        # Get first question
        question1 = self.quiz_controller.get_next_question(channel_id)
        self.assertIsNotNone(question1)
        
        # Pause the quiz
        pause_result = self.quiz_controller.pause_quiz(channel_id)
        self.assertTrue(pause_result['success'])
        
        # Verify paused state
        session = self.quiz_controller.get_session(channel_id)
        self.assertTrue(session.is_paused)
        
        # Try to get next question while paused (should fail)
        question_while_paused = self.quiz_controller.get_next_question(channel_id)
        self.assertIsNone(question_while_paused)
        
        # Resume the quiz
        resume_result = self.quiz_controller.resume_quiz(channel_id)
        self.assertTrue(resume_result['success'])
        
        # Verify resumed state
        session = self.quiz_controller.get_session(channel_id)
        self.assertFalse(session.is_paused)
        
        # Get second question
        question2 = self.quiz_controller.get_next_question(channel_id)
        self.assertIsNotNone(question2)
        
        # Verify questions are different
        self.assertNotEqual(question1.text, question2.text)
        
        # Complete and stop quiz
        self.assertTrue(self.quiz_controller.is_quiz_complete(channel_id))
        self.quiz_controller.stop_quiz(channel_id)
    
    def test_multiple_concurrent_quiz_sessions(self):
        """Test multiple concurrent quiz sessions in different channels."""
        channels = [11111, 22222, 33333]
        quiz_names = ["math_quiz", "science_quiz", "math_quiz"]
        
        # Load quiz data
        self.data_manager.load_quiz_files()
        self.config_manager.set_question_count(2)
        
        # Start multiple sessions
        for channel_id, quiz_name in zip(channels, quiz_names):
            result = self.quiz_controller.start_quiz(channel_id, quiz_name)
            self.assertTrue(result['success'])
        
        # Verify all sessions are active
        active_sessions = self.quiz_controller.get_all_active_sessions()
        self.assertEqual(len(active_sessions), 3)
        for channel_id in channels:
            self.assertIn(channel_id, active_sessions)
        
        # Get questions from each session
        for channel_id in channels:
            question = self.quiz_controller.get_next_question(channel_id)
            self.assertIsNotNone(question)
        
        # Pause one session
        self.quiz_controller.pause_quiz(channels[1])
        
        # Verify other sessions still work
        question = self.quiz_controller.get_next_question(channels[0])
        self.assertIsNotNone(question)
        question = self.quiz_controller.get_next_question(channels[2])
        self.assertIsNotNone(question)
        
        # Verify paused session doesn't return questions
        paused_question = self.quiz_controller.get_next_question(channels[1])
        self.assertIsNone(paused_question)
        
        # Clean up all sessions
        for channel_id in channels:
            self.quiz_controller.stop_quiz(channel_id)
        
        # Verify all sessions are stopped
        final_active = self.quiz_controller.get_all_active_sessions()
        self.assertEqual(len(final_active), 0)
    
    def test_quiz_engine_integration_with_settings(self):
        """Test quiz engine integration with different settings."""
        questions = TestFixtures.create_sample_questions()
        
        # Test with default settings
        default_settings = QuizSettings()
        selected = self.quiz_engine.select_questions(questions, default_settings)
        self.assertEqual(len(selected), len(questions))  # Should return all
        
        # Test with count limit
        limited_settings = QuizSettings(question_count=3)
        selected = self.quiz_engine.select_questions(questions, limited_settings)
        self.assertEqual(len(selected), 3)
        
        # Test with random order
        random_settings = QuizSettings(random_order=True, question_count=3)
        selected1 = self.quiz_engine.select_questions(questions, random_settings)
        selected2 = self.quiz_engine.select_questions(questions, random_settings)
        
        # Both should have 3 questions
        self.assertEqual(len(selected1), 3)
        self.assertEqual(len(selected2), 3)
        
        # Order might be different (though not guaranteed in test)
        self.assertEqual(len(selected1), len(selected2))
    
    def test_error_recovery_integration(self):
        """Test error recovery across components."""
        channel_id = 12345
        
        # Test with non-existent quiz
        result = self.quiz_controller.start_quiz(channel_id, "nonexistent_quiz")
        self.assertFalse(result['success'])
        self.assertIn('not found', result['message'])
        
        # Load valid data
        self.data_manager.load_quiz_files()
        
        # Test with valid quiz
        result = self.quiz_controller.start_quiz(channel_id, "math_quiz")
        self.assertTrue(result['success'])
        
        # Test session conflict resolution
        session = self.quiz_controller.get_session(channel_id)
        session.current_index = -1  # Introduce corruption
        
        conflicts = self.quiz_controller.handle_session_conflicts(channel_id)
        self.assertTrue(conflicts['conflicts_found'])
        self.assertTrue(conflicts['conflicts_resolved'])
        
        # Verify session is fixed
        fixed_session = self.quiz_controller.get_session(channel_id)
        self.assertEqual(fixed_session.current_index, 0)
        
        # Clean up
        self.quiz_controller.stop_quiz(channel_id)
    
    def test_configuration_integration(self):
        """Test configuration integration across components."""
        # Test configuration validation
        validation = self.config_manager.validate_settings()
        self.assertTrue(validation['valid'])
        
        # Test configuration health check
        health = self.config_manager.get_configuration_health_check()
        self.assertTrue(health['healthy'])
        
        # Test invalid configuration
        result = self.config_manager.set_question_count(-5)
        self.assertFalse(result['success'])
        
        # Test configuration reset
        self.config_manager.set_question_count(50)
        self.config_manager.set_random_order(True)
        self.config_manager.reset_to_defaults()
        
        settings = self.config_manager.get_quiz_settings()
        self.assertIsNone(settings.question_count)
        self.assertFalse(settings.random_order)
        self.assertEqual(settings.timer_duration, 10)


class TestDataFlowIntegration(unittest.TestCase):
    """Test data flow between components."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_manager = DataManager(self.temp_dir)
        self.config_manager = ConfigManager()
        self.quiz_controller = QuizController(self.data_manager, self.config_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_data_loading_error_handling_flow(self):
        """Test complete data loading error handling flow."""
        # Test with empty directory
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        # Should create sample quiz
        self.assertGreater(len(loaded_quizzes), 0)
        self.assertTrue(self.data_manager.has_load_errors())
        
        # Get loading summary
        summary = self.data_manager.get_loading_summary()
        self.assertIn('total_quizzes', summary)
        self.assertIn('available_quizzes', summary)
        self.assertTrue(summary['has_errors'])
        
        # Test quiz controller with loaded data
        available_quizzes = self.data_manager.get_available_quizzes()
        if available_quizzes:
            quiz_name = available_quizzes[0]
            result = self.quiz_controller.start_quiz(12345, quiz_name)
            self.assertTrue(result['success'])
            self.quiz_controller.stop_quiz(12345)
    
    def test_settings_propagation_flow(self):
        """Test settings propagation through the system."""
        # Create test quiz
        quiz_data = {
            "quiz": [
                {"question": f"Question {i}?", "answer": f"Answer {i}"}
                for i in range(10)
            ]
        }
        
        quiz_file = Path(self.temp_dir) / "test_quiz.json"
        with open(quiz_file, 'w') as f:
            json.dump(quiz_data, f)
        
        # Load data
        self.data_manager.load_quiz_files()
        
        # Configure settings
        self.config_manager.set_question_count(5)
        self.config_manager.set_random_order(True)
        
        # Start quiz with custom settings
        custom_settings = QuizSettings(question_count=3, random_order=False, timer_duration=20)
        result = self.quiz_controller.start_quiz(12345, "test_quiz", custom_settings)
        self.assertTrue(result['success'])
        
        # Verify custom settings were used
        session = self.quiz_controller.get_session(12345)
        self.assertEqual(session.settings.question_count, 3)
        self.assertFalse(session.settings.random_order)
        self.assertEqual(session.settings.timer_duration, 20)
        
        # Get questions and verify count
        questions_received = []
        while not self.quiz_controller.is_quiz_complete(12345):
            question = self.quiz_controller.get_next_question(12345)
            if question:
                questions_received.append(question)
        
        self.assertEqual(len(questions_received), 3)
        
        # Clean up
        self.quiz_controller.stop_quiz(12345)
    
    def test_component_interaction_edge_cases(self):
        """Test edge cases in component interactions."""
        # Test with minimal quiz
        minimal_quiz = {
            "quiz": [
                {"question": "Single question?", "answer": "Single answer"}
            ]
        }
        
        quiz_file = Path(self.temp_dir) / "minimal_quiz.json"
        with open(quiz_file, 'w') as f:
            json.dump(minimal_quiz, f)
        
        self.data_manager.load_quiz_files()
        
        # Test with question count larger than available
        self.config_manager.set_question_count(10)
        
        result = self.quiz_controller.start_quiz(12345, "minimal_quiz")
        self.assertTrue(result['success'])
        
        # Should only get 1 question despite requesting 10
        question = self.quiz_controller.get_next_question(12345)
        self.assertIsNotNone(question)
        
        # Should be complete after 1 question
        self.assertTrue(self.quiz_controller.is_quiz_complete(12345))
        
        # Clean up
        self.quiz_controller.stop_quiz(12345)


class TestAsyncIntegration(unittest.TestCase):
    """Test async integration scenarios."""
    
    def setUp(self):
        """Set up async test environment."""
        self.quiz_engine = QuizEngine()
    
    async def test_timer_integration_flow(self):
        """Test complete timer integration flow."""
        channel_id = "test_channel"
        
        # Test timer lifecycle
        update_calls = []
        completion_called = False
        
        async def update_callback(remaining):
            update_calls.append(remaining)
        
        async def completion_callback():
            nonlocal completion_called
            completion_called = True
        
        # Start timer
        timer_task = asyncio.create_task(
            self.quiz_engine.start_question_timer(
                channel_id, 2, update_callback, completion_callback
            )
        )
        
        # Check timer status during execution
        await asyncio.sleep(0.1)
        status = self.quiz_engine.get_timer_status(channel_id)
        self.assertIsNotNone(status)
        self.assertIn('remaining_time', status)
        
        # Wait for completion
        await timer_task
        
        # Verify callbacks were called
        self.assertEqual(len(update_calls), 2)
        self.assertTrue(completion_called)
        
        # Verify timer is cleaned up
        final_status = self.quiz_engine.get_timer_status(channel_id)
        self.assertIsNone(final_status)
    
    async def test_timer_pause_resume_integration(self):
        """Test timer pause/resume integration."""
        channel_id = "test_channel"
        
        update_calls = []
        
        async def update_callback(remaining):
            update_calls.append(remaining)
            # Pause after first update
            if remaining == 3:
                self.quiz_engine.pause_timer(channel_id)
                # Resume after short delay
                await asyncio.sleep(0.2)
                self.quiz_engine.resume_timer(channel_id)
        
        async def completion_callback():
            pass
        
        # Start timer
        await self.quiz_engine.start_question_timer(
            channel_id, 3, update_callback, completion_callback
        )
        
        # Should have received all updates despite pause
        self.assertEqual(len(update_calls), 3)
        self.assertEqual(update_calls, [3, 2, 1])


# Helper to run async tests
def async_test(coro):
    """Decorator to run async test methods."""
    def wrapper(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro(self))
        finally:
            loop.close()
    return wrapper


# Apply async_test decorator to async test methods
TestAsyncIntegration.test_timer_integration_flow = async_test(TestAsyncIntegration.test_timer_integration_flow)
TestAsyncIntegration.test_timer_pause_resume_integration = async_test(TestAsyncIntegration.test_timer_pause_resume_integration)


if __name__ == '__main__':
    unittest.main()