"""
Unit tests for DataManager class.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, Mock

from src.data_manager import DataManager
from src.models import Question
from tests.test_fixtures import TestFixtures, ErrorScenarios, TestDataValidation


class TestDataManager(unittest.TestCase):
    """Test cases for DataManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_manager = DataManager(self.temp_dir)
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_creates_directory_if_not_exists(self):
        """Test that DataManager creates quiz directory if it doesn't exist."""
        non_existent_dir = os.path.join(self.temp_dir, "new_quiz_dir")
        dm = DataManager(non_existent_dir)
        
        # Load quiz files should create the directory
        dm.load_quiz_files()
        
        self.assertTrue(Path(non_existent_dir).exists())
    
    def test_validate_quiz_structure_valid_data(self):
        """Test validation with valid quiz structure."""
        valid_data = {
            "quiz": [
                {
                    "question": "What is 2+2?",
                    "answer": "4"
                },
                {
                    "question": "What is the capital of France?",
                    "answer": "Paris",
                    "options": ["London", "Berlin", "Paris", "Madrid"]
                }
            ]
        }
        
        self.assertTrue(self.data_manager.validate_quiz_structure(valid_data))
    
    def test_validate_quiz_structure_missing_quiz_key(self):
        """Test validation fails when 'quiz' key is missing."""
        invalid_data = {
            "questions": [
                {"question": "Test?", "answer": "Test"}
            ]
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data))
    
    def test_validate_quiz_structure_quiz_not_array(self):
        """Test validation fails when 'quiz' value is not an array."""
        invalid_data = {
            "quiz": "not an array"
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data))
    
    def test_validate_quiz_structure_empty_quiz_array(self):
        """Test validation fails when quiz array is empty."""
        invalid_data = {
            "quiz": []
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data))
    
    def test_validate_quiz_structure_missing_question_field(self):
        """Test validation fails when question field is missing."""
        invalid_data = {
            "quiz": [
                {
                    "answer": "Test answer"
                }
            ]
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data))
    
    def test_validate_quiz_structure_missing_answer_field(self):
        """Test validation fails when answer field is missing."""
        invalid_data = {
            "quiz": [
                {
                    "question": "Test question?"
                }
            ]
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data))
    
    def test_validate_quiz_structure_invalid_field_types(self):
        """Test validation fails with invalid field types."""
        invalid_data = {
            "quiz": [
                {
                    "question": 123,  # Should be string
                    "answer": "Test answer"
                }
            ]
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data))
        
        invalid_data2 = {
            "quiz": [
                {
                    "question": "Test question?",
                    "answer": 456  # Should be string
                }
            ]
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data2))
    
    def test_validate_quiz_structure_invalid_options_type(self):
        """Test validation fails when options field is not an array."""
        invalid_data = {
            "quiz": [
                {
                    "question": "Test question?",
                    "answer": "Test answer",
                    "options": "not an array"
                }
            ]
        }
        
        self.assertFalse(self.data_manager.validate_quiz_structure(invalid_data))
    
    def test_load_quiz_files_valid_json(self):
        """Test loading valid JSON quiz files."""
        # Create a valid quiz file
        quiz_data = {
            "quiz": [
                {
                    "question": "What is 2+2?",
                    "answer": "4"
                },
                {
                    "question": "What is the capital of France?",
                    "answer": "Paris",
                    "options": ["London", "Berlin", "Paris", "Madrid"]
                }
            ]
        }
        
        quiz_file = Path(self.temp_dir) / "test_quiz.json"
        with open(quiz_file, 'w') as f:
            json.dump(quiz_data, f)
        
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        self.assertIn("test_quiz", loaded_quizzes)
        self.assertEqual(len(loaded_quizzes["test_quiz"]), 2)
        
        # Check first question
        q1 = loaded_quizzes["test_quiz"][0]
        self.assertEqual(q1.text, "What is 2+2?")
        self.assertEqual(q1.answer, "4")
        self.assertEqual(q1.options, [])
        
        # Check second question
        q2 = loaded_quizzes["test_quiz"][1]
        self.assertEqual(q2.text, "What is the capital of France?")
        self.assertEqual(q2.answer, "Paris")
        self.assertEqual(q2.options, ["London", "Berlin", "Paris", "Madrid"])
    
    def test_load_quiz_files_invalid_json(self):
        """Test handling of invalid JSON files."""
        # Create an invalid JSON file
        quiz_file = Path(self.temp_dir) / "invalid_quiz.json"
        with open(quiz_file, 'w') as f:
            f.write("{ invalid json }")
        
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        # Should not contain the invalid quiz
        self.assertNotIn("invalid_quiz", loaded_quizzes)
        # Should create fallback quiz when all files fail to load
        self.assertEqual(len(loaded_quizzes), 1)
        self.assertIn("fallback_quiz", loaded_quizzes)
    
    def test_load_quiz_files_invalid_structure(self):
        """Test handling of JSON files with invalid quiz structure."""
        # Create a JSON file with invalid structure
        invalid_data = {
            "questions": [  # Wrong key, should be "quiz"
                {"question": "Test?", "answer": "Test"}
            ]
        }
        
        quiz_file = Path(self.temp_dir) / "invalid_structure.json"
        with open(quiz_file, 'w') as f:
            json.dump(invalid_data, f)
        
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        # Should not contain the invalid quiz
        self.assertNotIn("invalid_structure", loaded_quizzes)
        # Should create fallback quiz when all files fail to load
        self.assertEqual(len(loaded_quizzes), 1)
        self.assertIn("fallback_quiz", loaded_quizzes)
    
    def test_load_quiz_files_mixed_valid_invalid(self):
        """Test loading mix of valid and invalid files."""
        # Create valid quiz file
        valid_data = {
            "quiz": [
                {"question": "Valid question?", "answer": "Valid answer"}
            ]
        }
        valid_file = Path(self.temp_dir) / "valid_quiz.json"
        with open(valid_file, 'w') as f:
            json.dump(valid_data, f)
        
        # Create invalid quiz file
        invalid_file = Path(self.temp_dir) / "invalid_quiz.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
        
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        # Should only contain the valid quiz
        self.assertIn("valid_quiz", loaded_quizzes)
        self.assertNotIn("invalid_quiz", loaded_quizzes)
        self.assertEqual(len(loaded_quizzes), 1)
    
    def test_load_quiz_files_no_json_files(self):
        """Test behavior when no JSON files exist in directory."""
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        # Should create sample quiz when no files exist
        self.assertEqual(len(loaded_quizzes), 1)
        self.assertIn("sample_quiz", loaded_quizzes)
    
    def test_load_single_file_file_not_found(self):
        """Test handling of missing files."""
        non_existent_file = Path(self.temp_dir) / "missing.json"
        
        result = self.data_manager._load_single_file(non_existent_file)
        
        self.assertIsNone(result)
    
    def test_parse_questions(self):
        """Test parsing of validated quiz data into Question objects."""
        quiz_data = {
            "quiz": [
                {
                    "question": "Test question 1?",
                    "answer": "Answer 1"
                },
                {
                    "question": "Test question 2?",
                    "answer": "Answer 2",
                    "options": ["A", "B", "C"]
                }
            ]
        }
        
        questions = self.data_manager._parse_questions(quiz_data)
        
        self.assertEqual(len(questions), 2)
        
        # Check first question
        self.assertEqual(questions[0].text, "Test question 1?")
        self.assertEqual(questions[0].answer, "Answer 1")
        self.assertEqual(questions[0].options, [])
        
        # Check second question
        self.assertEqual(questions[1].text, "Test question 2?")
        self.assertEqual(questions[1].answer, "Answer 2")
        self.assertEqual(questions[1].options, ["A", "B", "C"])


    def test_get_available_quizzes_empty(self):
        """Test getting available quizzes when none are loaded."""
        available = self.data_manager.get_available_quizzes()
        
        self.assertEqual(available, [])
    
    def test_get_available_quizzes_with_loaded_quizzes(self):
        """Test getting available quizzes when quizzes are loaded."""
        # Create multiple quiz files
        quiz1_data = {
            "quiz": [
                {"question": "Question 1?", "answer": "Answer 1"}
            ]
        }
        quiz2_data = {
            "quiz": [
                {"question": "Question 2?", "answer": "Answer 2"}
            ]
        }
        
        quiz1_file = Path(self.temp_dir) / "math_quiz.json"
        quiz2_file = Path(self.temp_dir) / "history_quiz.json"
        
        with open(quiz1_file, 'w') as f:
            json.dump(quiz1_data, f)
        with open(quiz2_file, 'w') as f:
            json.dump(quiz2_data, f)
        
        self.data_manager.load_quiz_files()
        available = self.data_manager.get_available_quizzes()
        
        self.assertEqual(len(available), 2)
        self.assertIn("math_quiz", available)
        self.assertIn("history_quiz", available)
    
    def test_get_quiz_questions_existing_quiz(self):
        """Test retrieving questions for an existing quiz."""
        # Create a quiz file
        quiz_data = {
            "quiz": [
                {"question": "What is 2+2?", "answer": "4"},
                {"question": "What is 3+3?", "answer": "6"}
            ]
        }
        
        quiz_file = Path(self.temp_dir) / "math_quiz.json"
        with open(quiz_file, 'w') as f:
            json.dump(quiz_data, f)
        
        self.data_manager.load_quiz_files()
        questions = self.data_manager.get_quiz_questions("math_quiz")
        
        self.assertIsNotNone(questions)
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].text, "What is 2+2?")
        self.assertEqual(questions[0].answer, "4")
        self.assertEqual(questions[1].text, "What is 3+3?")
        self.assertEqual(questions[1].answer, "6")
    
    def test_get_quiz_questions_nonexistent_quiz(self):
        """Test retrieving questions for a non-existent quiz."""
        questions = self.data_manager.get_quiz_questions("nonexistent_quiz")
        
        self.assertIsNone(questions)
    
    def test_quiz_exists_true(self):
        """Test quiz_exists returns True for existing quiz."""
        # Create a quiz file
        quiz_data = {
            "quiz": [
                {"question": "Test question?", "answer": "Test answer"}
            ]
        }
        
        quiz_file = Path(self.temp_dir) / "test_quiz.json"
        with open(quiz_file, 'w') as f:
            json.dump(quiz_data, f)
        
        self.data_manager.load_quiz_files()
        
        self.assertTrue(self.data_manager.quiz_exists("test_quiz"))
    
    def test_quiz_exists_false(self):
        """Test quiz_exists returns False for non-existent quiz."""
        self.assertFalse(self.data_manager.quiz_exists("nonexistent_quiz"))
    
    def test_get_quiz_count_empty(self):
        """Test getting quiz count when no quizzes are loaded."""
        count = self.data_manager.get_quiz_count()
        
        self.assertEqual(count, 0)
    
    def test_get_quiz_count_with_quizzes(self):
        """Test getting quiz count when quizzes are loaded."""
        # Create multiple quiz files
        for i in range(3):
            quiz_data = {
                "quiz": [
                    {"question": f"Question {i}?", "answer": f"Answer {i}"}
                ]
            }
            
            quiz_file = Path(self.temp_dir) / f"quiz_{i}.json"
            with open(quiz_file, 'w') as f:
                json.dump(quiz_data, f)
        
        self.data_manager.load_quiz_files()
        count = self.data_manager.get_quiz_count()
        
        self.assertEqual(count, 3)
    
    def test_get_question_count_existing_quiz(self):
        """Test getting question count for existing quiz."""
        # Create a quiz file with multiple questions
        quiz_data = {
            "quiz": [
                {"question": "Question 1?", "answer": "Answer 1"},
                {"question": "Question 2?", "answer": "Answer 2"},
                {"question": "Question 3?", "answer": "Answer 3"}
            ]
        }
        
        quiz_file = Path(self.temp_dir) / "test_quiz.json"
        with open(quiz_file, 'w') as f:
            json.dump(quiz_data, f)
        
        self.data_manager.load_quiz_files()
        count = self.data_manager.get_question_count("test_quiz")
        
        self.assertEqual(count, 3)
    
    def test_get_question_count_nonexistent_quiz(self):
        """Test getting question count for non-existent quiz."""
        count = self.data_manager.get_question_count("nonexistent_quiz")
        
        self.assertEqual(count, 0)
    
    def test_directory_scanning_filters_json_only(self):
        """Test that directory scanning only processes JSON files."""
        # Create JSON file
        quiz_data = {
            "quiz": [
                {"question": "Valid question?", "answer": "Valid answer"}
            ]
        }
        json_file = Path(self.temp_dir) / "valid_quiz.json"
        with open(json_file, 'w') as f:
            json.dump(quiz_data, f)
        
        # Create non-JSON files
        txt_file = Path(self.temp_dir) / "not_a_quiz.txt"
        with open(txt_file, 'w') as f:
            f.write("This is not a quiz file")
        
        py_file = Path(self.temp_dir) / "script.py"
        with open(py_file, 'w') as f:
            f.write("print('Hello world')")
        
        self.data_manager.load_quiz_files()
        available = self.data_manager.get_available_quizzes()
        
        # Should only contain the JSON file
        self.assertEqual(len(available), 1)
        self.assertIn("valid_quiz", available)
        self.assertNotIn("not_a_quiz", available)
        self.assertNotIn("script", available)


    def test_error_handling_comprehensive(self):
        """Test comprehensive error handling scenarios."""
        # Test file system errors
        for error in ErrorScenarios.get_file_system_errors():
            with patch('builtins.open', side_effect=error):
                result = self.data_manager._load_single_file(Path("test.json"))
                self.assertIsNone(result)
    
    def test_fallback_quiz_functionality(self):
        """Test fallback quiz when no valid files exist."""
        # Load with no files - should create sample quiz, not fallback
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        # Should create sample quiz when no files exist
        self.assertIn("sample_quiz", loaded_quizzes)
        self.assertFalse(self.data_manager.is_fallback_quiz_active())
        
        # Verify sample quiz structure
        sample_questions = loaded_quizzes["sample_quiz"]
        self.assertGreater(len(sample_questions), 0)
        for question in sample_questions:
            self.assertTrue(TestDataValidation.validate_question(question))
    
    def test_loading_summary_comprehensive(self):
        """Test comprehensive loading summary functionality."""
        # Create mixed valid/invalid files
        TestFixtures.create_temp_quiz_files(self.temp_dir)
        
        # Load files
        self.data_manager.load_quiz_files()
        
        # Get loading summary
        summary = self.data_manager.get_loading_summary()
        
        # Verify summary structure
        required_keys = ['total_quizzes', 'error_count', 
                        'available_quizzes', 'errors', 'has_errors', 'fallback_active']
        for key in required_keys:
            self.assertIn(key, summary)
        
        # Verify data types
        self.assertIsInstance(summary['total_quizzes'], int)
        self.assertIsInstance(summary['error_count'], int)
        self.assertIsInstance(summary['available_quizzes'], list)
        self.assertIsInstance(summary['errors'], list)
        self.assertIsInstance(summary['has_errors'], bool)
        self.assertIsInstance(summary['fallback_active'], bool)
    
    def test_load_errors_tracking(self):
        """Test error tracking functionality."""
        # Create invalid files
        invalid_file = Path(self.temp_dir) / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
        
        # Load files
        self.data_manager.load_quiz_files()
        
        # Check error tracking
        self.assertTrue(self.data_manager.has_load_errors())
        errors = self.data_manager.get_load_errors()
        self.assertGreater(len(errors), 0)
        self.assertIsInstance(errors[0], str)
    
    def test_concurrent_loading_safety(self):
        """Test thread safety of loading operations."""
        import threading
        import time
        
        # Create test files
        TestFixtures.create_temp_quiz_files(self.temp_dir)
        
        results = []
        errors = []
        
        def load_worker():
            try:
                result = self.data_manager.load_quiz_files()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=load_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0)
        self.assertGreater(len(results), 0)
    
    def test_memory_efficiency_large_files(self):
        """Test memory efficiency with large quiz files."""
        # Create large quiz file
        large_quiz = {
            "quiz": [
                {
                    "question": f"Question {i}?",
                    "answer": f"Answer {i}"
                }
                for i in range(1000)  # Large number of questions
            ]
        }
        
        large_file = Path(self.temp_dir) / "large_quiz.json"
        with open(large_file, 'w') as f:
            json.dump(large_quiz, f)
        
        # Load and verify
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        self.assertIn("large_quiz", loaded_quizzes)
        self.assertEqual(len(loaded_quizzes["large_quiz"]), 1000)
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        unicode_quiz = {
            "quiz": [
                {
                    "question": "What is 'café' in English? 🤔",
                    "answer": "coffee ☕"
                },
                {
                    "question": "¿Cómo estás?",
                    "answer": "How are you?",
                    "options": ["Hola", "Adiós", "How are you?", "Gracias"]
                }
            ]
        }
        
        unicode_file = Path(self.temp_dir) / "unicode_quiz.json"
        with open(unicode_file, 'w', encoding='utf-8') as f:
            json.dump(unicode_quiz, f, ensure_ascii=False)
        
        # Load and verify
        loaded_quizzes = self.data_manager.load_quiz_files()
        
        self.assertIn("unicode_quiz", loaded_quizzes)
        questions = loaded_quizzes["unicode_quiz"]
        self.assertEqual(questions[0].text, "What is 'café' in English? 🤔")
        self.assertEqual(questions[0].answer, "coffee ☕")


if __name__ == '__main__':
    unittest.main()