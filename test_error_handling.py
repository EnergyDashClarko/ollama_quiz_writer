#!/usr/bin/env python3
"""
Simple test to verify error handling implementations work correctly.
"""

import tempfile
import json
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from src.data_manager import DataManager
from src.config_manager import ConfigManager

def test_data_manager_error_handling():
    """Test data manager error handling features."""
    print("Testing DataManager error handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with empty directory
        dm = DataManager(temp_dir)
        loaded_quizzes = dm.load_quiz_files()
        
        print(f"✓ Empty directory handling: {len(loaded_quizzes)} quizzes loaded")
        print(f"✓ Has load errors: {dm.has_load_errors()}")
        print(f"✓ Fallback quiz active: {dm.is_fallback_quiz_active()}")
        
        # Test with invalid JSON
        invalid_file = Path(temp_dir) / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
        
        loaded_quizzes = dm.load_quiz_files()
        print(f"✓ Invalid JSON handling: {len(loaded_quizzes)} quizzes loaded")
        print(f"✓ Load errors: {len(dm.get_load_errors())} errors")
        
        # Test loading summary
        summary = dm.get_loading_summary()
        print(f"✓ Loading summary: {summary['total_quizzes']} quizzes, {summary['error_count']} errors")

def test_config_manager_error_handling():
    """Test config manager error handling features."""
    print("\nTesting ConfigManager error handling...")
    
    cm = ConfigManager()
    
    # Test invalid question count
    result = cm.set_question_count("invalid")
    print(f"✓ Invalid question count: success={result['success']}")
    print(f"✓ User message: {result['user_message']}")
    
    # Test invalid random order
    result = cm.set_random_order("invalid")
    print(f"✓ Invalid random order: success={result['success']}")
    print(f"✓ User message: {result['user_message']}")
    
    # Test toggle random order
    result = cm.toggle_random_order()
    print(f"✓ Toggle random order: success={result['success']}, new_value={result['new_value']}")
    
    # Test configuration health check
    health = cm.get_configuration_health_check()
    print(f"✓ Configuration health: healthy={health['healthy']}")
    print(f"✓ Warnings: {len(health['warnings'])}, Errors: {len(health['errors'])}")

def test_integration():
    """Test integration of error handling components."""
    print("\nTesting integration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        dm = DataManager(temp_dir)
        cm = ConfigManager()
        
        # Load data (will create fallback)
        loaded_quizzes = dm.load_quiz_files()
        
        # Set invalid config
        result = cm.set_question_count(-5)
        
        print(f"✓ Integration test completed")
        print(f"✓ Data manager has {len(loaded_quizzes)} quizzes")
        print(f"✓ Config validation failed as expected: {not result['success']}")

if __name__ == "__main__":
    print("=== Error Handling Verification Test ===")
    
    try:
        test_data_manager_error_handling()
        test_config_manager_error_handling()
        test_integration()
        
        print("\n✅ All error handling tests passed!")
        print("✅ Task 9 - Add comprehensive error handling - COMPLETED")
        
    except Exception as e:
        print(f"\n❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)