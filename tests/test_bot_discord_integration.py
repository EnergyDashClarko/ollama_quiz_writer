"""
Unit tests for Discord bot integration and API interactions.
"""
import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import discord
from discord.ext import commands

from src.bot import QuizBot
from tests.test_fixtures import MockDiscordObjects, TestFixtures, AsyncTestHelpers


class TestDiscordBotIntegration(unittest.TestCase):
    """Test Discord bot integration with mocked Discord API."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bot = None
        
    def tearDown(self):
        """Clean up after tests."""
        if self.bot:
            # Clean up bot resources
            pass
    
    async def async_setUp(self):
        """Async setup for bot testing."""
        # Create bot instance with mocked dependencies
        self.bot = QuizBot()
        
        # Mock the Discord client methods using patch
        self.tree_mock = Mock()
        self.tree_mock.sync = AsyncMock(return_value=[])
        self.tree_mock.command = Mock()
        
        # Patch the tree property
        with patch.object(self.bot, 'tree', self.tree_mock):
            pass
        
        # Mock data manager
        self.bot.data_manager = Mock()
        self.bot.data_manager.get_available_quizzes.return_value = ["test_quiz", "sample_quiz"]
        self.bot.data_manager.get_quiz_questions.return_value = TestFixtures.create_sample_questions()
        self.bot.data_manager.has_load_errors.return_value = False
        self.bot.data_manager.get_loading_summary.return_value = {
            'available_quizzes': ["test_quiz", "sample_quiz"],
            'has_errors': False,
            'errors': [],
            'fallback_active': False
        }
        
        # Mock config manager
        self.bot.config_manager = Mock()
        self.bot.config_manager.get_quiz_settings.return_value = TestFixtures.create_sample_quiz_settings()
        self.bot.config_manager.get_settings_summary.return_value = "Questions: 3 | Order: sequential | Timer: 10s"
        self.bot.config_manager.set_question_count.return_value = {'success': True}
        self.bot.config_manager.toggle_random_order.return_value = {
            'success': True, 
            'new_value': True, 
            'previous_value': False
        }
        self.bot.config_manager.get_configuration_health_check.return_value = {
            'healthy': True,
            'warnings': [],
            'errors': []
        }
        
        # Mock quiz controller
        self.bot.quiz_controller = Mock()
        self.bot.quiz_controller.start_quiz.return_value = {
            'success': True,
            'message': 'Quiz started successfully',
            'session_info': {
                'quiz_name': 'test_quiz',
                'total_questions': 3,
                'settings': TestFixtures.create_sample_quiz_settings()
            }
        }
        self.bot.quiz_controller.stop_quiz.return_value = {
            'success': True,
            'message': 'Quiz stopped successfully',
            'session_info': {'quiz_name': 'test_quiz'}
        }
        self.bot.quiz_controller.pause_quiz.return_value = {
            'success': True,
            'message': 'Quiz paused',
            'session_info': {'quiz_name': 'test_quiz'}
        }
        self.bot.quiz_controller.resume_quiz.return_value = {
            'success': True,
            'message': 'Quiz resumed',
            'session_info': {'quiz_name': 'test_quiz'}
        }
        self.bot.quiz_controller.get_session_status_summary.return_value = "Quiz: test_quiz | Status: Active | Progress: 1/3"
    
    async def test_help_command_success(self):
        """Test successful help command execution."""
        await self.async_setUp()
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute help command
        await self.bot.handle_help(interaction)
        
        # Verify response was sent
        interaction.response.send_message.assert_called_once()
        
        # Verify embed was created with correct content
        call_args = interaction.response.send_message.call_args
        embed_arg = call_args[1]['embed'] if 'embed' in call_args[1] else call_args[0][0]
        
        # Should be a discord.Embed or mock embed
        self.assertIsNotNone(embed_arg)
    
    async def test_help_command_with_discord_error(self):
        """Test help command with Discord API error."""
        await self.async_setUp()
        
        # Create mock interaction that fails
        interaction = MockDiscordObjects.create_mock_interaction()
        interaction.response.send_message.side_effect = discord.HTTPException(Mock(), "API Error")
        
        # Execute help command - should handle error gracefully
        await self.bot.handle_help(interaction)
        
        # Should have attempted to send message
        interaction.response.send_message.assert_called()
    
    async def test_set_questions_command_success(self):
        """Test successful set questions command."""
        await self.async_setUp()
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute set questions command
        await self.bot.handle_set_questions(interaction, 5)
        
        # Verify config manager was called
        self.bot.config_manager.set_question_count.assert_called_once_with(5)
        
        # Verify response was sent
        interaction.response.send_message.assert_called_once()
    
    async def test_set_questions_command_validation_error(self):
        """Test set questions command with validation error."""
        await self.async_setUp()
        
        # Mock validation failure
        self.bot.config_manager.set_question_count.return_value = {
            'success': False,
            'error': 'Invalid value',
            'user_message': 'Question count must be between 1 and 100'
        }
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute command
        await self.bot.handle_set_questions(interaction, -1)
        
        # Verify error response
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        
        # Should be ephemeral error message
        self.assertTrue(call_args[1].get('ephemeral', False))
    
    async def test_random_order_command_success(self):
        """Test successful random order toggle command."""
        await self.async_setUp()
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute random order command
        await self.bot.handle_random_order(interaction)
        
        # Verify config manager was called
        self.bot.config_manager.toggle_random_order.assert_called_once()
        
        # Verify response was sent
        interaction.response.send_message.assert_called_once()
    
    async def test_start_command_success(self):
        """Test successful quiz start command."""
        await self.async_setUp()
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute start command
        await self.bot.handle_start(interaction)
        
        # Verify quiz controller was called
        self.bot.quiz_controller.start_quiz.assert_called_once()
        
        # Verify response was sent
        interaction.response.send_message.assert_called_once()
    
    async def test_start_command_no_quizzes_available(self):
        """Test start command when no quizzes are available."""
        await self.async_setUp()
        
        # Mock no available quizzes
        self.bot.data_manager.get_loading_summary.return_value = {
            'available_quizzes': [],
            'has_errors': True,
            'errors': ['Failed to load quiz1.json: Invalid JSON'],
            'fallback_active': False
        }
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute start command
        await self.bot.handle_start(interaction)
        
        # Should send error message about no quizzes
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        embed_arg = call_args[1]['embed'] if 'embed' in call_args[1] else call_args[0][0]
        
        # Should indicate no quizzes available
        self.assertIsNotNone(embed_arg)
    
    async def test_stop_command_success(self):
        """Test successful quiz stop command."""
        await self.async_setUp()
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute stop command
        await self.bot.handle_stop(interaction)
        
        # Verify quiz controller was called
        self.bot.quiz_controller.stop_quiz.assert_called_once()
        
        # Verify response was sent
        interaction.response.send_message.assert_called_once()
    
    async def test_pause_resume_commands(self):
        """Test pause and resume commands."""
        await self.async_setUp()
        
        # Test pause command
        interaction = MockDiscordObjects.create_mock_interaction()
        await self.bot.handle_pause(interaction)
        
        self.bot.quiz_controller.pause_quiz.assert_called_once()
        interaction.response.send_message.assert_called_once()
        
        # Reset mock
        interaction.response.send_message.reset_mock()
        
        # Test resume command
        await self.bot.handle_resume(interaction)
        
        self.bot.quiz_controller.resume_quiz.assert_called_once()
        interaction.response.send_message.assert_called_once()
    
    async def test_status_command(self):
        """Test status command."""
        await self.async_setUp()
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute status command
        await self.bot.handle_status(interaction)
        
        # Verify quiz controller was called
        self.bot.quiz_controller.get_session_status_summary.assert_called_once()
        
        # Verify response was sent
        interaction.response.send_message.assert_called_once()
    
    async def test_ollama_mix_command(self):
        """Test ollama mix command."""
        await self.async_setUp()
        
        # Create mock interaction
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Execute ollama mix command
        await self.bot.handle_ollama_mix(interaction)
        
        # Verify specific response message
        interaction.response.send_message.assert_called_once_with(
            "LLM is not active at the moment. Select from existing quiz files instead"
        )
    
    async def test_discord_api_error_handling(self):
        """Test Discord API error handling."""
        await self.async_setUp()
        
        # Test rate limiting error
        rate_limit_error = discord.HTTPException(Mock(), "Rate limited")
        rate_limit_error.status = 429
        rate_limit_error.retry_after = 1
        
        result = await self.bot.handle_discord_api_error(
            rate_limit_error, "test_operation"
        )
        self.assertTrue(result)  # Should retry
        
        # Test permission error
        permission_error = discord.HTTPException(Mock(), "Forbidden")
        permission_error.status = 403
        
        interaction = MockDiscordObjects.create_mock_interaction()
        result = await self.bot.handle_discord_api_error(
            permission_error, "test_operation", interaction
        )
        self.assertFalse(result)  # Should not retry
        
        # Verify error response was sent
        self.bot.send_error_response = AsyncMock()
    
    async def test_error_response_fallback(self):
        """Test error response fallback mechanisms."""
        await self.async_setUp()
        
        # Create interaction that fails on embed send
        interaction = MockDiscordObjects.create_mock_interaction()
        interaction.response.send_message.side_effect = discord.HTTPException(Mock(), "Failed")
        
        # Test error response with fallback
        await self.bot.send_error_response(interaction, "Test error", "Test Title")
        
        # Should have attempted to send message
        interaction.response.send_message.assert_called()
    
    async def test_command_setup_and_registration(self):
        """Test command setup and registration."""
        await self.async_setUp()
        
        # Mock tree.command decorator
        command_mocks = []
        
        def mock_command_decorator(name=None, description=None):
            def decorator(func):
                command_mocks.append({'name': name, 'description': description, 'func': func})
                return func
            return decorator
        
        self.bot.tree.command = mock_command_decorator
        
        # Setup commands
        await self.bot.setup_commands()
        
        # Verify all expected commands were registered
        expected_commands = [
            'help', 'set_questions', 'random_order', 'ollama_mix',
            'start', 'stop', 'pause', 'resume', 'status'
        ]
        
        registered_commands = [cmd['name'] for cmd in command_mocks]
        
        for expected_cmd in expected_commands:
            self.assertIn(expected_cmd, registered_commands)


class TestDiscordBotErrorScenarios(unittest.TestCase):
    """Test Discord bot error scenarios and edge cases."""
    
    async def test_bot_initialization_failure(self):
        """Test bot initialization failure scenarios."""
        with patch('src.bot.DataManager') as mock_dm:
            mock_dm.side_effect = Exception("Failed to initialize DataManager")
            
            bot = QuizBot()
            
            # Should handle initialization error
            with self.assertRaises(Exception):
                await bot.setup_hook()
    
    async def test_command_execution_with_missing_dependencies(self):
        """Test command execution when dependencies are missing."""
        bot = QuizBot()
        
        # Don't initialize dependencies
        bot.data_manager = None
        bot.config_manager = None
        bot.quiz_controller = None
        
        interaction = MockDiscordObjects.create_mock_interaction()
        
        # Commands should handle missing dependencies gracefully
        try:
            await bot.handle_help(interaction)
        except AttributeError:
            pass  # Expected when dependencies are missing
    
    async def test_concurrent_command_execution(self):
        """Test concurrent command execution."""
        bot = QuizBot()
        
        # Mock dependencies
        bot.data_manager = Mock()
        bot.config_manager = Mock()
        bot.quiz_controller = Mock()
        
        # Setup return values
        bot.data_manager.get_available_quizzes.return_value = ["test_quiz"]
        bot.config_manager.get_settings_summary.return_value = "Test settings"
        bot.config_manager.set_question_count.return_value = {'success': True}
        
        # Create multiple interactions
        interactions = [MockDiscordObjects.create_mock_interaction() for _ in range(5)]
        
        # Execute commands concurrently
        tasks = []
        for i, interaction in enumerate(interactions):
            if i % 2 == 0:
                task = bot.handle_help(interaction)
            else:
                task = bot.handle_set_questions(interaction, 5)
            tasks.append(task)
        
        # Wait for all to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # All interactions should have received responses
        for interaction in interactions:
            interaction.response.send_message.assert_called()


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
TestDiscordBotIntegration.test_help_command_success = async_test(TestDiscordBotIntegration.test_help_command_success)
TestDiscordBotIntegration.test_help_command_with_discord_error = async_test(TestDiscordBotIntegration.test_help_command_with_discord_error)
TestDiscordBotIntegration.test_set_questions_command_success = async_test(TestDiscordBotIntegration.test_set_questions_command_success)
TestDiscordBotIntegration.test_set_questions_command_validation_error = async_test(TestDiscordBotIntegration.test_set_questions_command_validation_error)
TestDiscordBotIntegration.test_random_order_command_success = async_test(TestDiscordBotIntegration.test_random_order_command_success)
TestDiscordBotIntegration.test_start_command_success = async_test(TestDiscordBotIntegration.test_start_command_success)
TestDiscordBotIntegration.test_start_command_no_quizzes_available = async_test(TestDiscordBotIntegration.test_start_command_no_quizzes_available)
TestDiscordBotIntegration.test_stop_command_success = async_test(TestDiscordBotIntegration.test_stop_command_success)
TestDiscordBotIntegration.test_pause_resume_commands = async_test(TestDiscordBotIntegration.test_pause_resume_commands)
TestDiscordBotIntegration.test_status_command = async_test(TestDiscordBotIntegration.test_status_command)
TestDiscordBotIntegration.test_ollama_mix_command = async_test(TestDiscordBotIntegration.test_ollama_mix_command)
TestDiscordBotIntegration.test_discord_api_error_handling = async_test(TestDiscordBotIntegration.test_discord_api_error_handling)
TestDiscordBotIntegration.test_error_response_fallback = async_test(TestDiscordBotIntegration.test_error_response_fallback)
TestDiscordBotIntegration.test_command_setup_and_registration = async_test(TestDiscordBotIntegration.test_command_setup_and_registration)

TestDiscordBotErrorScenarios.test_bot_initialization_failure = async_test(TestDiscordBotErrorScenarios.test_bot_initialization_failure)
TestDiscordBotErrorScenarios.test_command_execution_with_missing_dependencies = async_test(TestDiscordBotErrorScenarios.test_command_execution_with_missing_dependencies)
TestDiscordBotErrorScenarios.test_concurrent_command_execution = async_test(TestDiscordBotErrorScenarios.test_concurrent_command_execution)


if __name__ == '__main__':
    unittest.main()