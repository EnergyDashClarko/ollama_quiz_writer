"""
Quiz session controller for the Discord Quiz Bot.
Manages active quiz sessions, configuration, and state per Discord channel.
"""
import logging
import asyncio
import discord
import time
from typing import Dict, Optional, List, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import traceback

from .models import QuizSession, Question, QuizSettings
from .quiz_engine import QuizEngine
from .data_manager import DataManager
from .config_manager import ConfigManager


class SessionState(Enum):
    """Enumeration of possible quiz session states."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class QuizControllerError(Exception):
    """Base exception for quiz controller errors."""
    pass


class SessionConflictError(QuizControllerError):
    """Raised when attempting to create a session that conflicts with existing session."""
    pass


class SessionNotFoundError(QuizControllerError):
    """Raised when attempting to operate on a non-existent session."""
    pass


class InvalidSessionStateError(QuizControllerError):
    """Raised when session is in an invalid state for the requested operation."""
    pass


class QuizController:
    """
    Orchestrates quiz sessions and manages state across Discord channels.
    
    This class handles the lifecycle of quiz sessions, including creation,
    state management, and cleanup. Each Discord channel can have at most
    one active quiz session at a time.
    """
    
    def __init__(self, data_manager: DataManager, config_manager: ConfigManager):
        """
        Initialize the quiz controller.
        
        Args:
            data_manager: Instance for loading quiz data
            config_manager: Instance for managing configuration
        """
        self.logger = logging.getLogger(__name__)
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.quiz_engine = QuizEngine()
        
        # Active sessions mapped by channel ID
        self._active_sessions: Dict[int, QuizSession] = {}
        
        # Error tracking and recovery
        self._session_errors: Dict[int, List[str]] = {}
        self._retry_counts: Dict[str, int] = {}
        self._max_retries = 3
        self._cleanup_interval = timedelta(hours=1)
        self._last_cleanup = datetime.now()
        
        self.logger.info("QuizController initialized")
    
    def create_session(
        self, 
        channel_id: int, 
        quiz_name: str, 
        settings: Optional[QuizSettings] = None
    ) -> bool:
        """
        Create a new quiz session for the specified channel.
        
        Args:
            channel_id: Discord channel identifier
            quiz_name: Name of the quiz to load
            settings: Optional quiz settings, uses global config if None
            
        Returns:
            True if session was created successfully, False otherwise
            
        Raises:
            ValueError: If quiz_name is invalid or questions cannot be loaded
        """
        # Check if session already exists for this channel
        if self.has_active_session(channel_id):
            self.logger.warning(f"Attempted to create session for channel {channel_id} "
                              f"but session already exists")
            return False
        
        try:
            # Load questions for the specified quiz
            questions = self.data_manager.get_quiz_questions(quiz_name)
            if not questions:
                raise ValueError(f"No questions found for quiz: {quiz_name}")
            
            # Use provided settings or get from config manager
            if settings is None:
                settings = self.config_manager.get_quiz_settings()
            
            # Select and order questions based on settings
            selected_questions = self.quiz_engine.select_questions(questions, settings)
            
            if not selected_questions:
                raise ValueError("No questions available after applying settings")
            
            # Create new session
            session = QuizSession(
                channel_id=channel_id,
                quiz_name=quiz_name,
                questions=selected_questions,
                current_index=0,
                is_paused=False,
                is_active=True,
                settings=settings,
                start_time=datetime.now()
            )
            
            # Store the session
            self._active_sessions[channel_id] = session
            
            self.logger.info(f"Created quiz session for channel {channel_id}: "
                           f"quiz='{quiz_name}', questions={len(selected_questions)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create session for channel {channel_id}: {e}")
            return False
    
    def get_session(self, channel_id: int) -> Optional[QuizSession]:
        """
        Get the active session for a channel.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            QuizSession if active session exists, None otherwise
        """
        return self._active_sessions.get(channel_id)
    
    def has_active_session(self, channel_id: int) -> bool:
        """
        Check if a channel has an active quiz session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if channel has active session, False otherwise
        """
        session = self._active_sessions.get(channel_id)
        return session is not None and session.is_active
    
    def get_session_state(self, channel_id: int) -> SessionState:
        """
        Get the current state of a session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Current session state
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None:
            return SessionState.INACTIVE
        
        if not session.is_active:
            return SessionState.COMPLETED
        
        if session.is_paused:
            return SessionState.PAUSED
        
        return SessionState.ACTIVE
    
    def pause_session(self, channel_id: int) -> bool:
        """
        Pause an active quiz session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if session was paused, False if no active session
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None or not session.is_active:
            self.logger.warning(
                f"Cannot pause session for channel {channel_id}: no active session",
                extra={
                    'event_type': 'session_pause_failed',
                    'channel_id': channel_id,
                    'reason': 'no_active_session',
                    'timestamp': time.time()
                }
            )
            return False
        
        if session.is_paused:
            self.logger.info(
                f"Session for channel {channel_id} is already paused",
                extra={
                    'event_type': 'session_already_paused',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
            return True
        
        session.is_paused = True
        
        # Pause any active timer with logging
        timer_paused = self.quiz_engine.pause_timer(str(channel_id))
        
        self.logger.info(
            f"Paused session for channel {channel_id}, timer paused: {timer_paused}",
            extra={
                'event_type': 'session_paused',
                'channel_id': channel_id,
                'timer_paused': timer_paused,
                'timestamp': time.time()
            }
        )
        return True
    
    def resume_session(self, channel_id: int) -> bool:
        """
        Resume a paused quiz session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if session was resumed, False if no paused session
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None or not session.is_active:
            self.logger.warning(
                f"Cannot resume session for channel {channel_id}: no active session",
                extra={
                    'event_type': 'session_resume_failed',
                    'channel_id': channel_id,
                    'reason': 'no_active_session',
                    'timestamp': time.time()
                }
            )
            return False
        
        if not session.is_paused:
            self.logger.info(
                f"Session for channel {channel_id} is not paused",
                extra={
                    'event_type': 'session_not_paused',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
            return True
        
        session.is_paused = False
        
        # Resume any active timer with logging
        timer_resumed = self.quiz_engine.resume_timer(str(channel_id))
        
        self.logger.info(
            f"Resumed session for channel {channel_id}, timer resumed: {timer_resumed}",
            extra={
                'event_type': 'session_resumed',
                'channel_id': channel_id,
                'timer_resumed': timer_resumed,
                'timestamp': time.time()
            }
        )
        return True
    
    async def stop_session(self, channel_id: int) -> bool:
        """
        Stop and cleanup an active quiz session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if session was stopped, False if no active session
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None:
            self.logger.warning(
                f"Cannot stop session for channel {channel_id}: no session exists",
                extra={
                    'event_type': 'session_stop_no_session',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
            return False
        
        # Mark session as inactive
        session.is_active = False
        session.is_paused = False
        
        # Cancel any active timer with comprehensive logging
        timer_cancelled = await self.quiz_engine.cancel_timer(str(channel_id))
        
        # Remove session from active sessions
        del self._active_sessions[channel_id]
        
        self.logger.info(
            f"Stopped and cleaned up session for channel {channel_id}, timer cancelled: {timer_cancelled}",
            extra={
                'event_type': 'session_stopped',
                'channel_id': channel_id,
                'timer_cancelled': timer_cancelled,
                'timestamp': time.time()
            }
        )
        return True
    
    def get_current_question(self, channel_id: int) -> Optional[Question]:
        """
        Get the current question for an active session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Current Question if session is active, None otherwise
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None or not session.is_active:
            return None
        
        if session.current_index >= len(session.questions):
            return None
        
        return session.questions[session.current_index]
    
    def advance_question(self, channel_id: int) -> bool:
        """
        Advance to the next question in the session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if advanced successfully, False if no more questions or no session
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None or not session.is_active:
            return False
        
        session.current_index += 1
        
        # Check if quiz is completed
        if session.current_index >= len(session.questions):
            self.logger.info(f"Quiz completed for channel {channel_id}")
            return False
        
        self.logger.debug(f"Advanced to question {session.current_index + 1} "
                         f"for channel {channel_id}")
        return True
    
    def get_session_progress(self, channel_id: int) -> Optional[Dict[str, any]]:
        """
        Get progress information for an active session.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with progress info, None if no active session
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None:
            return None
        
        return {
            'quiz_name': session.quiz_name,
            'current_question': session.current_index + 1,
            'total_questions': len(session.questions),
            'is_active': session.is_active,
            'is_paused': session.is_paused,
            'start_time': session.start_time,
            'settings': {
                'question_count': session.settings.question_count,
                'random_order': session.settings.random_order,
                'timer_duration': session.settings.timer_duration
            }
        }
    
    def validate_session_state(self, channel_id: int) -> Dict[str, any]:
        """
        Validate the state of a session and return diagnostic information.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with validation results and session state info
        """
        session = self._active_sessions.get(channel_id)
        
        if session is None:
            return {
                'valid': True,
                'state': SessionState.INACTIVE.value,
                'issues': []
            }
        
        issues = []
        
        # Check for invalid question index
        if session.current_index < 0:
            issues.append("Current question index is negative")
        elif session.current_index >= len(session.questions):
            issues.append("Current question index exceeds available questions")
        
        # Check for empty questions list
        if not session.questions:
            issues.append("Session has no questions")
        
        # Check for invalid channel ID
        if session.channel_id != channel_id:
            issues.append("Session channel ID mismatch")
        
        # Check for inconsistent state
        if not session.is_active and session.is_paused:
            issues.append("Session cannot be paused if not active")
        
        return {
            'valid': len(issues) == 0,
            'state': self.get_session_state(channel_id).value,
            'issues': issues,
            'session_info': self.get_session_progress(channel_id)
        }
    
    def cleanup_inactive_sessions(self) -> int:
        """
        Clean up sessions that are no longer active.
        
        Returns:
            Number of sessions cleaned up
        """
        inactive_channels = []
        
        for channel_id, session in self._active_sessions.items():
            if not session.is_active:
                inactive_channels.append(channel_id)
        
        for channel_id in inactive_channels:
            del self._active_sessions[channel_id]
            # Note: This is called from sync context, so we can't await here
            # The timer will be cleaned up when the session is removed
        
        if inactive_channels:
            self.logger.info(f"Cleaned up {len(inactive_channels)} inactive sessions")
        
        return len(inactive_channels)
    
    def _handle_session_error(self, channel_id: int, error: Exception, operation: str) -> Dict[str, Any]:
        """
        Handle session errors with logging and recovery attempts.
        
        Args:
            channel_id: Discord channel identifier
            error: The exception that occurred
            operation: Description of the operation that failed
            
        Returns:
            Dictionary with error handling results
        """
        error_msg = f"Error in {operation} for channel {channel_id}: {error}"
        self.logger.error(error_msg, exc_info=True)
        
        # Track errors per session
        if channel_id not in self._session_errors:
            self._session_errors[channel_id] = []
        
        self._session_errors[channel_id].append(f"{operation}: {str(error)}")
        
        # Attempt recovery based on error type
        recovery_result = self._attempt_error_recovery(channel_id, error, operation)
        
        return {
            'success': False,
            'error': str(error),
            'operation': operation,
            'recovery_attempted': recovery_result['attempted'],
            'recovery_successful': recovery_result['successful'],
            'user_message': self._get_user_friendly_error_message(error, operation)
        }
    
    def _attempt_error_recovery(self, channel_id: int, error: Exception, operation: str) -> Dict[str, bool]:
        """
        Attempt to recover from session errors.
        
        Args:
            channel_id: Discord channel identifier
            error: The exception that occurred
            operation: Description of the operation that failed
            
        Returns:
            Dictionary with recovery attempt results
        """
        recovery_key = f"{channel_id}_{operation}"
        retry_count = self._retry_counts.get(recovery_key, 0)
        
        if retry_count >= self._max_retries:
            self.logger.warning(f"Max retries exceeded for {recovery_key}")
            return {'attempted': False, 'successful': False}
        
        self._retry_counts[recovery_key] = retry_count + 1
        
        try:
            # Attempt different recovery strategies based on error type
            if isinstance(error, SessionConflictError):
                # Clean up conflicting session
                self.logger.info(f"Attempting to resolve session conflict for channel {channel_id}")
                self.stop_session(channel_id)
                return {'attempted': True, 'successful': True}
            
            elif isinstance(error, InvalidSessionStateError):
                # Reset session state
                self.logger.info(f"Attempting to reset session state for channel {channel_id}")
                session = self._active_sessions.get(channel_id)
                if session:
                    session.is_paused = False
                    self.quiz_engine.cancel_timer(str(channel_id))
                return {'attempted': True, 'successful': True}
            
            elif "timer" in str(error).lower():
                # Timer-related errors
                self.logger.info(f"Attempting to recover from timer error for channel {channel_id}")
                self.quiz_engine.cancel_timer(str(channel_id))
                return {'attempted': True, 'successful': True}
            
            elif "discord" in str(error).lower() or "http" in str(error).lower():
                # Discord API errors - will be handled by retry logic in bot.py
                return {'attempted': False, 'successful': False}
            
            else:
                # Generic recovery - clean up session
                self.logger.info(f"Attempting generic recovery for channel {channel_id}")
                self._cleanup_session_errors(channel_id)
                return {'attempted': True, 'successful': False}
                
        except Exception as recovery_error:
            self.logger.error(f"Recovery attempt failed for {recovery_key}: {recovery_error}")
            return {'attempted': True, 'successful': False}
    
    def _get_user_friendly_error_message(self, error: Exception, operation: str) -> str:
        """
        Generate user-friendly error messages.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            
        Returns:
            User-friendly error message
        """
        if isinstance(error, SessionConflictError):
            return "❌ A quiz is already running in this channel. Please stop it first with `/stop`."
        
        elif isinstance(error, SessionNotFoundError):
            return "❌ No active quiz found in this channel. Start a quiz with `/start`."
        
        elif isinstance(error, InvalidSessionStateError):
            return "❌ The quiz is in an invalid state. Please try stopping and restarting the quiz."
        
        elif "timer" in str(error).lower():
            return "❌ Timer error occurred. The quiz will continue without the timer."
        
        elif "discord" in str(error).lower():
            return "❌ Discord connection error. Please try again in a moment."
        
        elif "permission" in str(error).lower():
            return "❌ Permission error. Please check bot permissions in this channel."
        
        elif "quiz" in str(error).lower() and "not found" in str(error).lower():
            return "❌ Quiz file not found. Please check available quizzes with `/help`."
        
        elif "question" in str(error).lower():
            return "❌ Error loading quiz questions. Please try a different quiz."
        
        else:
            return f"❌ An unexpected error occurred during {operation}. Please try again."
    
    def _cleanup_session_errors(self, channel_id: int) -> None:
        """
        Clean up error tracking for a specific session.
        
        Args:
            channel_id: Discord channel identifier
        """
        if channel_id in self._session_errors:
            del self._session_errors[channel_id]
        
        # Clean up retry counts for this channel
        keys_to_remove = [key for key in self._retry_counts.keys() if key.startswith(str(channel_id))]
        for key in keys_to_remove:
            del self._retry_counts[key]
    
    def _periodic_cleanup(self) -> None:
        """
        Perform periodic cleanup of error tracking and stale sessions.
        """
        now = datetime.now()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self.logger.info("Performing periodic cleanup")
        
        # Clean up old retry counts
        old_keys = []
        for key, count in self._retry_counts.items():
            if count >= self._max_retries:
                old_keys.append(key)
        
        for key in old_keys:
            del self._retry_counts[key]
        
        # Clean up old error records
        for channel_id in list(self._session_errors.keys()):
            if len(self._session_errors[channel_id]) > 10:  # Keep only last 10 errors
                self._session_errors[channel_id] = self._session_errors[channel_id][-10:]
        
        # Clean up inactive sessions
        self.cleanup_inactive_sessions()
        
        self._last_cleanup = now
        self.logger.info("Periodic cleanup completed")
    
    def start_quiz(self, channel_id: int, quiz_name: str) -> Dict[str, Any]:
        """
        Start a quiz with comprehensive error handling.
        
        Args:
            channel_id: Discord channel identifier
            quiz_name: Name of the quiz to start
            
        Returns:
            Dictionary with operation results and error information
        """
        try:
            self._periodic_cleanup()
            
            # Check for existing session
            if self.has_active_session(channel_id):
                raise SessionConflictError(f"Quiz already running in channel {channel_id}")
            
            # Validate quiz exists
            if not self.data_manager.quiz_exists(quiz_name):
                available_quizzes = self.data_manager.get_available_quizzes()
                if not available_quizzes:
                    raise ValueError("No quiz files available. Please add quiz files to the quizzes directory.")
                raise ValueError(f"Quiz '{quiz_name}' not found. Available quizzes: {', '.join(available_quizzes)}")
            
            # Create session
            success = self.create_session(channel_id, quiz_name)
            if not success:
                raise RuntimeError("Failed to create quiz session")
            
            # Get session info for response
            session_info = self.get_session_progress(channel_id)
            
            # Clear any previous errors for this channel
            self._cleanup_session_errors(channel_id)
            
            return {
                'success': True,
                'message': f"Quiz '{quiz_name}' started successfully",
                'session_info': session_info
            }
            
        except Exception as e:
            return self._handle_session_error(channel_id, e, "start_quiz")
    
    def stop_quiz(self, channel_id: int) -> Dict[str, Any]:
        """
        Stop a quiz with comprehensive error handling.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with operation results and error information
        """
        try:
            # Get session info before stopping
            session_info = self.get_session_progress(channel_id)
            
            if not self.has_active_session(channel_id):
                return {
                    'success': False,
                    'message': "No active quiz to stop in this channel",
                    'user_message': "ℹ️ No active quiz found in this channel"
                }
            
            # Stop the session
            success = self.stop_session(channel_id)
            if not success:
                raise RuntimeError("Failed to stop quiz session")
            
            # Clear errors for this channel
            self._cleanup_session_errors(channel_id)
            
            return {
                'success': True,
                'message': "Quiz stopped successfully",
                'session_info': session_info
            }
            
        except Exception as e:
            return self._handle_session_error(channel_id, e, "stop_quiz")
    
    def pause_quiz(self, channel_id: int) -> Dict[str, Any]:
        """
        Pause a quiz with comprehensive error handling.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with operation results and error information
        """
        try:
            session = self.get_session(channel_id)
            if not session or not session.is_active:
                raise SessionNotFoundError(f"No active quiz to pause in channel {channel_id}")
            
            if session.is_paused:
                return {
                    'success': True,
                    'message': "Quiz is already paused",
                    'session_info': self.get_session_progress(channel_id)
                }
            
            success = self.pause_session(channel_id)
            if not success:
                raise RuntimeError("Failed to pause quiz session")
            
            return {
                'success': True,
                'message': "Quiz paused successfully",
                'session_info': self.get_session_progress(channel_id)
            }
            
        except Exception as e:
            return self._handle_session_error(channel_id, e, "pause_quiz")
    
    def resume_quiz(self, channel_id: int) -> Dict[str, Any]:
        """
        Resume a quiz with comprehensive error handling.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with operation results and error information
        """
        try:
            session = self.get_session(channel_id)
            if not session or not session.is_active:
                raise SessionNotFoundError(f"No active quiz to resume in channel {channel_id}")
            
            if not session.is_paused:
                return {
                    'success': True,
                    'message': "Quiz is not paused",
                    'session_info': self.get_session_progress(channel_id)
                }
            
            success = self.resume_session(channel_id)
            if not success:
                raise RuntimeError("Failed to resume quiz session")
            
            return {
                'success': True,
                'message': "Quiz resumed successfully",
                'session_info': self.get_session_progress(channel_id)
            }
            
        except Exception as e:
            return self._handle_session_error(channel_id, e, "resume_quiz")
    

    

    

    
    async def _send_completion_message(self, discord_channel, session: QuizSession) -> None:
        """
        Send quiz completion message with error handling.
        
        Args:
            discord_channel: Discord channel object for sending messages
            session: Completed quiz session
        """
        try:
            duration = datetime.now() - session.start_time
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            
            embed = discord.Embed(
                title="🎉 Quiz Completed!",
                description=f"**{session.quiz_name}** has been completed",
                color=0x00ff00
            )
            
            embed.add_field(
                name="📊 Final Stats",
                value=(
                    f"Questions: {len(session.questions)}\n"
                    f"Duration: {minutes}m {seconds}s\n"
                    f"Settings: {'🔀 Random' if session.settings.random_order else '📋 Sequential'} order"
                ),
                inline=False
            )
            
            embed.set_footer(text="Thanks for playing! Use /start to begin a new quiz.")
            
            await discord_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error sending completion message: {e}")
            # Fallback to simple message
            try:
                await discord_channel.send("🎉 Quiz completed! Thanks for playing!")
            except Exception:
                self.logger.error("Failed to send fallback completion message")
    
    def get_error_summary(self, channel_id: int) -> Dict[str, Any]:
        """
        Get error summary for a specific channel.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with error information
        """
        return {
            'channel_id': channel_id,
            'errors': self._session_errors.get(channel_id, []),
            'error_count': len(self._session_errors.get(channel_id, [])),
            'has_errors': channel_id in self._session_errors
        }
    
    def get_all_active_sessions(self) -> Dict[int, Dict[str, any]]:
        """
        Get information about all active sessions.
        
        Returns:
            Dictionary mapping channel IDs to session progress info
        """
        active_sessions = {}
        
        for channel_id, session in self._active_sessions.items():
            if session.is_active:
                active_sessions[channel_id] = self.get_session_progress(channel_id)
        
        return active_sessions
    
    def get_available_quizzes(self) -> List[str]:
        """
        Get list of available quiz names.
        
        Returns:
            List of quiz names that can be used to create sessions
        """
        return self.data_manager.get_available_quizzes()
    
    def start_quiz(
        self, 
        channel_id: int, 
        quiz_name: str, 
        settings: Optional[QuizSettings] = None
    ) -> Dict[str, any]:
        """
        Start a new quiz session with comprehensive validation and error handling.
        
        Args:
            channel_id: Discord channel identifier
            quiz_name: Name of the quiz to start
            settings: Optional quiz settings, uses global config if None
            
        Returns:
            Dictionary with operation result and session info
        """
        result = {
            'success': False,
            'message': '',
            'session_info': None
        }
        
        # Check for existing active session
        if self.has_active_session(channel_id):
            result['message'] = "A quiz is already running in this channel. Use /stop to end it first."
            return result
        
        # Validate quiz name
        available_quizzes = self.get_available_quizzes()
        if quiz_name not in available_quizzes:
            result['message'] = f"Quiz '{quiz_name}' not found. Available quizzes: {', '.join(available_quizzes)}"
            return result
        
        # Create the session
        if self.create_session(channel_id, quiz_name, settings):
            session_info = self.get_session_progress(channel_id)
            result.update({
                'success': True,
                'message': f"Started quiz '{quiz_name}' with {session_info['total_questions']} questions.",
                'session_info': session_info
            })
            self.logger.info(f"Successfully started quiz '{quiz_name}' for channel {channel_id}")
        else:
            result['message'] = f"Failed to start quiz '{quiz_name}'. Please check the quiz file and try again."
            self.logger.error(f"Failed to start quiz '{quiz_name}' for channel {channel_id}")
        
        return result
    
    def stop_quiz(self, channel_id: int) -> Dict[str, any]:
        """
        Stop an active quiz session with validation and cleanup.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with operation result and final session info
        """
        result = {
            'success': False,
            'message': '',
            'session_info': None
        }
        
        # Get session info before stopping
        session_info = self.get_session_progress(channel_id)
        
        if not self.has_active_session(channel_id):
            result['message'] = "No active quiz session to stop in this channel."
            return result
        
        # Stop the session
        if self.stop_session(channel_id):
            result.update({
                'success': True,
                'message': "Quiz session stopped successfully.",
                'session_info': session_info
            })
            self.logger.info(f"Successfully stopped quiz session for channel {channel_id}")
        else:
            result['message'] = "Failed to stop quiz session."
            self.logger.error(f"Failed to stop quiz session for channel {channel_id}")
        
        return result
    
    def pause_quiz(self, channel_id: int) -> Dict[str, any]:
        """
        Pause an active quiz session with validation.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with operation result and session status
        """
        result = {
            'success': False,
            'message': '',
            'session_info': None
        }
        
        if not self.has_active_session(channel_id):
            result['message'] = "No active quiz session to pause in this channel."
            return result
        
        session = self.get_session(channel_id)
        if session and session.is_paused:
            result.update({
                'success': True,
                'message': "Quiz is already paused.",
                'session_info': self.get_session_progress(channel_id)
            })
            return result
        
        # Pause the session
        if self.pause_session(channel_id):
            result.update({
                'success': True,
                'message': "Quiz session paused. Use /resume to continue.",
                'session_info': self.get_session_progress(channel_id)
            })
            self.logger.info(f"Successfully paused quiz session for channel {channel_id}")
        else:
            result['message'] = "Failed to pause quiz session."
            self.logger.error(f"Failed to pause quiz session for channel {channel_id}")
        
        return result
    
    def resume_quiz(self, channel_id: int) -> Dict[str, any]:
        """
        Resume a paused quiz session with validation.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with operation result and session status
        """
        result = {
            'success': False,
            'message': '',
            'session_info': None
        }
        
        if not self.has_active_session(channel_id):
            result['message'] = "No active quiz session to resume in this channel."
            return result
        
        session = self.get_session(channel_id)
        if session and not session.is_paused:
            result.update({
                'success': True,
                'message': "Quiz is not paused.",
                'session_info': self.get_session_progress(channel_id)
            })
            return result
        
        # Resume the session
        if self.resume_session(channel_id):
            result.update({
                'success': True,
                'message': "Quiz session resumed.",
                'session_info': self.get_session_progress(channel_id)
            })
            self.logger.info(f"Successfully resumed quiz session for channel {channel_id}")
        else:
            result['message'] = "Failed to resume quiz session."
            self.logger.error(f"Failed to resume quiz session for channel {channel_id}")
        
        return result
    
    def handle_session_conflicts(self, channel_id: int) -> Dict[str, any]:
        """
        Handle and resolve session conflicts for a channel.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with conflict resolution results
        """
        result = {
            'conflicts_found': False,
            'conflicts_resolved': False,
            'issues': [],
            'actions_taken': []
        }
        
        validation = self.validate_session_state(channel_id)
        
        if not validation['valid']:
            result['conflicts_found'] = True
            result['issues'] = validation['issues']
            
            # Attempt to resolve conflicts
            session = self.get_session(channel_id)
            if session:
                # Fix invalid question index
                if session.current_index < 0:
                    session.current_index = 0
                    result['actions_taken'].append("Reset question index to 0")
                elif session.current_index >= len(session.questions):
                    # Mark session as completed
                    session.is_active = False
                    result['actions_taken'].append("Marked session as completed due to invalid question index")
                
                # Fix inconsistent state
                if not session.is_active and session.is_paused:
                    session.is_paused = False
                    result['actions_taken'].append("Fixed inconsistent pause state")
                
                # Clean up if session has no questions
                if not session.questions:
                    self.stop_session(channel_id)
                    result['actions_taken'].append("Removed session with no questions")
            
            # Re-validate after fixes
            new_validation = self.validate_session_state(channel_id)
            result['conflicts_resolved'] = new_validation['valid']
            
            if result['conflicts_resolved']:
                self.logger.info(f"Resolved session conflicts for channel {channel_id}: "
                               f"{', '.join(result['actions_taken'])}")
            else:
                self.logger.warning(f"Could not fully resolve session conflicts for channel {channel_id}")
        
        return result
    
    def get_session_status_summary(self, channel_id: int) -> str:
        """
        Get a human-readable summary of the session status.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Formatted string describing the session status
        """
        session_info = self.get_session_progress(channel_id)
        
        if session_info is None:
            return "No active quiz session in this channel."
        
        state = self.get_session_state(channel_id)
        status_parts = []
        
        # Basic info
        status_parts.append(f"Quiz: {session_info['quiz_name']}")
        status_parts.append(f"Progress: {session_info['current_question']}/{session_info['total_questions']}")
        
        # State info
        if state == SessionState.ACTIVE:
            status_parts.append("Status: Active")
        elif state == SessionState.PAUSED:
            status_parts.append("Status: Paused")
        elif state == SessionState.COMPLETED:
            status_parts.append("Status: Completed")
        
        # Settings info
        settings = session_info['settings']
        if settings['random_order']:
            status_parts.append("Order: Random")
        else:
            status_parts.append("Order: Sequential")
        
        status_parts.append(f"Timer: {settings['timer_duration']}s per question")
        
        # Duration info
        start_time = session_info['start_time']
        duration = datetime.now() - start_time
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)
        status_parts.append(f"Duration: {minutes}m {seconds}s")
        
        return " | ".join(status_parts)
    
    def get_next_question(self, channel_id: int) -> Optional[Question]:
        """
        Get the next question for an active session and advance the index.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Next Question if available, None if quiz is complete or no session
        """
        session = self.get_session(channel_id)
        
        if session is None or not session.is_active or session.is_paused:
            return None
        
        # Check if we have more questions
        if session.current_index >= len(session.questions):
            return None
        
        current_question = session.questions[session.current_index]
        
        # Advance to next question for future calls
        session.current_index += 1
        
        # Check if quiz is now complete
        if session.current_index >= len(session.questions):
            self.logger.info(f"Quiz completed for channel {channel_id}")
        
        return current_question
    
    def is_quiz_complete(self, channel_id: int) -> bool:
        """
        Check if the quiz is complete (all questions have been presented).
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if quiz is complete, False otherwise
        """
        session = self.get_session(channel_id)
        
        if session is None:
            return True  # No session means "complete" in a sense
        
        return session.current_index >= len(session.questions)
    
    def get_quiz_completion_info(self, channel_id: int) -> Optional[Dict[str, any]]:
        """
        Get completion information for a finished quiz.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with completion info, None if quiz not complete
        """
        session = self.get_session(channel_id)
        
        if session is None or not self.is_quiz_complete(channel_id):
            return None
        
        duration = datetime.now() - session.start_time
        
        return {
            'quiz_name': session.quiz_name,
            'total_questions': len(session.questions),
            'duration': {
                'total_seconds': int(duration.total_seconds()),
                'minutes': int(duration.total_seconds() // 60),
                'seconds': int(duration.total_seconds() % 60)
            },
            'settings': {
                'question_count': session.settings.question_count,
                'random_order': session.settings.random_order,
                'timer_duration': session.settings.timer_duration
            },
            'start_time': session.start_time,
            'completion_time': datetime.now()
        }
    
    async def present_question(self, channel_id: int, channel: discord.TextChannel) -> Optional[discord.Message]:
        """
        Present the current question to Discord with countdown timer.
        Enhanced with comprehensive timer error handling and retry logic.
        
        Args:
            channel_id: Discord channel identifier
            channel: Discord channel object to send message to
            
        Returns:
            Discord message object if question was presented, None otherwise
        """
        session = self.get_session(channel_id)
        
        if session is None or not session.is_active or session.is_paused:
            self.logger.debug(f"Cannot present question for channel {channel_id}: invalid session state")
            return None
        
        current_question = self.get_current_question(channel_id)
        if current_question is None:
            self.logger.warning(f"No current question available for channel {channel_id}")
            return None
        
        # Create question embed
        embed = discord.Embed(
            title=f"🎯 Question {session.current_index + 1}/{len(session.questions)}",
            description=current_question.text,
            color=0x00ff00
        )
        
        # Add timer info
        embed.add_field(
            name="⏱️ Time Remaining",
            value=f"{session.settings.timer_duration} seconds",
            inline=True
        )
        
        # Add quiz info
        embed.add_field(
            name="📚 Quiz",
            value=session.quiz_name,
            inline=True
        )
        
        embed.set_footer(text="Answer will be revealed when time expires")
        
        try:
            # Send the question message
            message = await channel.send(embed=embed)
            self.logger.debug(f"Question message sent successfully for channel {channel_id}")
            
            # Small delay to ensure message is fully sent before starting timer
            await asyncio.sleep(0.1)
            
            # Attempt to start timer with comprehensive error handling and retry logic
            timer_started = await self._start_timer_with_retry(
                channel_id, session, message, current_question
            )
            
            if not timer_started:
                # Graceful fallback: proceed without timer
                self.logger.warning(f"Timer failed to start for channel {channel_id}, proceeding without timer")
                await self._handle_timer_fallback(message, session, current_question, channel_id)
            
            return message
            
        except discord.HTTPException as e:
            self.logger.error(f"Discord HTTP error sending question message for channel {channel_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in present_question for channel {channel_id}: {e}", exc_info=True)
            # Ensure cleanup on any error
            try:
                self.quiz_engine.cancel_timer(str(channel_id))
            except Exception as cleanup_error:
                self.logger.error(f"Error during timer cleanup in present_question for channel {channel_id}: {cleanup_error}")
            return None
    
    async def _start_timer_with_retry(
        self, 
        channel_id: int, 
        session: QuizSession, 
        message: discord.Message, 
        current_question: Question
    ) -> bool:
        """
        Start timer with comprehensive retry logic and error handling.
        
        Args:
            channel_id: Discord channel identifier
            session: Current quiz session
            message: Discord message to update
            current_question: Current question object
            
        Returns:
            True if timer started successfully, False otherwise
        """
        max_timer_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_timer_retries):
            try:
                self.logger.debug(f"Timer start attempt {attempt + 1}/{max_timer_retries} for channel {channel_id}")
                
                # Enhanced timer readiness check
                timer_ready = await self._verify_timer_readiness_with_cleanup(str(channel_id), attempt)
                
                if not timer_ready:
                    self.logger.warning(f"Timer readiness check failed for channel {channel_id} on attempt {attempt + 1}")
                    if attempt < max_timer_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        self.logger.error(f"Timer readiness validation failed after {max_timer_retries} attempts for channel {channel_id}")
                        return False
                
                # Attempt to start the timer
                await self.quiz_engine.start_question_timer(
                    str(channel_id),
                    session.settings.timer_duration,
                    lambda remaining_time: self._update_timer_message(message, current_question, session, remaining_time),
                    lambda: self._reveal_answer(message, current_question, session, channel_id)
                )
                
                self.logger.info(f"Timer started successfully for channel {channel_id} on attempt {attempt + 1}")
                return True
                
            except RuntimeError as e:
                self.logger.error(f"Timer start failed for channel {channel_id} on attempt {attempt + 1}: {e}")
                if attempt < max_timer_retries - 1:
                    self.logger.info(f"Retrying timer start for channel {channel_id} after {retry_delay}s delay")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error(f"Timer start failed after {max_timer_retries} attempts for channel {channel_id}: {e}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Unexpected error starting timer for channel {channel_id} on attempt {attempt + 1}: {e}", exc_info=True)
                if attempt < max_timer_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error(f"Timer start failed with unexpected error after {max_timer_retries} attempts for channel {channel_id}: {e}")
                    return False
        
        return False
    
    async def _verify_timer_readiness_with_cleanup(self, channel_id: str, attempt: int) -> bool:
        """
        Verify timer readiness with enhanced cleanup logic.
        
        Args:
            channel_id: Discord channel identifier
            attempt: Current attempt number (0-based)
            
        Returns:
            True if timer is ready, False otherwise
        """
        try:
            # Initial readiness check
            timer_ready = self.quiz_engine._verify_timer_readiness(channel_id)
            
            if timer_ready:
                self.logger.debug(f"Timer readiness verified for channel {channel_id}")
                return True
            
            # Timer not ready, attempt cleanup
            self.logger.debug(f"Timer not ready for channel {channel_id}, attempting cleanup (attempt {attempt + 1})")
            
            # Cancel any existing timer
            cleanup_success = self.quiz_engine.cancel_timer(channel_id)
            if cleanup_success:
                self.logger.debug(f"Timer cleanup successful for channel {channel_id}")
            else:
                self.logger.warning(f"Timer cleanup reported failure for channel {channel_id}")
            
            # Wait for cleanup to complete with increasing delay based on attempt
            cleanup_delay = 0.1 + (attempt * 0.05)  # Increase delay with each attempt
            await asyncio.sleep(cleanup_delay)
            
            # Re-verify readiness after cleanup
            timer_ready = self.quiz_engine._verify_timer_readiness(channel_id)
            
            if timer_ready:
                self.logger.debug(f"Timer readiness verified after cleanup for channel {channel_id}")
                return True
            else:
                self.logger.warning(f"Timer still not ready after cleanup for channel {channel_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during timer readiness verification for channel {channel_id}: {e}", exc_info=True)
            return False
    
    async def _handle_timer_fallback(
        self, 
        message: discord.Message, 
        session: QuizSession, 
        current_question: Question, 
        channel_id: int
    ) -> None:
        """
        Handle graceful fallback when timer fails to start.
        
        Args:
            message: Discord message to update
            session: Current quiz session
            current_question: Current question object
            channel_id: Discord channel identifier
        """
        try:
            self.logger.info(f"Implementing timer fallback for channel {channel_id}")
            
            # Update message to indicate timer issue with user-friendly message
            embed = message.embeds[0] if message.embeds else discord.Embed(
                title=f"🎯 Question {session.current_index + 1}/{len(session.questions)}",
                description=current_question.text,
                color=0xffa500  # Orange color to indicate issue
            )
            
            # Update or add timer status field
            embed.clear_fields()
            embed.add_field(
                name="⚠️ Timer Status",
                value="Timer unavailable - question will auto-advance",
                inline=True
            )
            
            embed.add_field(
                name="📚 Quiz",
                value=session.quiz_name,
                inline=True
            )
            
            embed.set_footer(text=f"Answer will be revealed in {session.settings.timer_duration} seconds")
            
            await message.edit(embed=embed)
            self.logger.debug(f"Updated message with timer fallback notice for channel {channel_id}")
            
            # Proceed without timer after the configured duration
            await asyncio.sleep(session.settings.timer_duration)
            
            # Reveal answer using the same callback that would be used by timer
            await self._reveal_answer(message, current_question, session, channel_id)
            self.logger.info(f"Timer fallback completed successfully for channel {channel_id}")
            
        except Exception as e:
            self.logger.error(f"Error during timer fallback for channel {channel_id}: {e}", exc_info=True)
            # Last resort: try to reveal answer anyway
            try:
                await self._reveal_answer(message, current_question, session, channel_id)
            except Exception as reveal_error:
                self.logger.error(f"Failed to reveal answer during fallback for channel {channel_id}: {reveal_error}")
    
    async def _update_timer_message(self, message: discord.Message, question: Question, session: QuizSession, remaining_time: int):
        """
        Update the question message with remaining time.
        
        Args:
            message: Discord message to update
            question: Current question
            session: Quiz session
            remaining_time: Seconds remaining
        """
        try:
            # Create updated embed
            embed = discord.Embed(
                title=f"🎯 Question {session.current_index + 1}/{len(session.questions)}",
                description=question.text,
                color=0x00ff00 if remaining_time > 3 else 0xff6600 if remaining_time > 1 else 0xff0000
            )
            
            # Update timer display
            timer_emoji = "⏱️" if remaining_time > 3 else "⚠️" if remaining_time > 1 else "🚨"
            embed.add_field(
                name=f"{timer_emoji} Time Remaining",
                value=f"{remaining_time} second{'s' if remaining_time != 1 else ''}",
                inline=True
            )
            
            # Add quiz info
            embed.add_field(
                name="📚 Quiz",
                value=session.quiz_name,
                inline=True
            )
            
            if remaining_time <= 3:
                embed.set_footer(text="⚡ Time running out!")
            else:
                embed.set_footer(text="Answer will be revealed when time expires")
            
            await message.edit(embed=embed)
            
        except discord.HTTPException as e:
            self.logger.error(f"Failed to update timer message: {e}")
    
    async def _reveal_answer(self, message: discord.Message, question: Question, session: QuizSession, channel_id: int):
        """
        Reveal the answer and advance to next question or end quiz.
        
        Args:
            message: Discord message to update
            question: Current question
            session: Quiz session
            channel_id: Discord channel identifier
        """
        try:
            # Step 1: Explicit timer cleanup before proceeding
            self.logger.debug(f"Starting explicit timer cleanup for channel {channel_id}")
            cleanup_success = self.quiz_engine.cancel_timer(str(channel_id))
            if cleanup_success:
                self.logger.debug(f"Timer cleanup successful for channel {channel_id}")
            else:
                self.logger.warning(f"Timer cleanup returned False for channel {channel_id}")
            
            # Create answer reveal embed
            embed = discord.Embed(
                title=f"⏰ Time's Up! - Question {session.current_index + 1}/{len(session.questions)}",
                description=question.text,
                color=0xff0000
            )
            
            embed.add_field(
                name="✅ Correct Answer",
                value=f"**{question.answer}**",
                inline=False
            )
            
            embed.add_field(
                name="📚 Quiz",
                value=session.quiz_name,
                inline=True
            )
            
            # Check if this was the last question
            if session.current_index + 1 >= len(session.questions):
                embed.add_field(
                    name="🎉 Quiz Complete!",
                    value="That was the final question. Great job!",
                    inline=False
                )
                embed.set_footer(text="Quiz completed")
                
                # Mark session as complete
                session.is_active = False
                self.stop_session(channel_id)
            else:
                embed.add_field(
                    name="➡️ Next Question",
                    value="Get ready for the next question in 3 seconds...",
                    inline=False
                )
                embed.set_footer(text="Next question coming up")
            
            await message.edit(embed=embed)
            
            # If not the last question, advance and present next question with proper sequencing
            if session.is_active and self.advance_question(channel_id):
                # Step 2: Brief pause for user experience (3 seconds)
                await asyncio.sleep(3)
                
                # Step 3: Additional delay for timer cleanup completion
                self.logger.debug(f"Adding additional cleanup delay for channel {channel_id}")
                await asyncio.sleep(0.2)  # Increased delay to ensure complete cleanup
                
                # Step 4: Timer readiness verification before starting next question
                if session.is_active and not session.is_paused:
                    self.logger.debug(f"Verifying timer readiness before presenting next question for channel {channel_id}")
                    
                    # Verify timer is ready for new question
                    timer_ready = self.quiz_engine._verify_timer_readiness(str(channel_id))
                    if not timer_ready:
                        self.logger.warning(f"Timer not ready for channel {channel_id}, attempting additional cleanup")
                        # Attempt additional cleanup if timer not ready
                        self.quiz_engine.cancel_timer(str(channel_id))
                        await asyncio.sleep(0.1)  # Brief wait after cleanup
                        
                        # Re-verify readiness
                        timer_ready = self.quiz_engine._verify_timer_readiness(str(channel_id))
                        if not timer_ready:
                            self.logger.error(f"Timer still not ready after additional cleanup for channel {channel_id}")
                    
                    # Present next question with improved error handling
                    if timer_ready:
                        self.logger.debug(f"Timer readiness verified, presenting next question for channel {channel_id}")
                        await self.present_question(channel_id, message.channel)
                    else:
                        self.logger.error(f"Unable to verify timer readiness for channel {channel_id}, stopping quiz")
                        session.is_active = False
                        self.stop_session(channel_id)
                        await message.channel.send("❌ Timer error occurred. Quiz has been stopped.")
            else:
                # Quiz is complete, send completion summary
                await self._send_quiz_completion_summary(channel_id, message.channel)
            
        except discord.HTTPException as e:
            self.logger.error(f"Failed to reveal answer: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in _reveal_answer for channel {channel_id}: {e}")
            # Ensure cleanup on any error
            self.quiz_engine.cancel_timer(str(channel_id))
    
    async def start_quiz_presentation(self, channel_id: int, channel: discord.TextChannel) -> bool:
        """
        Start presenting the quiz questions with timing.
        
        Args:
            channel_id: Discord channel identifier
            channel: Discord channel object
            
        Returns:
            True if quiz presentation started, False otherwise
        """
        session = self.get_session(channel_id)
        
        if session is None or not session.is_active:
            return False
        
        # Present the first question
        message = await self.present_question(channel_id, channel)
        return message is not None
    
    async def _send_quiz_completion_summary(self, channel_id: int, channel: discord.TextChannel):
        """
        Send a completion summary when the quiz ends.
        
        Args:
            channel_id: Discord channel identifier
            channel: Discord channel object
        """
        try:
            completion_info = self.get_quiz_completion_info(channel_id)
            
            if completion_info is None:
                return
            
            # Create completion embed
            embed = discord.Embed(
                title="🎉 Quiz Complete!",
                description=f"**{completion_info['quiz_name']}** has been completed!",
                color=0x00ff00
            )
            
            # Add completion stats
            duration = completion_info['duration']
            embed.add_field(
                name="📊 Final Statistics",
                value=(
                    f"Questions Completed: {completion_info['total_questions']}\n"
                    f"Total Time: {duration['minutes']}m {duration['seconds']}s\n"
                    f"Average per Question: {duration['total_seconds'] // completion_info['total_questions']}s"
                ),
                inline=False
            )
            
            # Add quiz settings used
            settings = completion_info['settings']
            embed.add_field(
                name="⚙️ Quiz Settings",
                value=(
                    f"Order: {'🔀 Random' if settings['random_order'] else '📋 Sequential'}\n"
                    f"Timer: {settings['timer_duration']} seconds per question\n"
                    f"Questions: {settings['question_count'] or 'All available'}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎯 Start Another Quiz",
                value="Use `/start` to begin a new quiz session",
                inline=False
            )
            
            embed.set_footer(text="Thanks for playing!")
            
            await channel.send(embed=embed)
            
        except discord.HTTPException as e:
            self.logger.error(f"Failed to send completion summary: {e}")
        except Exception as e:
            self.logger.error(f"Error in completion summary: {e}")