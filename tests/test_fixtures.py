"""
Test fixtures and sample data for Discord Quiz Bot tests.
"""
import json
import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, AsyncMock
import discord

from src.models import Question, QuizSettings, QuizSession
from datetime import datetime


class TestFixtures:
    """Centralized test fixtures for all test modules."""
    
    @staticmethod
    def create_sample_questions() -> List[Question]:
        """Create sample questions for testing."""
        return [
            Question("What is 2+2?", "4"),
            Question("What is the capital of France?", "Paris", ["London", "Berlin", "Paris", "Madrid"]),
            Question("What color is the sky?", "Blue"),
            Question("What is 5*5?", "25"),
            Question("What is the largest planet?", "Jupiter", ["Earth", "Mars", "Jupiter", "Saturn"])
        ]
    
    @staticmethod
    def create_sample_quiz_settings() -> QuizSettings:
        """Create sample quiz settings for testing."""
        return QuizSettings(
            question_count=3,
            random_order=False,
            timer_duration=10
        )
    
    @staticmethod
    def create_sample_quiz_session(channel_id: int = 12345, quiz_name: str = "test_quiz") -> QuizSession:
        """Create sample quiz session for testing."""
        return QuizSession(
            channel_id=channel_id,
            quiz_name=quiz_name,
            questions=TestFixtures.create_sample_questions(),
            current_index=0,
            is_paused=False,
            is_active=True,
            settings=TestFixtures.create_sample_quiz_settings(),
            start_time=datetime.now()
        )
    
    @staticmethod
    def create_valid_quiz_json() -> Dict:
        """Create valid quiz JSON structure."""
        return {
            "quiz": [
                {
                    "question": "What is the capital of Japan?",
                    "answer": "Tokyo"
                },
                {
                    "question": "What is 10 + 5?",
                    "answer": "15",
                    "options": ["10", "15", "20", "25"]
                },
                {
                    "question": "What programming language is this bot written in?",
                    "answer": "Python"
                }
            ]
        }
    
    @staticmethod
    def create_invalid_quiz_json_structures() -> List[Dict]:
        """Create various invalid quiz JSON structures for testing."""
        return [
            # Missing 'quiz' key
            {
                "questions": [
                    {"question": "Test?", "answer": "Test"}
                ]
            },
            # 'quiz' is not an array
            {
                "quiz": "not an array"
            },
            # Empty quiz array
            {
                "quiz": []
            },
            # Missing question field
            {
                "quiz": [
                    {"answer": "Test answer"}
                ]
            },
            # Missing answer field
            {
                "quiz": [
                    {"question": "Test question?"}
                ]
            },
            # Invalid field types
            {
                "quiz": [
                    {
                        "question": 123,  # Should be string
                        "answer": "Test answer"
                    }
                ]
            },
            # Invalid options type
            {
                "quiz": [
                    {
                        "question": "Test question?",
                        "answer": "Test answer",
                        "options": "not an array"
                    }
                ]
            }
        ]
    
    @staticmethod
    def create_temp_quiz_files(temp_dir: str) -> Dict[str, Path]:
        """Create temporary quiz files for testing."""
        quiz_files = {}
        
        # Valid quiz file
        valid_quiz = TestFixtures.create_valid_quiz_json()
        valid_file = Path(temp_dir) / "valid_quiz.json"
        with open(valid_file, 'w') as f:
            json.dump(valid_quiz, f)
        quiz_files["valid"] = valid_file
        
        # Large quiz file
        large_quiz = {
            "quiz": [
                {
                    "question": f"Question {i}?",
                    "answer": f"Answer {i}"
                }
                for i in range(50)
            ]
        }
        large_file = Path(temp_dir) / "large_quiz.json"
        with open(large_file, 'w') as f:
            json.dump(large_quiz, f)
        quiz_files["large"] = large_file
        
        # Quiz with options
        options_quiz = {
            "quiz": [
                {
                    "question": "What is the color of grass?",
                    "answer": "Green",
                    "options": ["Red", "Blue", "Green", "Yellow"]
                },
                {
                    "question": "How many days in a week?",
                    "answer": "7",
                    "options": ["5", "6", "7", "8"]
                }
            ]
        }
        options_file = Path(temp_dir) / "options_quiz.json"
        with open(options_file, 'w') as f:
            json.dump(options_quiz, f)
        quiz_files["options"] = options_file
        
        # Invalid JSON file
        invalid_file = Path(temp_dir) / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
        quiz_files["invalid"] = invalid_file
        
        # Invalid structure file
        invalid_structure = TestFixtures.create_invalid_quiz_json_structures()[0]
        invalid_structure_file = Path(temp_dir) / "invalid_structure.json"
        with open(invalid_structure_file, 'w') as f:
            json.dump(invalid_structure, f)
        quiz_files["invalid_structure"] = invalid_structure_file
        
        # Non-JSON file
        non_json_file = Path(temp_dir) / "not_a_quiz.txt"
        with open(non_json_file, 'w') as f:
            f.write("This is not a JSON file")
        quiz_files["non_json"] = non_json_file
        
        return quiz_files


