"""
Data manager for JSON file operations and quiz data validation.
"""
import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import shutil

from .models import Question


class DataManager:
    """Manages loading and validation of JSON quiz files."""
    
    def __init__(self, quiz_directory: str = "./quizzes/"):
        """
        Initialize DataManager with quiz directory path.
        
        Args:
            quiz_directory: Path to directory containing JSON quiz files
        """
        self.quiz_directory = Path(quiz_directory)
        self.loaded_quizzes: Dict[str, List[Question]] = {}
        self.logger = logging.getLogger(__name__)
        self.load_errors: List[str] = []  # Track loading errors for user feedback
        self.fallback_quiz_created = False  # Track if we created a fallback quiz
        
    def load_quiz_files(self) -> Dict[str, List[Question]]:
        """
        Load all JSON files from the quiz directory with comprehensive error handling.
        
        Returns:
            Dictionary mapping quiz names to lists of Question objects
        """
        self.loaded_quizzes.clear()
        self.load_errors.clear()
        self.fallback_quiz_created = False
        
        # Ensure directory exists with proper error handling
        directory_result = self._ensure_quiz_directory()
        if not directory_result['success']:
            self.load_errors.append(directory_result['error'])
            return self._create_fallback_quiz()
        
        # Scan for JSON files with error handling
        scan_result = self._scan_quiz_files()
        if not scan_result['success']:
            self.load_errors.append(scan_result['error'])
            return self._create_fallback_quiz()
        
        json_files = scan_result['files']
        
        # If no files found, create sample quiz and provide guidance
        if not json_files:
            self.logger.warning(f"No JSON files found in {self.quiz_directory}")
            self.load_errors.append(f"No quiz files found in {self.quiz_directory}")
            return self._create_sample_quiz()
        
        # Load each file with individual error handling
        successful_loads = 0
        for json_file in json_files:
            load_result = self._load_quiz_file_safely(json_file)
            if load_result['success']:
                successful_loads += 1
            else:
                self.load_errors.append(f"{json_file.name}: {load_result['error']}")
        
        # If no files loaded successfully, create fallback
        if successful_loads == 0:
            self.logger.error("No quiz files could be loaded successfully")
            self.load_errors.append("All quiz files failed to load")
            return self._create_fallback_quiz()
        
        self.logger.info(f"Successfully loaded {successful_loads} quiz files")
        if self.load_errors:
            self.logger.warning(f"Encountered {len(self.load_errors)} loading errors")
            
        return self.loaded_quizzes
    
    def _load_single_file(self, file_path: Path) -> Optional[dict]:
        """
        Load and parse a single JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Parsed JSON data or None if loading failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if self.validate_quiz_structure(data):
                    return data
                else:
                    self.logger.error(f"Invalid quiz structure in {file_path}")
                    return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            return None
        except FileNotFoundError:
            self.logger.error(f"Quiz file not found: {file_path}")
            return None
        except OSError as e:
            self.logger.error(f"Failed to read quiz file {file_path}: {e}")
            return None
    
    def validate_quiz_structure(self, data: dict) -> bool:
        """
        Validate that JSON data has the correct quiz structure.
        
        Expected structure:
        {
            "quiz": [
                {
                    "question": str,
                    "answer": str,
                    "options": list  # Optional
                }
            ]
        }
        
        Args:
            data: Parsed JSON data to validate
            
        Returns:
            True if structure is valid, False otherwise
        """
        if not isinstance(data, dict):
            self.logger.error("Quiz data must be a JSON object")
            return False
            
        if "quiz" not in data:
            self.logger.error("Quiz data must contain a 'quiz' key")
            return False
            
        quiz_array = data["quiz"]
        if not isinstance(quiz_array, list):
            self.logger.error("'quiz' value must be an array")
            return False
            
        if not quiz_array:
            self.logger.error("Quiz array cannot be empty")
            return False
            
        for i, question_data in enumerate(quiz_array):
            if not isinstance(question_data, dict):
                self.logger.error(f"Question {i} must be an object")
                return False
                
            # Check required fields
            if "question" not in question_data:
                self.logger.error(f"Question {i} missing 'question' field")
                return False
                
            if "answer" not in question_data:
                self.logger.error(f"Question {i} missing 'answer' field")
                return False
                
            # Validate field types
            if not isinstance(question_data["question"], str):
                self.logger.error(f"Question {i} 'question' field must be a string")
                return False
                
            if not isinstance(question_data["answer"], str):
                self.logger.error(f"Question {i} 'answer' field must be a string")
                return False
                
            # Validate optional options field
            if "options" in question_data:
                if not isinstance(question_data["options"], list):
                    self.logger.error(f"Question {i} 'options' field must be an array")
                    return False
                    
        return True
    
    def _parse_questions(self, quiz_data: dict) -> List[Question]:
        """
        Parse validated quiz data into Question objects.
        
        Args:
            quiz_data: Validated quiz data dictionary
            
        Returns:
            List of Question objects
        """
        questions = []
        
        for question_data in quiz_data["quiz"]:
            question = Question(
                text=question_data["question"],
                answer=question_data["answer"],
                options=question_data.get("options", [])
            )
            questions.append(question)
            
        return questions
    
    def get_available_quizzes(self) -> List[str]:
        """
        Get list of available quiz names.
        
        Returns:
            List of quiz names (without file extensions)
        """
        return list(self.loaded_quizzes.keys())
    
    def get_quiz_questions(self, quiz_name: str) -> Optional[List[Question]]:
        """
        Retrieve questions for a specific quiz.
        
        Args:
            quiz_name: Name of the quiz (without file extension)
            
        Returns:
            List of Question objects for the quiz, or None if quiz not found
        """
        return self.loaded_quizzes.get(quiz_name)
    
    def quiz_exists(self, quiz_name: str) -> bool:
        """
        Check if a quiz with the given name exists.
        
        Args:
            quiz_name: Name of the quiz to check
            
        Returns:
            True if quiz exists, False otherwise
        """
        return quiz_name in self.loaded_quizzes
    
    def get_quiz_count(self) -> int:
        """
        Get the total number of loaded quizzes.
        
        Returns:
            Number of loaded quizzes
        """
        return len(self.loaded_quizzes)
    
    def get_question_count(self, quiz_name: str) -> int:
        """
        Get the number of questions in a specific quiz.
        
        Args:
            quiz_name: Name of the quiz
            
        Returns:
            Number of questions in the quiz, or 0 if quiz not found
        """
        questions = self.get_quiz_questions(quiz_name)
        return len(questions) if questions else 0
    
    def _ensure_quiz_directory(self) -> Dict[str, any]:
        """
        Ensure quiz directory exists with comprehensive error handling.
        
        Returns:
            Dictionary with success status and error message if applicable
        """
        try:
            if not self.quiz_directory.exists():
                # Check if parent directory is writable
                parent_dir = self.quiz_directory.parent
                if not parent_dir.exists():
                    try:
                        parent_dir.mkdir(parents=True, exist_ok=True)
                    except PermissionError:
                        return {
                            'success': False,
                            'error': f"Permission denied: Cannot create parent directory {parent_dir}"
                        }
                    except OSError as e:
                        return {
                            'success': False,
                            'error': f"Failed to create parent directory {parent_dir}: {e}"
                        }
                
                # Check if we have write permissions
                if not os.access(parent_dir, os.W_OK):
                    return {
                        'success': False,
                        'error': f"Permission denied: Cannot write to {parent_dir}"
                    }
                
                # Create quiz directory
                self.quiz_directory.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created quiz directory: {self.quiz_directory}")
            
            # Verify directory is accessible
            if not os.access(self.quiz_directory, os.R_OK):
                return {
                    'success': False,
                    'error': f"Permission denied: Cannot read from {self.quiz_directory}"
                }
            
            return {'success': True}
            
        except PermissionError:
            return {
                'success': False,
                'error': f"Permission denied: Cannot access {self.quiz_directory}"
            }
        except OSError as e:
            return {
                'success': False,
                'error': f"System error accessing {self.quiz_directory}: {e}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error with directory {self.quiz_directory}: {e}"
            }
    
    def _scan_quiz_files(self) -> Dict[str, any]:
        """
        Scan quiz directory for JSON files with error handling.
        
        Returns:
            Dictionary with success status, files list, and error message if applicable
        """
        try:
            json_files = list(self.quiz_directory.glob("*.json"))
            return {
                'success': True,
                'files': json_files
            }
        except PermissionError:
            return {
                'success': False,
                'error': f"Permission denied: Cannot read directory {self.quiz_directory}",
                'files': []
            }
        except OSError as e:
            return {
                'success': False,
                'error': f"System error scanning {self.quiz_directory}: {e}",
                'files': []
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error scanning {self.quiz_directory}: {e}",
                'files': []
            }
    
    def _load_quiz_file_safely(self, json_file: Path) -> Dict[str, any]:
        """
        Load a single quiz file with comprehensive error handling.
        
        Args:
            json_file: Path to the JSON file to load
            
        Returns:
            Dictionary with success status and error message if applicable
        """
        try:
            # Check file accessibility
            if not json_file.exists():
                return {
                    'success': False,
                    'error': "File not found"
                }
            
            if not os.access(json_file, os.R_OK):
                return {
                    'success': False,
                    'error': "Permission denied: Cannot read file"
                }
            
            # Check file size (prevent loading extremely large files)
            file_size = json_file.stat().st_size
            max_size = 10 * 1024 * 1024  # 10MB limit
            if file_size > max_size:
                return {
                    'success': False,
                    'error': f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {max_size / 1024 / 1024}MB"
                }
            
            # Load and validate the file
            quiz_data = self._load_single_file(json_file)
            if quiz_data is None:
                return {
                    'success': False,
                    'error': "Invalid JSON structure or validation failed"
                }
            
            # Parse questions
            questions = self._parse_questions(quiz_data)
            if not questions:
                return {
                    'success': False,
                    'error': "No valid questions found in file"
                }
            
            # Store the loaded quiz
            quiz_name = json_file.stem
            self.loaded_quizzes[quiz_name] = questions
            self.logger.info(f"Loaded quiz '{quiz_name}' with {len(questions)} questions")
            
            return {'success': True}
            
        except PermissionError:
            return {
                'success': False,
                'error': "Permission denied"
            }
        except OSError as e:
            return {
                'success': False,
                'error': f"System error: {e}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error: {e}"
            }
    
    def _create_sample_quiz(self) -> Dict[str, List[Question]]:
        """
        Create a sample quiz file when no quiz files are found.
        
        Returns:
            Dictionary with the sample quiz loaded
        """
        try:
            sample_quiz_data = {
                "quiz": [
                    {
                        "question": "What is the capital of France?",
                        "answer": "Paris"
                    },
                    {
                        "question": "What is 2 + 2?",
                        "answer": "4"
                    },
                    {
                        "question": "What programming language is this bot written in?",
                        "answer": "Python"
                    }
                ]
            }
            
            sample_file_path = self.quiz_directory / "sample_quiz.json"
            
            # Only create if it doesn't exist
            if not sample_file_path.exists():
                with open(sample_file_path, 'w', encoding='utf-8') as f:
                    json.dump(sample_quiz_data, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Created sample quiz file: {sample_file_path}")
            
            # Load the sample quiz
            questions = [
                Question(text=q["question"], answer=q["answer"])
                for q in sample_quiz_data["quiz"]
            ]
            
            self.loaded_quizzes["sample_quiz"] = questions
            self.logger.info("Loaded sample quiz with 3 questions")
            
            return self.loaded_quizzes
            
        except Exception as e:
            self.logger.error(f"Failed to create sample quiz: {e}")
            self.load_errors.append(f"Failed to create sample quiz: {e}")
            return self._create_fallback_quiz()
    
    def _create_fallback_quiz(self) -> Dict[str, List[Question]]:
        """
        Create a minimal fallback quiz in memory when all file operations fail.
        
        Returns:
            Dictionary with the fallback quiz loaded
        """
        try:
            fallback_questions = [
                Question(
                    text="This is a fallback question. What should you do when quiz files can't be loaded?",
                    answer="Check the quiz directory and file permissions"
                )
            ]
            
            self.loaded_quizzes["fallback_quiz"] = fallback_questions
            self.fallback_quiz_created = True
            self.logger.warning("Created fallback quiz due to file loading failures")
            
            return self.loaded_quizzes
            
        except Exception as e:
            self.logger.critical(f"Failed to create fallback quiz: {e}")
            # Return empty dict as last resort
            return {}
    
    def get_load_errors(self) -> List[str]:
        """
        Get list of errors encountered during the last load operation.
        
        Returns:
            List of error messages
        """
        return self.load_errors.copy()
    
    def has_load_errors(self) -> bool:
        """
        Check if there were any errors during the last load operation.
        
        Returns:
            True if there were loading errors, False otherwise
        """
        return len(self.load_errors) > 0
    
    def is_fallback_quiz_active(self) -> bool:
        """
        Check if the fallback quiz was created due to loading failures.
        
        Returns:
            True if fallback quiz is active, False otherwise
        """
        return self.fallback_quiz_created
    
    def get_loading_summary(self) -> Dict[str, any]:
        """
        Get a comprehensive summary of the loading operation.
        
        Returns:
            Dictionary with loading statistics and status
        """
        return {
            'total_quizzes': len(self.loaded_quizzes),
            'has_errors': self.has_load_errors(),
            'error_count': len(self.load_errors),
            'errors': self.get_load_errors(),
            'fallback_active': self.is_fallback_quiz_active(),
            'quiz_directory': str(self.quiz_directory),
            'available_quizzes': list(self.loaded_quizzes.keys())
        }