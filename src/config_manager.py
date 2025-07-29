"""
Configuration manager for Discord Quiz Bot settings and parameters.
"""
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import os

from .models import QuizSettings


class ConfigManager:
    """Manages bot configuration settings and quiz parameters."""
    
    # Default configuration values
    DEFAULT_QUESTION_COUNT = None  # Use all questions by default
    DEFAULT_RANDOM_ORDER = False
    DEFAULT_TIMER_DURATION = 30
    DEFAULT_QUIZ_DIRECTORY = "./quizzes/"
    
    # Validation limits
    MIN_TIMER_DURATION = 5
    MAX_TIMER_DURATION = 300  # 5 minutes
    MIN_QUESTION_COUNT = 1
    MAX_QUESTION_COUNT = 100
    
    def __init__(self):
        """Initialize ConfigManager with default settings."""
        self.logger = logging.getLogger(__name__)
        self._global_settings = QuizSettings()
        self._quiz_directory = self.DEFAULT_QUIZ_DIRECTORY
        
    def get_quiz_settings(self) -> QuizSettings:
        """
        Get current quiz settings.
        
        Returns:
            QuizSettings object with current configuration
        """
        return QuizSettings(
            question_count=self._global_settings.question_count,
            random_order=self._global_settings.random_order,
            timer_duration=self._global_settings.timer_duration
        )
    
    def set_question_count(self, count: Optional[int]) -> Dict[str, any]:
        """
        Set the number of questions for quizzes with detailed error reporting.
        
        Args:
            count: Number of questions, or None to use all questions
            
        Returns:
            Dictionary with success status, error message, and user-friendly message
        """
        try:
            if count is None:
                self._global_settings.question_count = None
                self.logger.info("Question count set to use all available questions")
                return {
                    'success': True,
                    'message': "Question count set to use all available questions",
                    'user_message': "✅ Will use all available questions from each quiz"
                }
            
            # Type validation
            if not isinstance(count, int):
                error_msg = f"Question count must be an integer, got {type(count).__name__}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Invalid input: Expected a number, got {type(count).__name__}"
                }
            
            # Range validation
            if count < self.MIN_QUESTION_COUNT:
                error_msg = f"Question count must be at least {self.MIN_QUESTION_COUNT}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Too few questions: Minimum is {self.MIN_QUESTION_COUNT}"
                }
            
            if count > self.MAX_QUESTION_COUNT:
                error_msg = f"Question count cannot exceed {self.MAX_QUESTION_COUNT}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Too many questions: Maximum is {self.MAX_QUESTION_COUNT}"
                }
            
            # Success case
            self._global_settings.question_count = count
            self.logger.info(f"Question count set to {count}")
            return {
                'success': True,
                'message': f"Question count set to {count}",
                'user_message': f"✅ Question count set to {count}"
            }
            
        except Exception as e:
            error_msg = f"Unexpected error setting question count: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user_message': "❌ An unexpected error occurred while setting question count"
            }
    
    def get_question_count(self) -> Optional[int]:
        """
        Get current question count setting.
        
        Returns:
            Number of questions, or None if using all questions
        """
        return self._global_settings.question_count
    
    def set_random_order(self, random_order: bool) -> Dict[str, any]:
        """
        Set whether questions should be presented in random order with error handling.
        
        Args:
            random_order: True for random order, False for sequential
            
        Returns:
            Dictionary with success status, error message, and user-friendly message
        """
        try:
            if not isinstance(random_order, bool):
                error_msg = f"Random order must be a boolean, got {type(random_order).__name__}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Invalid input: Expected true/false, got {type(random_order).__name__}"
                }
            
            self._global_settings.random_order = random_order
            order_type = "random" if random_order else "sequential"
            self.logger.info(f"Question order set to {order_type}")
            
            return {
                'success': True,
                'message': f"Question order set to {order_type}",
                'user_message': f"✅ Questions will be presented in {order_type} order"
            }
            
        except Exception as e:
            error_msg = f"Unexpected error setting random order: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user_message': "❌ An unexpected error occurred while setting question order"
            }
    
    def get_random_order(self) -> bool:
        """
        Get current random order setting.
        
        Returns:
            True if questions are in random order, False if sequential
        """
        return self._global_settings.random_order
    
    def toggle_random_order(self) -> Dict[str, any]:
        """
        Toggle the random order setting with error handling.
        
        Returns:
            Dictionary with success status, new value, and user-friendly message
        """
        try:
            new_value = not self._global_settings.random_order
            result = self.set_random_order(new_value)
            
            if result['success']:
                return {
                    'success': True,
                    'new_value': new_value,
                    'message': result['message'],
                    'user_message': result['user_message']
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Unexpected error toggling random order: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user_message': "❌ An unexpected error occurred while toggling question order"
            }
    
    def set_timer_duration(self, duration: int) -> Dict[str, any]:
        """
        Set the timer duration for each question with error handling.
        
        Args:
            duration: Timer duration in seconds
            
        Returns:
            Dictionary with success status, error message, and user-friendly message
        """
        try:
            if not isinstance(duration, int):
                error_msg = f"Timer duration must be an integer, got {type(duration).__name__}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Invalid input: Expected a number, got {type(duration).__name__}"
                }
            
            if duration < self.MIN_TIMER_DURATION:
                error_msg = f"Timer duration must be at least {self.MIN_TIMER_DURATION} seconds"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Timer too short: Minimum is {self.MIN_TIMER_DURATION} seconds"
                }
            
            if duration > self.MAX_TIMER_DURATION:
                error_msg = f"Timer duration cannot exceed {self.MAX_TIMER_DURATION} seconds"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Timer too long: Maximum is {self.MAX_TIMER_DURATION} seconds ({self.MAX_TIMER_DURATION // 60} minutes)"
                }
            
            self._global_settings.timer_duration = duration
            self.logger.info(f"Timer duration set to {duration} seconds")
            return {
                'success': True,
                'message': f"Timer duration set to {duration} seconds",
                'user_message': f"✅ Timer set to {duration} seconds"
            }
            
        except Exception as e:
            error_msg = f"Unexpected error setting timer duration: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user_message': "❌ An unexpected error occurred while setting timer duration"
            }
    
    def get_timer_duration(self) -> int:
        """
        Get current timer duration setting.
        
        Returns:
            Timer duration in seconds
        """
        return self._global_settings.timer_duration
    
    def set_quiz_directory(self, directory: str) -> Dict[str, any]:
        """
        Set the directory path for quiz files with validation and error handling.
        
        Args:
            directory: Path to quiz files directory
            
        Returns:
            Dictionary with success status, error message, and user-friendly message
        """
        try:
            if not isinstance(directory, str):
                error_msg = f"Quiz directory must be a string, got {type(directory).__name__}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Invalid input: Expected a path string, got {type(directory).__name__}"
                }
            
            if not directory.strip():
                error_msg = "Quiz directory cannot be empty"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': "❌ Directory path cannot be empty"
                }
            
            # Validate path format
            try:
                normalized_path = str(Path(directory).resolve())
            except (OSError, ValueError) as e:
                error_msg = f"Invalid directory path format: {e}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Invalid path format: {directory}"
                }
            
            # Check if path is reasonable (not system directories)
            path_obj = Path(normalized_path)
            system_dirs = ['/bin', '/usr', '/etc', '/sys', '/proc', 'C:\\Windows', 'C:\\Program Files']
            if any(str(path_obj).startswith(sys_dir) for sys_dir in system_dirs):
                error_msg = f"Cannot use system directory: {normalized_path}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'user_message': f"❌ Cannot use system directory: {directory}"
                }
            
            self._quiz_directory = normalized_path
            self.logger.info(f"Quiz directory set to {normalized_path}")
            return {
                'success': True,
                'message': f"Quiz directory set to {normalized_path}",
                'user_message': f"✅ Quiz directory set to {normalized_path}"
            }
            
        except Exception as e:
            error_msg = f"Unexpected error setting quiz directory: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user_message': "❌ An unexpected error occurred while setting quiz directory"
            }
    
    def get_quiz_directory(self) -> str:
        """
        Get current quiz directory setting.
        
        Returns:
            Path to quiz files directory
        """
        return self._quiz_directory
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values."""
        self._global_settings = QuizSettings(
            question_count=self.DEFAULT_QUESTION_COUNT,
            random_order=self.DEFAULT_RANDOM_ORDER,
            timer_duration=self.DEFAULT_TIMER_DURATION
        )
        self._quiz_directory = self.DEFAULT_QUIZ_DIRECTORY
        self.logger.info("All settings reset to default values")
    
    def validate_settings(self) -> Dict[str, Any]:
        """
        Validate current settings and return validation results.
        
        Returns:
            Dictionary with validation results and any issues found
        """
        validation_result = {
            "valid": True,
            "issues": []
        }
        
        # Validate question count
        if self._global_settings.question_count is not None:
            if (not isinstance(self._global_settings.question_count, int) or
                self._global_settings.question_count < self.MIN_QUESTION_COUNT or
                self._global_settings.question_count > self.MAX_QUESTION_COUNT):
                validation_result["valid"] = False
                validation_result["issues"].append(
                    f"Invalid question count: {self._global_settings.question_count}"
                )
        
        # Validate random order
        if not isinstance(self._global_settings.random_order, bool):
            validation_result["valid"] = False
            validation_result["issues"].append(
                f"Invalid random order setting: {self._global_settings.random_order}"
            )
        
        # Validate timer duration
        if (not isinstance(self._global_settings.timer_duration, int) or
            self._global_settings.timer_duration < self.MIN_TIMER_DURATION or
            self._global_settings.timer_duration > self.MAX_TIMER_DURATION):
            validation_result["valid"] = False
            validation_result["issues"].append(
                f"Invalid timer duration: {self._global_settings.timer_duration}"
            )
        
        # Validate quiz directory
        if not isinstance(self._quiz_directory, str) or not self._quiz_directory.strip():
            validation_result["valid"] = False
            validation_result["issues"].append(
                f"Invalid quiz directory: {self._quiz_directory}"
            )
        
        return validation_result
    
    def get_settings_summary(self) -> str:
        """
        Get a formatted summary of current settings.
        
        Returns:
            Human-readable string describing current settings
        """
        question_count_str = (
            str(self._global_settings.question_count) 
            if self._global_settings.question_count is not None 
            else "all available"
        )
        
        order_str = "random" if self._global_settings.random_order else "sequential"
        
        return (
            f"Quiz Settings:\n"
            f"• Questions: {question_count_str}\n"
            f"• Order: {order_str}\n"
            f"• Timer: {self._global_settings.timer_duration} seconds\n"
            f"• Quiz Directory: {self._quiz_directory}"
        )
    
    def get_user_friendly_validation_errors(self) -> List[str]:
        """
        Get user-friendly validation error messages for current settings.
        
        Returns:
            List of user-friendly error messages
        """
        validation_result = self.validate_settings()
        user_friendly_errors = []
        
        for issue in validation_result.get("issues", []):
            if "question count" in issue.lower():
                user_friendly_errors.append(
                    f"❌ Question Count Issue: {issue}. "
                    f"Please set a value between {self.MIN_QUESTION_COUNT} and {self.MAX_QUESTION_COUNT}."
                )
            elif "random order" in issue.lower():
                user_friendly_errors.append(
                    f"❌ Random Order Issue: {issue}. "
                    "Please use /random_order to toggle this setting."
                )
            elif "timer duration" in issue.lower():
                user_friendly_errors.append(
                    f"❌ Timer Duration Issue: {issue}. "
                    f"Please set a value between {self.MIN_TIMER_DURATION} and {self.MAX_TIMER_DURATION} seconds."
                )
            elif "quiz directory" in issue.lower():
                user_friendly_errors.append(
                    f"❌ Quiz Directory Issue: {issue}. "
                    "Please check the directory path and permissions."
                )
            else:
                user_friendly_errors.append(f"❌ Configuration Issue: {issue}")
        
        return user_friendly_errors
    
    def get_configuration_health_check(self) -> Dict[str, any]:
        """
        Perform a comprehensive health check of the configuration.
        
        Returns:
            Dictionary with health status and recommendations
        """
        health_check = {
            'healthy': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        try:
            # Check validation status
            validation_result = self.validate_settings()
            if not validation_result['valid']:
                health_check['healthy'] = False
                health_check['errors'].extend(self.get_user_friendly_validation_errors())
            
            # Check quiz directory accessibility
            quiz_dir = Path(self._quiz_directory)
            if not quiz_dir.exists():
                health_check['warnings'].append(
                    f"⚠️ Quiz directory does not exist: {self._quiz_directory}"
                )
                health_check['recommendations'].append(
                    "The quiz directory will be created automatically when loading quiz files."
                )
            elif not os.access(quiz_dir, os.R_OK):
                health_check['healthy'] = False
                health_check['errors'].append(
                    f"❌ Cannot read quiz directory: {self._quiz_directory}"
                )
                health_check['recommendations'].append(
                    "Check file permissions for the quiz directory."
                )
            
            # Check for reasonable settings
            if self._global_settings.question_count and self._global_settings.question_count > 50:
                health_check['warnings'].append(
                    f"⚠️ Large question count ({self._global_settings.question_count}) may result in very long quizzes"
                )
                health_check['recommendations'].append(
                    "Consider using a smaller question count for better user experience."
                )
            
            if self._global_settings.timer_duration < 10:
                health_check['warnings'].append(
                    f"⚠️ Short timer duration ({self._global_settings.timer_duration}s) may not give users enough time"
                )
                health_check['recommendations'].append(
                    "Consider using at least 10 seconds per question."
                )
            
            return health_check
            
        except Exception as e:
            self.logger.error(f"Error during configuration health check: {e}")
            return {
                'healthy': False,
                'warnings': [],
                'errors': [f"❌ Health check failed: {e}"],
                'recommendations': ["Please check the configuration and try again."]
            }