class MockDiscordObjects:
    """Mock Discord objects for testing bot functionality."""
    
    @staticmethod
    def create_mock_interaction(channel_id: int = 12345, user_id: int = 67890) -> Mock:
        """Create mock Discord interaction."""
        interaction = Mock(spec=discord.Interaction)
        interaction.channel_id = channel_id
        interaction.user.id = user_id
        interaction.response = Mock()
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()
        interaction.followup = Mock()
        interaction.followup.send = AsyncMock()
        return interaction
    
    @staticmethod
    def create_mock_channel(channel_id: int = 12345) -> Mock:
        """Create mock Discord channel."""
        channel = Mock(spec=discord.TextChannel)
        channel.id = channel_id
        channel.send = AsyncMock()
        channel.edit = AsyncMock()
        return channel
    
    @staticmethod
    def create_mock_message(message_id: int = 11111, content: str = "Test message") -> Mock:
        """Create mock Discord message."""
        message = Mock(spec=discord.Message)
        message.id = message_id
        message.content = content
        message.edit = AsyncMock()
        message.delete = AsyncMock()
        return message
    
    @staticmethod
    def create_mock_embed() -> Mock:
        """Create mock Discord embed."""
        embed = Mock(spec=discord.Embed)
        embed.title = "Test Embed"
        embed.description = "Test Description"
        embed.color = 0x00ff00
        return embed


class AsyncTestHelpers:
    """Helper functions for async testing."""
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float = 5.0):
        """Run coroutine with timeout."""
        import asyncio
        return await asyncio.wait_for(coro, timeout=timeout)
    
    @staticmethod
    def create_async_mock_with_side_effect(side_effect):
        """Create async mock with side effect."""
        mock = AsyncMock()
        mock.side_effect = side_effect
        return mock


class TestDataValidation:
    """Validation helpers for test assertions."""
    
    @staticmethod
    def validate_question(question: Question) -> bool:
        """Validate Question object structure."""
        return (
            isinstance(question.text, str) and
            isinstance(question.answer, str) and
            isinstance(question.options, list) and
            len(question.text) > 0 and
            len(question.answer) > 0
        )
    
    @staticmethod
    def validate_quiz_settings(settings: QuizSettings) -> bool:
        """Validate QuizSettings object structure."""
        return (
            (settings.question_count is None or isinstance(settings.question_count, int)) and
            isinstance(settings.random_order, bool) and
            isinstance(settings.timer_duration, int) and
            settings.timer_duration > 0
        )
    
    @staticmethod
    def validate_quiz_session(session: QuizSession) -> bool:
        """Validate QuizSession object structure."""
        return (
            isinstance(session.channel_id, int) and
            isinstance(session.quiz_name, str) and
            isinstance(session.questions, list) and
            isinstance(session.current_index, int) and
            isinstance(session.is_paused, bool) and
            isinstance(session.is_active, bool) and
            TestDataValidation.validate_quiz_settings(session.settings) and
            isinstance(session.start_time, datetime) and
            session.current_index >= 0 and
            len(session.quiz_name) > 0 and
            len(session.questions) > 0
        )


class ErrorScenarios:
    """Common error scenarios for testing."""
    
    @staticmethod
    def get_file_system_errors():
        """Get file system error scenarios."""
        return [
            FileNotFoundError("File not found"),
            PermissionError("Permission denied"),
            OSError("OS error occurred"),
            json.JSONDecodeError("Invalid JSON", "test", 0)
        ]
    
    @staticmethod
    def get_discord_api_errors():
        """Get Discord API error scenarios."""
        return [
            discord.HTTPException(Mock(), "HTTP error"),
            discord.Forbidden(Mock(), "Forbidden"),
            discord.NotFound(Mock(), "Not found"),
            discord.ConnectionClosed(None, None)
        ]
    
    @staticmethod
    def get_validation_errors():
        """Get validation error scenarios."""
        return [
            ValueError("Invalid value"),
            TypeError("Invalid type"),
            KeyError("Missing key"),
            AttributeError("Missing attribute")
        ]