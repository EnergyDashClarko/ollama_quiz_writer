"""
Core data models for the Discord Quiz Bot.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Question:
    """Represents a single quiz question."""
    text: str
    answer: str
    options: List[str] = field(default_factory=list)


@dataclass
class QuizSettings:
    """Configuration settings for a quiz session."""
    question_count: Optional[int] = None
    random_order: bool = False
    timer_duration: int = 30


@dataclass
class QuizSession:
    """Represents an active quiz session in a Discord channel."""
    channel_id: int
    quiz_name: str
    questions: List[Question]
    current_index: int
    is_paused: bool
    is_active: bool
    settings: QuizSettings
    start_time: datetime