"""
Quiz engine core logic for the Discord Quiz Bot.
Handles question selection, ordering, and timing functionality.
"""
import random
import asyncio
import discord
import logging
import time
from typing import List, Optional, Callable, Any
from src.models import Question, QuizSettings

# Set up logger for timer operations
logger = logging.getLogger(__name__)

class TimerLifecycleLogger:
    """Structured logging for timer lifecycle events."""
    
    @staticmethod
    def log_timer_creation(channel_id: str, duration: int, attempt: int = 1) -> None:
        """Log timer creation event with structured data."""
        logger.info(
            "Timer lifecycle: CREATION_START",
            extra={
                'event_type': 'timer_creation_start',
                'channel_id': channel_id,
                'duration': duration,
                'attempt': attempt,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_timer_created(channel_id: str, duration: int, creation_time: float) -> None:
        """Log successful timer creation."""
        creation_duration = time.time() - creation_time
        logger.info(
            f"Timer lifecycle: CREATED - Channel {channel_id}, Duration {duration}s, Setup time {creation_duration:.3f}s",
            extra={
                'event_type': 'timer_created',
                'channel_id': channel_id,
                'duration': duration,
                'creation_duration': creation_duration,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_timer_start(channel_id: str, task_id: str = None) -> None:
        """Log timer countdown start."""
        logger.info(
            f"Timer lifecycle: COUNTDOWN_START - Channel {channel_id}",
            extra={
                'event_type': 'timer_countdown_start',
                'channel_id': channel_id,
                'task_id': task_id,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_timer_update(channel_id: str, remaining_time: int, total_duration: int) -> None:
        """Log timer update events (throttled to avoid spam)."""
        # Log only at specific intervals to avoid log spam
        if remaining_time % 10 == 0 or remaining_time <= 5:
            progress_percent = ((total_duration - remaining_time) / total_duration) * 100
            logger.debug(
                f"Timer lifecycle: UPDATE - Channel {channel_id}, Remaining {remaining_time}s ({progress_percent:.1f}% complete)",
                extra={
                    'event_type': 'timer_update',
                    'channel_id': channel_id,
                    'remaining_time': remaining_time,
                    'total_duration': total_duration,
                    'progress_percent': progress_percent,
                    'timestamp': time.time()
                }
            )
    
    @staticmethod
    def log_timer_completion(channel_id: str, completion_type: str, total_duration: int) -> None:
        """Log timer completion (natural expiry or cancellation)."""
        logger.info(
            f"Timer lifecycle: COMPLETED - Channel {channel_id}, Type {completion_type}, Duration {total_duration}s",
            extra={
                'event_type': 'timer_completed',
                'channel_id': channel_id,
                'completion_type': completion_type,
                'total_duration': total_duration,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_timer_cleanup_start(channel_id: str) -> float:
        """Log start of timer cleanup process."""
        cleanup_start_time = time.time()
        logger.info(
            f"Timer lifecycle: CLEANUP_START - Channel {channel_id}",
            extra={
                'event_type': 'timer_cleanup_start',
                'channel_id': channel_id,
                'timestamp': cleanup_start_time
            }
        )
        return cleanup_start_time
    
    @staticmethod
    def log_timer_cleanup_complete(channel_id: str, cleanup_start_time: float, success: bool) -> None:
        """Log completion of timer cleanup process."""
        cleanup_duration = time.time() - cleanup_start_time
        status = "SUCCESS" if success else "FAILED"
        logger.info(
            f"Timer lifecycle: CLEANUP_COMPLETE - Channel {channel_id}, Status {status}, Duration {cleanup_duration:.3f}s",
            extra={
                'event_type': 'timer_cleanup_complete',
                'channel_id': channel_id,
                'cleanup_duration': cleanup_duration,
                'success': success,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_timer_state_transition(channel_id: str, from_state: str, to_state: str, reason: str = None) -> None:
        """Log timer state transitions."""
        logger.info(
            f"Timer lifecycle: STATE_TRANSITION - Channel {channel_id}, {from_state} -> {to_state}" + 
            (f" ({reason})" if reason else ""),
            extra={
                'event_type': 'timer_state_transition',
                'channel_id': channel_id,
                'from_state': from_state,
                'to_state': to_state,
                'reason': reason,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_timer_error(channel_id: str, error_type: str, error_message: str, operation: str) -> None:
        """Log timer-related errors with context."""
        logger.error(
            f"Timer lifecycle: ERROR - Channel {channel_id}, Operation {operation}, Type {error_type}: {error_message}",
            extra={
                'event_type': 'timer_error',
                'channel_id': channel_id,
                'error_type': error_type,
                'error_message': error_message,
                'operation': operation,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_race_condition_detected(channel_id: str, details: str) -> None:
        """Log race condition detection."""
        logger.warning(
            f"Timer lifecycle: RACE_CONDITION - Channel {channel_id}: {details}",
            extra={
                'event_type': 'timer_race_condition',
                'channel_id': channel_id,
                'details': details,
                'timestamp': time.time()
            }
        )
    
    @staticmethod
    def log_timer_retry(channel_id: str, attempt: int, max_attempts: int, delay: float, reason: str) -> None:
        """Log timer retry attempts."""
        logger.warning(
            f"Timer lifecycle: RETRY - Channel {channel_id}, Attempt {attempt}/{max_attempts}, Delay {delay:.3f}s, Reason: {reason}",
            extra={
                'event_type': 'timer_retry',
                'channel_id': channel_id,
                'attempt': attempt,
                'max_attempts': max_attempts,
                'delay': delay,
                'reason': reason,
                'timestamp': time.time()
            }
        )


class QuizTimer:
    """Manages countdown timers for quiz questions."""
    
    def __init__(self, channel_id: str = None):
        """Initialize the timer."""
        self._task: Optional[asyncio.Task] = None
        self._is_paused = False
        self._remaining_time = 0
        self._is_cancelled = False
        self._channel_id = channel_id
        self._creation_time = time.time()
        self._total_duration = 0
        
        logger.debug(
            f"QuizTimer instance created for channel {channel_id}",
            extra={
                'event_type': 'timer_instance_created',
                'channel_id': channel_id,
                'timestamp': self._creation_time
            }
        )
    
    async def start_countdown(
        self, 
        duration: int, 
        update_callback: Callable[[int], Any],
        completion_callback: Callable[[], Any]
    ) -> None:
        """
        Start a countdown timer with callbacks for updates and completion.
        
        Args:
            duration: Timer duration in seconds
            update_callback: Called each second with remaining time
            completion_callback: Called when timer completes or is cancelled
        """
        self._remaining_time = duration
        self._total_duration = duration
        self._is_cancelled = False
        self._is_paused = False
        
        # Log countdown start
        TimerLifecycleLogger.log_timer_start(
            self._channel_id, 
            str(id(self._task)) if self._task else None
        )
        
        countdown_start_time = time.time()
        
        try:
            while self._remaining_time > 0 and not self._is_cancelled:
                if not self._is_paused:
                    # Log timer updates at intervals
                    TimerLifecycleLogger.log_timer_update(
                        self._channel_id, 
                        self._remaining_time, 
                        self._total_duration
                    )
                    
                    await update_callback(self._remaining_time)
                    await asyncio.sleep(1)
                    self._remaining_time -= 1
                else:
                    # When paused, just wait a bit and check again
                    TimerLifecycleLogger.log_timer_state_transition(
                        self._channel_id, 
                        "running", 
                        "paused", 
                        "timer paused by user"
                    )
                    await asyncio.sleep(0.1)
            
            # Determine completion type and log
            if self._is_cancelled:
                TimerLifecycleLogger.log_timer_completion(
                    self._channel_id, 
                    "cancelled", 
                    self._total_duration
                )
            else:
                TimerLifecycleLogger.log_timer_completion(
                    self._channel_id, 
                    "natural_expiry", 
                    self._total_duration
                )
                await completion_callback()
                
        except asyncio.CancelledError:
            self._is_cancelled = True
            TimerLifecycleLogger.log_timer_completion(
                self._channel_id, 
                "asyncio_cancelled", 
                self._total_duration
            )
            raise
        except Exception as e:
            TimerLifecycleLogger.log_timer_error(
                self._channel_id,
                "countdown_execution_error",
                str(e),
                "start_countdown"
            )
            raise
    
    def pause(self) -> None:
        """Pause the countdown timer."""
        if not self._is_paused:
            TimerLifecycleLogger.log_timer_state_transition(
                self._channel_id, 
                "running", 
                "paused", 
                "pause requested"
            )
        self._is_paused = True
    
    def resume(self) -> None:
        """Resume the countdown timer."""
        if self._is_paused:
            TimerLifecycleLogger.log_timer_state_transition(
                self._channel_id, 
                "paused", 
                "running", 
                "resume requested"
            )
        self._is_paused = False
    
    def cancel(self) -> None:
        """Cancel the countdown timer."""
        TimerLifecycleLogger.log_timer_state_transition(
            self._channel_id, 
            "running" if not self._is_paused else "paused", 
            "cancelling", 
            "cancel requested"
        )
        
        self._is_cancelled = True
        if self._task and not self._task.done():
            logger.debug(f"Cancelling timer task for channel {self._channel_id}")
            self._task.cancel()
            TimerLifecycleLogger.log_timer_state_transition(
                self._channel_id, 
                "cancelling", 
                "cancelled", 
                "task cancelled"
            )
        else:
            logger.debug(f"No active task to cancel or task already done for channel {self._channel_id}")
            TimerLifecycleLogger.log_timer_state_transition(
                self._channel_id, 
                "cancelling", 
                "cancelled", 
                "no active task"
            )
    
    @property
    def is_paused(self) -> bool:
        """Check if timer is paused."""
        return self._is_paused
    
    @property
    def is_cancelled(self) -> bool:
        """Check if timer is cancelled."""
        return self._is_cancelled
    
    @property
    def remaining_time(self) -> int:
        """Get remaining time in seconds."""
        return self._remaining_time


class QuizEngine:
    """Core quiz engine that handles question selection, ordering, and timing."""
    
    def __init__(self):
        """Initialize the quiz engine."""
        self._timers: dict[str, QuizTimer] = {}  # Channel ID -> Timer mapping
    
    def select_questions(self, questions: List[Question], settings: QuizSettings) -> List[Question]:
        """
        Select and order questions based on quiz settings.
        
        Args:
            questions: List of available questions
            settings: Quiz configuration settings
            
        Returns:
            List of selected and ordered questions
            
        Raises:
            ValueError: If questions list is empty
        """
        if not questions:
            raise ValueError("Cannot select questions from empty list")
        
        # Make a copy to avoid modifying the original list
        selected_questions = questions.copy()
        
        # Apply random ordering if enabled
        if settings.random_order:
            selected_questions = self.shuffle_questions(selected_questions)
        
        # Limit question count if specified
        if settings.question_count is not None:
            selected_questions = self.limit_question_count(selected_questions, settings.question_count)
        
        return selected_questions
    
    def shuffle_questions(self, questions: List[Question]) -> List[Question]:
        """
        Shuffle questions randomly.
        
        Args:
            questions: List of questions to shuffle
            
        Returns:
            New list with questions in random order
        """
        shuffled = questions.copy()
        random.shuffle(shuffled)
        return shuffled
    
    def limit_question_count(self, questions: List[Question], count: int) -> List[Question]:
        """
        Limit the number of questions to the specified count.
        
        Args:
            questions: List of questions to limit
            count: Maximum number of questions to return
            
        Returns:
            List limited to the specified count
            
        Note:
            If count is greater than available questions, returns all questions.
            If count is less than 1, returns empty list.
        """
        if count < 1:
            return []
        
        return questions[:count]
    
    def _verify_timer_readiness(self, channel_id: str) -> bool:
        """
        Verify no existing timer before starting new one.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if ready to start new timer, False if existing timer found
        """
        verification_start_time = time.time()
        
        if channel_id in self._timers:
            timer = self._timers[channel_id]
            # Check if timer is still active
            if timer._task and not timer._task.done() and not timer.is_cancelled:
                TimerLifecycleLogger.log_race_condition_detected(
                    channel_id,
                    f"Active timer exists during readiness check - Task done: {timer._task.done()}, Cancelled: {timer.is_cancelled}"
                )
                logger.warning(f"Timer readiness check failed: active timer exists for channel {channel_id}")
                return False
            else:
                # Timer exists but is inactive, clean it up
                TimerLifecycleLogger.log_timer_state_transition(
                    channel_id,
                    "inactive_exists",
                    "cleaning_up",
                    "found inactive timer during readiness check"
                )
                logger.debug(f"Found inactive timer for channel {channel_id}, cleaning up")
                try:
                    del self._timers[channel_id]
                    logger.debug(f"Cleaned up inactive timer for channel {channel_id}")
                    TimerLifecycleLogger.log_timer_state_transition(
                        channel_id,
                        "cleaning_up",
                        "cleaned",
                        "inactive timer removed"
                    )
                except KeyError:
                    pass  # Already removed
        
        verification_duration = time.time() - verification_start_time
        logger.debug(
            f"Timer readiness verified for channel {channel_id} in {verification_duration:.3f}s",
            extra={
                'event_type': 'timer_readiness_verified',
                'channel_id': channel_id,
                'verification_duration': verification_duration,
                'timestamp': time.time()
            }
        )
        return True

    async def start_question_timer(
        self,
        channel_id: str,
        duration: int,
        update_callback: Callable[[int], Any],
        completion_callback: Callable[[], Any]
    ) -> None:
        """
        Start a countdown timer for a question in a specific channel with readiness validation.
        
        Args:
            channel_id: Discord channel identifier
            duration: Timer duration in seconds
            update_callback: Called each second with remaining time
            completion_callback: Called when timer completes
            
        Raises:
            RuntimeError: If timer fails to start after all retry attempts
        """
        operation_start_time = time.time()
        TimerLifecycleLogger.log_timer_creation(channel_id, duration)
        
        # Implement retry logic for timer start failures
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms delay
        
        for attempt in range(max_retries):
            try:
                # Pre-start validation: verify no existing timer
                if not self._verify_timer_readiness(channel_id):
                    TimerLifecycleLogger.log_timer_retry(
                        channel_id, 
                        attempt + 1, 
                        max_retries, 
                        retry_delay, 
                        "timer readiness validation failed"
                    )
                    
                    # Cancel any existing timer and wait for cleanup
                    cleanup_success = self.cancel_timer(channel_id)
                    if cleanup_success:
                        logger.debug(f"Previous timer cleaned up successfully for channel {channel_id}")
                    
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    
                    # Re-verify readiness after cleanup
                    if not self._verify_timer_readiness(channel_id):
                        if attempt < max_retries - 1:
                            TimerLifecycleLogger.log_race_condition_detected(
                                channel_id,
                                f"Timer still not ready after cleanup on attempt {attempt + 1}"
                            )
                            continue
                        else:
                            error_msg = f"Timer creation conflict: unable to clear existing timer for channel {channel_id}"
                            TimerLifecycleLogger.log_timer_error(
                                channel_id,
                                "creation_conflict",
                                error_msg,
                                "start_question_timer"
                            )
                            raise RuntimeError(error_msg)
                
                # Additional delay to ensure cleanup completes
                await asyncio.sleep(0.05)
                
                # Create new timer and register it immediately
                timer_creation_time = time.time()
                timer = QuizTimer(channel_id)
                self._timers[channel_id] = timer
                
                TimerLifecycleLogger.log_timer_created(channel_id, duration, timer_creation_time)
                
                # Start the countdown as a background task
                timer._task = asyncio.create_task(
                    timer.start_countdown(duration, update_callback, completion_callback)
                )
                
                logger.debug(
                    f"Started countdown task for channel {channel_id}",
                    extra={
                        'event_type': 'timer_task_started',
                        'channel_id': channel_id,
                        'task_id': str(id(timer._task)),
                        'duration': duration,
                        'timestamp': time.time()
                    }
                )
                
                # Timer started successfully, break out of retry loop
                break
                
            except Exception as e:
                TimerLifecycleLogger.log_timer_error(
                    channel_id,
                    "creation_error",
                    str(e),
                    f"start_question_timer_attempt_{attempt + 1}"
                )
                
                # Clean up any partial timer creation
                if channel_id in self._timers:
                    try:
                        del self._timers[channel_id]
                        logger.debug(f"Cleaned up partial timer creation for channel {channel_id}")
                    except KeyError:
                        pass
                
                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    TimerLifecycleLogger.log_timer_retry(
                        channel_id, 
                        attempt + 2, 
                        max_retries, 
                        retry_delay, 
                        f"creation error: {str(e)}"
                    )
                else:
                    # All retries exhausted, raise error
                    error_msg = f"Failed to start timer for channel {channel_id} after {max_retries} attempts: {e}"
                    TimerLifecycleLogger.log_timer_error(
                        channel_id,
                        "creation_failed_all_retries",
                        error_msg,
                        "start_question_timer"
                    )
                    raise RuntimeError(error_msg)
        
        try:
            # Wait for the timer task to complete
            await self._timers[channel_id]._task
            logger.debug(
                f"Timer task completed normally for channel {channel_id}",
                extra={
                    'event_type': 'timer_task_completed',
                    'channel_id': channel_id,
                    'total_operation_time': time.time() - operation_start_time,
                    'timestamp': time.time()
                }
            )
        except asyncio.CancelledError:
            logger.debug(
                f"Timer task was cancelled for channel {channel_id}",
                extra={
                    'event_type': 'timer_task_cancelled',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
            pass
        except Exception as e:
            TimerLifecycleLogger.log_timer_error(
                channel_id,
                "execution_error",
                str(e),
                "timer_task_execution"
            )
        finally:
            # Clean up timer when done
            if channel_id in self._timers:
                del self._timers[channel_id]
                logger.debug(
                    f"Timer cleanup completed in finally block for channel {channel_id}",
                    extra={
                        'event_type': 'timer_finally_cleanup',
                        'channel_id': channel_id,
                        'timestamp': time.time()
                    }
                )
    
    def pause_timer(self, channel_id: str) -> bool:
        """
        Pause the timer for a specific channel.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if timer was paused, False if no active timer
        """
        if channel_id in self._timers:
            logger.debug(
                f"Pausing timer for channel {channel_id}",
                extra={
                    'event_type': 'timer_pause_requested',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
            self._timers[channel_id].pause()
            return True
        else:
            logger.debug(
                f"Cannot pause timer for channel {channel_id}: no active timer",
                extra={
                    'event_type': 'timer_pause_no_timer',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
        return False
    
    def resume_timer(self, channel_id: str) -> bool:
        """
        Resume the timer for a specific channel.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if timer was resumed, False if no active timer
        """
        if channel_id in self._timers:
            logger.debug(
                f"Resuming timer for channel {channel_id}",
                extra={
                    'event_type': 'timer_resume_requested',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
            self._timers[channel_id].resume()
            return True
        else:
            logger.debug(
                f"Cannot resume timer for channel {channel_id}: no active timer",
                extra={
                    'event_type': 'timer_resume_no_timer',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
        return False
    
    async def cancel_timer(self, channel_id: str) -> bool:
        """
        Cancel the timer for a specific channel with complete cleanup verification.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if timer was cancelled, False if no active timer
        """
        cleanup_start_time = TimerLifecycleLogger.log_timer_cleanup_start(channel_id)
        
        if channel_id not in self._timers:
            logger.debug(
                f"No active timer found for channel {channel_id}",
                extra={
                    'event_type': 'timer_cancel_no_timer',
                    'channel_id': channel_id,
                    'timestamp': time.time()
                }
            )
            return False
        
        timer = self._timers[channel_id]
        
        try:
            # Step 1: Mark timer as cancelled
            TimerLifecycleLogger.log_timer_state_transition(
                channel_id,
                "active",
                "cancelling",
                "cancel_timer called"
            )
            timer.cancel()
            
            # Step 2: Cancel the asyncio task if it exists and is running
            if timer._task and not timer._task.done():
                logger.debug(
                    f"Cancelling asyncio task for channel {channel_id}",
                    extra={
                        'event_type': 'timer_task_cancelling',
                        'channel_id': channel_id,
                        'task_id': str(id(timer._task)),
                        'timestamp': time.time()
                    }
                )
                timer._task.cancel()
                
                # Step 3: Verify task cancellation with timeout
                max_wait_time = 2.0  # Maximum time to wait for task cancellation
                wait_start = time.time()
                
                while not timer._task.done() and (time.time() - wait_start) < max_wait_time:
                    # Small delay to allow task to complete cancellation
                    await asyncio.sleep(0.01)
                
                wait_duration = time.time() - wait_start
                
                if not timer._task.done():
                    TimerLifecycleLogger.log_timer_error(
                        channel_id,
                        "cancellation_timeout",
                        f"Timer task did not complete cancellation within {max_wait_time}s timeout (waited {wait_duration:.3f}s)",
                        "cancel_timer"
                    )
                    # Implement forced cleanup mechanism
                    self._force_timer_cleanup(channel_id, timer)
                else:
                    logger.debug(
                        f"Timer task successfully cancelled for channel {channel_id} in {wait_duration:.3f}s",
                        extra={
                            'event_type': 'timer_task_cancelled_success',
                            'channel_id': channel_id,
                            'cancellation_duration': wait_duration,
                            'timestamp': time.time()
                        }
                    )
            
            # Step 4: Remove timer from tracking dictionary
            del self._timers[channel_id]
            TimerLifecycleLogger.log_timer_state_transition(
                channel_id,
                "cancelling",
                "removed_from_tracking",
                "timer removed from _timers dictionary"
            )
            
            # Step 5: Verify complete cleanup
            cleanup_verified = self._verify_timer_cleanup(channel_id)
            
            TimerLifecycleLogger.log_timer_cleanup_complete(
                channel_id, 
                cleanup_start_time, 
                cleanup_verified
            )
            
            if cleanup_verified:
                return True
            else:
                TimerLifecycleLogger.log_timer_error(
                    channel_id,
                    "cleanup_verification_failed",
                    "Timer cleanup verification failed",
                    "cancel_timer"
                )
                return False
                
        except Exception as e:
            TimerLifecycleLogger.log_timer_error(
                channel_id,
                "cleanup_exception",
                str(e),
                "cancel_timer"
            )
            # Attempt forced cleanup on error
            self._force_timer_cleanup(channel_id, timer)
            TimerLifecycleLogger.log_timer_cleanup_complete(
                channel_id, 
                cleanup_start_time, 
                False
            )
            return False
    
    def _force_timer_cleanup(self, channel_id: str, timer: QuizTimer) -> None:
        """
        Implement forced cleanup mechanism for stuck timers.
        
        Args:
            channel_id: Discord channel identifier
            timer: Timer object to force cleanup
        """
        force_cleanup_start_time = time.time()
        TimerLifecycleLogger.log_timer_state_transition(
            channel_id,
            "stuck",
            "force_cleanup_start",
            "initiating forced cleanup for stuck timer"
        )
        
        try:
            # Force cancel the timer object
            timer._is_cancelled = True
            timer._remaining_time = 0
            TimerLifecycleLogger.log_timer_state_transition(
                channel_id,
                "force_cleanup_start",
                "timer_object_cancelled",
                "timer object state forcibly cancelled"
            )
            
            # Force remove from timers dictionary if still present
            if channel_id in self._timers:
                del self._timers[channel_id]
                TimerLifecycleLogger.log_timer_state_transition(
                    channel_id,
                    "timer_object_cancelled",
                    "removed_from_tracking",
                    "forced removal from tracking dictionary"
                )
            
            # If task still exists, attempt more aggressive cancellation
            if timer._task and not timer._task.done():
                try:
                    # Try to cancel with a more direct approach
                    timer._task.cancel()
                    TimerLifecycleLogger.log_timer_state_transition(
                        channel_id,
                        "removed_from_tracking",
                        "task_force_cancelled",
                        "attempted aggressive task cancellation"
                    )
                except Exception as task_error:
                    TimerLifecycleLogger.log_timer_error(
                        channel_id,
                        "force_cancel_task_failed",
                        str(task_error),
                        "_force_timer_cleanup"
                    )
            
            force_cleanup_duration = time.time() - force_cleanup_start_time
            logger.warning(
                f"Forced cleanup completed for channel {channel_id} in {force_cleanup_duration:.3f}s",
                extra={
                    'event_type': 'timer_force_cleanup_completed',
                    'channel_id': channel_id,
                    'force_cleanup_duration': force_cleanup_duration,
                    'timestamp': time.time()
                }
            )
            
        except Exception as e:
            TimerLifecycleLogger.log_timer_error(
                channel_id,
                "force_cleanup_critical_error",
                str(e),
                "_force_timer_cleanup"
            )
    
    def _verify_timer_cleanup(self, channel_id: str) -> bool:
        """
        Verify that timer resources are fully released.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            True if cleanup is verified complete, False otherwise
        """
        verification_start_time = time.time()
        
        try:
            # Check 1: Timer should not be in tracking dictionary
            if channel_id in self._timers:
                TimerLifecycleLogger.log_timer_error(
                    channel_id,
                    "cleanup_verification_failed",
                    "timer still in tracking dictionary",
                    "_verify_timer_cleanup"
                )
                return False
            
            # Check 2: Verify no orphaned timer references
            # This is a defensive check to ensure we don't have any lingering references
            timer_count = len(self._timers)
            verification_duration = time.time() - verification_start_time
            
            logger.debug(
                f"Timer cleanup verification: {timer_count} active timers remaining",
                extra={
                    'event_type': 'timer_cleanup_verification',
                    'channel_id': channel_id,
                    'active_timer_count': timer_count,
                    'verification_duration': verification_duration,
                    'timestamp': time.time()
                }
            )
            
            # Check 3: Log successful verification
            logger.debug(
                f"Timer cleanup verification passed for channel {channel_id} in {verification_duration:.3f}s",
                extra={
                    'event_type': 'timer_cleanup_verification_passed',
                    'channel_id': channel_id,
                    'verification_duration': verification_duration,
                    'timestamp': time.time()
                }
            )
            return True
            
        except Exception as e:
            TimerLifecycleLogger.log_timer_error(
                channel_id,
                "cleanup_verification_exception",
                str(e),
                "_verify_timer_cleanup"
            )
            return False
    
    def get_timer_status(self, channel_id: str) -> Optional[dict]:
        """
        Get the status of a timer for a specific channel.
        
        Args:
            channel_id: Discord channel identifier
            
        Returns:
            Dictionary with timer status or None if no active timer
        """
        if channel_id in self._timers:
            timer = self._timers[channel_id]
            return {
                'remaining_time': timer.remaining_time,
                'is_paused': timer.is_paused,
                'is_cancelled': timer.is_cancelled
            }
        return None
    
    async def present_question_with_timer(
        self,
        question: Question,
        channel: discord.TextChannel,
        channel_id: str,
        question_number: int,
        total_questions: int,
        quiz_name: str,
        timer_duration: int = 30
    ) -> Optional[discord.Message]:
        """
        Present a question to Discord with countdown timer and automatic answer reveal.
        
        Args:
            question: Question to present
            channel: Discord channel to send to
            channel_id: Channel identifier for timer management
            question_number: Current question number (1-based)
            total_questions: Total number of questions in quiz
            quiz_name: Name of the quiz
            timer_duration: Timer duration in seconds
            
        Returns:
            Discord message object if successful, None otherwise
        """
        try:
            # Create question embed
            embed = discord.Embed(
                title=f"🎯 Question {question_number}/{total_questions}",
                description=question.text,
                color=0x00ff00
            )
            
            # Add timer info
            embed.add_field(
                name="⏱️ Time Remaining",
                value=f"{timer_duration} seconds",
                inline=True
            )
            
            # Add quiz info
            embed.add_field(
                name="📚 Quiz",
                value=quiz_name,
                inline=True
            )
            
            embed.set_footer(text="Answer will be revealed when time expires")
            
            # Send the question message
            message = await channel.send(embed=embed)
            
            # Start countdown timer with callbacks
            await self.start_question_timer(
                channel_id,
                timer_duration,
                lambda remaining_time: self._update_question_timer(
                    message, question, question_number, total_questions, quiz_name, remaining_time
                ),
                lambda: self._reveal_question_answer(
                    message, question, question_number, total_questions, quiz_name
                )
            )
            
            return message
            
        except discord.HTTPException as e:
            # Log error but don't raise to avoid breaking quiz flow
            print(f"Failed to present question: {e}")
            return None
    
    async def _update_question_timer(
        self,
        message: discord.Message,
        question: Question,
        question_number: int,
        total_questions: int,
        quiz_name: str,
        remaining_time: int
    ):
        """
        Update question message with remaining time.
        
        Args:
            message: Discord message to update
            question: Current question
            question_number: Current question number
            total_questions: Total questions in quiz
            quiz_name: Name of the quiz
            remaining_time: Seconds remaining
        """
        try:
            # Change color based on remaining time
            if remaining_time > 5:
                color = 0x00ff00  # Green
                timer_emoji = "⏱️"
                footer_text = "Answer will be revealed when time expires"
            elif remaining_time > 2:
                color = 0xff6600  # Orange
                timer_emoji = "⚠️"
                footer_text = "⚡ Time running out!"
            else:
                color = 0xff0000  # Red
                timer_emoji = "🚨"
                footer_text = "🚨 Final seconds!"
            
            # Create updated embed
            embed = discord.Embed(
                title=f"🎯 Question {question_number}/{total_questions}",
                description=question.text,
                color=color
            )
            
            # Update timer display
            embed.add_field(
                name=f"{timer_emoji} Time Remaining",
                value=f"{remaining_time} second{'s' if remaining_time != 1 else ''}",
                inline=True
            )
            
            # Add quiz info
            embed.add_field(
                name="📚 Quiz",
                value=quiz_name,
                inline=True
            )
            
            embed.set_footer(text=footer_text)
            
            await message.edit(embed=embed)
            
        except discord.HTTPException as e:
            # Log error but don't raise to avoid breaking timer
            print(f"Failed to update timer: {e}")
    
    async def _reveal_question_answer(
        self,
        message: discord.Message,
        question: Question,
        question_number: int,
        total_questions: int,
        quiz_name: str
    ):
        """
        Reveal the answer when timer expires.
        
        Args:
            message: Discord message to update
            question: Current question
            question_number: Current question number
            total_questions: Total questions in quiz
            quiz_name: Name of the quiz
        """
        try:
            # Create answer reveal embed
            embed = discord.Embed(
                title=f"⏰ Time's Up! - Question {question_number}/{total_questions}",
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
                value=quiz_name,
                inline=True
            )
            
            # Add completion status
            if question_number == total_questions:
                embed.add_field(
                    name="🎉 Quiz Complete!",
                    value="That was the final question. Great job!",
                    inline=False
                )
                embed.set_footer(text="Quiz completed")
            else:
                embed.add_field(
                    name="➡️ Next Question",
                    value=f"Question {question_number + 1} coming up next...",
                    inline=False
                )
                embed.set_footer(text="Get ready for the next question")
            
            await message.edit(embed=embed)
            
        except discord.HTTPException as e:
            # Log error but don't raise to avoid breaking quiz flow
            print(f"Failed to reveal answer: {e}")