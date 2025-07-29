"""
Unit tests for the QuizEngine class.
"""
import unittest
import asyncio
import random
import time
from unittest.mock import AsyncMock, MagicMock, patch
from src.quiz_engine import QuizEngine, QuizTimer
from src.models import Question, QuizSettings
from tests.test_fixtures import TestFixtures, AsyncTestHelpers


class TestQuizEngine(unittest.TestCase):
    """Test cases for QuizEngine question selection and ordering."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = QuizEngine()
        self.sample_questions = [
            Question("What is 2+2?", "4"),
            Question("What is the capital of France?", "Paris"),
            Question("What color is the sky?", "Blue"),
            Question("What is 5*5?", "25"),
            Question("What is the largest planet?", "Jupiter")
        ]
    
    def test_select_questions_default_settings(self):
        """Test question selection with default settings."""
        settings = QuizSettings()
        result = self.engine.select_questions(self.sample_questions, settings)
        
        # Should return all questions in original order
        self.assertEqual(len(result), 5)
        self.assertEqual(result, self.sample_questions)
    
    def test_select_questions_with_count_limit(self):
        """Test question selection with count limitation."""
        settings = QuizSettings(question_count=3)
        result = self.engine.select_questions(self.sample_questions, settings)
        
        # Should return first 3 questions
        self.assertEqual(len(result), 3)
        self.assertEqual(result, self.sample_questions[:3])
    
    def test_select_questions_with_random_order(self):
        """Test question selection with random ordering."""
        settings = QuizSettings(random_order=True)
        
        # Set seed for reproducible test
        random.seed(42)
        result = self.engine.select_questions(self.sample_questions, settings)
        
        # Should return all questions but potentially in different order
        self.assertEqual(len(result), 5)
        self.assertEqual(set(q.text for q in result), set(q.text for q in self.sample_questions))
    
    def test_select_questions_random_with_count(self):
        """Test question selection with both random order and count limit."""
        settings = QuizSettings(random_order=True, question_count=2)
        
        random.seed(42)
        result = self.engine.select_questions(self.sample_questions, settings)
        
        # Should return 2 questions
        self.assertEqual(len(result), 2)
        # All returned questions should be from original set
        for question in result:
            self.assertIn(question, self.sample_questions)
    
    def test_select_questions_empty_list(self):
        """Test question selection with empty question list."""
        settings = QuizSettings()
        
        with self.assertRaises(ValueError) as context:
            self.engine.select_questions([], settings)
        
        self.assertEqual(str(context.exception), "Cannot select questions from empty list")
    
    def test_select_questions_count_exceeds_available(self):
        """Test question selection when requested count exceeds available questions."""
        settings = QuizSettings(question_count=10)  # More than 5 available
        result = self.engine.select_questions(self.sample_questions, settings)
        
        # Should return all available questions
        self.assertEqual(len(result), 5)
        self.assertEqual(result, self.sample_questions)
    
    def test_shuffle_questions(self):
        """Test question shuffling functionality."""
        # Test multiple times to ensure randomness works
        results = []
        for _ in range(10):
            shuffled = self.engine.shuffle_questions(self.sample_questions)
            results.append([q.text for q in shuffled])
        
        # Should contain all original questions
        for result in results:
            self.assertEqual(set(result), set(q.text for q in self.sample_questions))
        
        # At least one result should be different from original order
        original_order = [q.text for q in self.sample_questions]
        self.assertTrue(any(result != original_order for result in results))
    
    def test_shuffle_questions_preserves_original(self):
        """Test that shuffling doesn't modify the original list."""
        original_copy = self.sample_questions.copy()
        self.engine.shuffle_questions(self.sample_questions)
        
        # Original list should be unchanged
        self.assertEqual(self.sample_questions, original_copy)
    
    def test_limit_question_count_normal(self):
        """Test normal question count limiting."""
        result = self.engine.limit_question_count(self.sample_questions, 3)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result, self.sample_questions[:3])
    
    def test_limit_question_count_zero(self):
        """Test question count limiting with zero count."""
        result = self.engine.limit_question_count(self.sample_questions, 0)
        
        self.assertEqual(len(result), 0)
        self.assertEqual(result, [])
    
    def test_limit_question_count_negative(self):
        """Test question count limiting with negative count."""
        result = self.engine.limit_question_count(self.sample_questions, -1)
        
        self.assertEqual(len(result), 0)
        self.assertEqual(result, [])
    
    def test_limit_question_count_exceeds_available(self):
        """Test question count limiting when count exceeds available questions."""
        result = self.engine.limit_question_count(self.sample_questions, 10)
        
        # Should return all available questions
        self.assertEqual(len(result), 5)
        self.assertEqual(result, self.sample_questions)
    
    def test_limit_question_count_preserves_original(self):
        """Test that limiting doesn't modify the original list."""
        original_copy = self.sample_questions.copy()
        self.engine.limit_question_count(self.sample_questions, 3)
        
        # Original list should be unchanged
        self.assertEqual(self.sample_questions, original_copy)


class TestQuizTimer(unittest.TestCase):
    """Test cases for QuizTimer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.timer = QuizTimer()
    
    async def test_timer_countdown_completion(self):
        """Test timer countdown completes successfully."""
        update_calls = []
        completion_called = False
        
        async def update_callback(remaining):
            update_calls.append(remaining)
        
        async def completion_callback():
            nonlocal completion_called
            completion_called = True
        
        # Start a 2-second timer
        await self.timer.start_countdown(2, update_callback, completion_callback)
        
        # Should have been called with 2, then 1
        self.assertEqual(update_calls, [2, 1])
        self.assertTrue(completion_called)
    
    def test_timer_pause_resume(self):
        """Test timer pause and resume functionality."""
        self.assertFalse(self.timer.is_paused)
        
        self.timer.pause()
        self.assertTrue(self.timer.is_paused)
        
        self.timer.resume()
        self.assertFalse(self.timer.is_paused)
    
    def test_timer_cancel(self):
        """Test timer cancellation."""
        self.assertFalse(self.timer.is_cancelled)
        
        self.timer.cancel()
        self.assertTrue(self.timer.is_cancelled)
    
    def test_timer_remaining_time(self):
        """Test timer remaining time property."""
        # Initially should be 0
        self.assertEqual(self.timer.remaining_time, 0)


class TestQuizEngineTimer(unittest.TestCase):
    """Test cases for QuizEngine timer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = QuizEngine()
        self.channel_id = "test_channel_123"
    
    def test_timer_status_no_active_timer(self):
        """Test getting timer status when no timer is active."""
        status = self.engine.get_timer_status(self.channel_id)
        self.assertIsNone(status)
    
    def test_pause_timer_no_active_timer(self):
        """Test pausing timer when no timer is active."""
        result = self.engine.pause_timer(self.channel_id)
        self.assertFalse(result)
    
    def test_resume_timer_no_active_timer(self):
        """Test resuming timer when no timer is active."""
        result = self.engine.resume_timer(self.channel_id)
        self.assertFalse(result)
    
    def test_cancel_timer_no_active_timer(self):
        """Test cancelling timer when no timer is active."""
        result = self.engine.cancel_timer(self.channel_id)
        self.assertFalse(result)
    
    async def test_start_question_timer(self):
        """Test starting a question timer."""
        update_calls = []
        completion_called = False
        
        async def update_callback(remaining):
            update_calls.append(remaining)
        
        async def completion_callback():
            nonlocal completion_called
            completion_called = True
        
        # Start timer in background
        timer_task = asyncio.create_task(
            self.engine.start_question_timer(
                self.channel_id, 2, update_callback, completion_callback
            )
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Check timer status
        status = self.engine.get_timer_status(self.channel_id)
        self.assertIsNotNone(status)
        self.assertIn('remaining_time', status)
        self.assertIn('is_paused', status)
        self.assertIn('is_cancelled', status)
        
        # Wait for completion
        await timer_task
        
        # Verify callbacks were called
        self.assertEqual(len(update_calls), 2)
        self.assertTrue(completion_called)
    
    async def test_timer_pause_resume_integration(self):
        """Test timer pause and resume integration."""
        update_calls = []
        
        async def update_callback(remaining):
            update_calls.append(remaining)
            # Pause after first update
            if remaining == 3:
                self.engine.pause_timer(self.channel_id)
                # Resume after a short delay
                await asyncio.sleep(0.5)
                self.engine.resume_timer(self.channel_id)
        
        async def completion_callback():
            pass
        
        # Start timer
        await self.engine.start_question_timer(
            self.channel_id, 3, update_callback, completion_callback
        )
        
        # Should have received all updates despite pause
        self.assertEqual(len(update_calls), 3)
    
    async def test_timer_cancellation(self):
        """Test timer cancellation during countdown."""
        update_calls = []
        completion_called = False
        
        async def update_callback(remaining):
            update_calls.append(remaining)
            # Cancel after first update
            if remaining == 3:
                self.engine.cancel_timer(self.channel_id)
        
        async def completion_callback():
            nonlocal completion_called
            completion_called = True
        
        # Start timer
        await self.engine.start_question_timer(
            self.channel_id, 3, update_callback, completion_callback
        )
        
        # Should have received only one update before cancellation
        self.assertEqual(len(update_calls), 1)
        self.assertFalse(completion_called)
    
    async def test_multiple_channel_timers(self):
        """Test managing timers for multiple channels."""
        channel1 = "channel_1"
        channel2 = "channel_2"
        
        update_calls_1 = []
        update_calls_2 = []
        
        async def update_callback_1(remaining):
            update_calls_1.append(remaining)
        
        async def update_callback_2(remaining):
            update_calls_2.append(remaining)
        
        async def completion_callback():
            pass
        
        # Start timers for both channels
        timer1_task = asyncio.create_task(
            self.engine.start_question_timer(
                channel1, 2, update_callback_1, completion_callback
            )
        )
        
        timer2_task = asyncio.create_task(
            self.engine.start_question_timer(
                channel2, 2, update_callback_2, completion_callback
            )
        )
        
        # Wait for both to complete
        await asyncio.gather(timer1_task, timer2_task)
        
        # Both should have received their updates
        self.assertEqual(len(update_calls_1), 2)
        self.assertEqual(len(update_calls_2), 2)


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
TestQuizTimer.test_timer_countdown_completion = async_test(TestQuizTimer.test_timer_countdown_completion)
TestQuizEngineTimer.test_start_question_timer = async_test(TestQuizEngineTimer.test_start_question_timer)
TestQuizEngineTimer.test_timer_pause_resume_integration = async_test(TestQuizEngineTimer.test_timer_pause_resume_integration)
TestQuizEngineTimer.test_timer_cancellation = async_test(TestQuizEngineTimer.test_timer_cancellation)
TestQuizEngineTimer.test_multiple_channel_timers = async_test(TestQuizEngineTimer.test_multiple_channel_timers)


class TestQuizEngineComprehensive(unittest.TestCase):
    """Comprehensive tests for QuizEngine functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = QuizEngine()
        self.sample_questions = TestFixtures.create_sample_questions()
    
    def test_question_selection_edge_cases(self):
        """Test question selection with edge cases."""
        settings = QuizSettings()
        
        # Test with single question
        single_question = [Question("Single?", "Answer")]
        result = self.engine.select_questions(single_question, settings)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], single_question[0])
        
        # Test with exact count match
        settings.question_count = len(self.sample_questions)
        result = self.engine.select_questions(self.sample_questions, settings)
        self.assertEqual(len(result), len(self.sample_questions))
    
    def test_randomization_distribution(self):
        """Test that randomization produces varied distributions."""
        settings = QuizSettings(random_order=True)
        
        # Generate multiple randomized sets
        results = []
        for _ in range(20):
            result = self.engine.select_questions(self.sample_questions, settings)
            results.append([q.text for q in result])
        
        # Check that we get different orderings
        unique_orderings = set(tuple(r) for r in results)
        self.assertGreater(len(unique_orderings), 1, "Randomization should produce different orderings")
    
    def test_question_selection_performance(self):
        """Test performance of question selection with large datasets."""
        # Create large question set
        large_questions = [
            Question(f"Question {i}?", f"Answer {i}")
            for i in range(1000)
        ]
        
        settings = QuizSettings(question_count=100, random_order=True)
        
        # Measure time
        start_time = time.time()
        result = self.engine.select_questions(large_questions, settings)
        end_time = time.time()
        
        # Should complete quickly (under 1 second)
        self.assertLess(end_time - start_time, 1.0)
        self.assertEqual(len(result), 100)
    
    def test_memory_efficiency(self):
        """Test memory efficiency of question operations."""
        import sys
        
        # Create large question set
        large_questions = [
            Question(f"Question {i}?", f"Answer {i}")
            for i in range(5000)
        ]
        
        # Measure memory usage (approximate)
        initial_size = sys.getsizeof(large_questions)
        
        # Perform operations
        settings = QuizSettings(question_count=10, random_order=True)
        result = self.engine.select_questions(large_questions, settings)
        
        # Result should be much smaller
        result_size = sys.getsizeof(result)
        self.assertLess(result_size, initial_size / 10)
    
    async def test_timer_accuracy(self):
        """Test timer accuracy and precision."""
        timer = QuizTimer()
        
        start_time = time.time()
        update_times = []
        
        async def update_callback(remaining):
            update_times.append(time.time())
        
        async def completion_callback():
            pass
        
        # Start 3-second timer
        await timer.start_countdown(3, update_callback, completion_callback)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be approximately 3 seconds (allow 0.5s tolerance)
        self.assertAlmostEqual(total_time, 3.0, delta=0.5)
        
        # Should have received 3 updates
        self.assertEqual(len(update_times), 3)
    
    async def test_concurrent_timers_isolation(self):
        """Test that concurrent timers don't interfere with each other."""
        engine = QuizEngine()
        
        channel1_updates = []
        channel2_updates = []
        
        async def update_callback_1(remaining):
            channel1_updates.append(remaining)
        
        async def update_callback_2(remaining):
            channel2_updates.append(remaining)
        
        async def completion_callback():
            pass
        
        # Start timers with different durations
        timer1_task = asyncio.create_task(
            engine.start_question_timer("channel1", 2, update_callback_1, completion_callback)
        )
        
        timer2_task = asyncio.create_task(
            engine.start_question_timer("channel2", 3, update_callback_2, completion_callback)
        )
        
        # Wait for both to complete
        await asyncio.gather(timer1_task, timer2_task)
        
        # Verify independent operation
        self.assertEqual(len(channel1_updates), 2)
        self.assertEqual(len(channel2_updates), 3)
        self.assertEqual(channel1_updates, [2, 1])
        self.assertEqual(channel2_updates, [3, 2, 1])
    
    async def test_timer_error_handling(self):
        """Test timer error handling scenarios."""
        timer = QuizTimer()
        
        # Test with callback that raises exception
        async def failing_update_callback(remaining):
            if remaining == 2:
                raise ValueError("Test error")
        
        async def completion_callback():
            pass
        
        # Current implementation doesn't handle callback errors gracefully
        # The error should propagate up
        with self.assertRaises(ValueError):
            await timer.start_countdown(3, failing_update_callback, completion_callback)
    
    def test_question_validation(self):
        """Test question validation and sanitization."""
        # Test with various question formats
        test_questions = [
            Question("", "Answer"),  # Empty question
            Question("Question?", ""),  # Empty answer
            Question("   Whitespace question   ", "   Whitespace answer   "),
            Question("Question with\nnewlines", "Answer with\ttabs"),
        ]
        
        settings = QuizSettings()
        
        # Should handle all questions without crashing
        try:
            result = self.engine.select_questions(test_questions, settings)
            self.assertEqual(len(result), len(test_questions))
        except Exception as e:
            self.fail(f"Question validation failed: {e}")


# Apply async_test decorator to new async test methods
TestQuizEngineComprehensive.test_timer_accuracy = async_test(TestQuizEngineComprehensive.test_timer_accuracy)
TestQuizEngineComprehensive.test_concurrent_timers_isolation = async_test(TestQuizEngineComprehensive.test_concurrent_timers_isolation)
TestQuizEngineComprehensive.test_timer_error_handling = async_test(TestQuizEngineComprehensive.test_timer_error_handling)


if __name__ == '__main__':
    unittest.main()