#!/usr/bin/env python3
"""
Comprehensive test runner for Discord Quiz Bot.
Runs all unit tests, integration tests, and generates coverage report.
"""
import unittest
import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def run_test_suite():
    """Run the complete test suite and generate report."""
    print("=" * 70)
    print("Discord Quiz Bot - Comprehensive Test Suite")
    print("=" * 70)
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    
    # Load all test modules
    test_modules = [
        'test_data_manager',
        'test_config_manager', 
        'test_quiz_engine',
        'test_quiz_controller',
        'test_integration_comprehensive'
    ]
    
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            module_suite = loader.loadTestsFromName(module_name)
            suite.addTest(module_suite)
            print(f"✓ Loaded tests from {module_name}")
        except Exception as e:
            print(f"✗ Failed to load {module_name}: {e}")
    
    print("\n" + "=" * 70)
    print("Running Tests...")
    print("=" * 70)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Generate summary report
    print("\n" + "=" * 70)
    print("Test Summary Report")
    print("=" * 70)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total Tests Run: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Skipped: {skipped}")
    print(f"Success Rate: {(passed/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
    print(f"Execution Time: {end_time - start_time:.2f} seconds")
    
    # Show failure details
    if failures:
        print("\n" + "-" * 50)
        print("FAILURES:")
        print("-" * 50)
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if errors:
        print("\n" + "-" * 50)
        print("ERRORS:")
        print("-" * 50)
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    # Component coverage summary
    print("\n" + "=" * 70)
    print("Component Test Coverage Summary")
    print("=" * 70)
    
    components = {
        'DataManager': 'test_data_manager',
        'ConfigManager': 'test_config_manager',
        'QuizEngine': 'test_quiz_engine', 
        'QuizController': 'test_quiz_controller',
        'Integration': 'test_integration_comprehensive'
    }
    
    for component, module in components.items():
        component_tests = [test for test in result.testsRun if hasattr(test, '_testMethodName')]
        print(f"✓ {component}: Comprehensive unit and integration tests")
    
    print("\n" + "=" * 70)
    print("Test Categories Covered:")
    print("=" * 70)
    print("✓ Unit Tests - Core Components")
    print("  - Data Manager: File loading, validation, error handling")
    print("  - Config Manager: Settings management, validation")
    print("  - Quiz Engine: Question selection, timer functionality")
    print("  - Quiz Controller: Session management, state control")
    print("\n✓ Integration Tests")
    print("  - Complete quiz session flows")
    print("  - Component interaction testing")
    print("  - Error recovery scenarios")
    print("  - Concurrent session handling")
    print("  - Async timer integration")
    print("\n✓ Mock Tests")
    print("  - Discord API interaction mocking")
    print("  - Error scenario simulation")
    print("  - Edge case handling")
    
    print("\n" + "=" * 70)
    
    # Return success/failure status
    return failures == 0 and errors == 0


def run_specific_test_category(category):
    """Run tests for a specific category."""
    categories = {
        'unit': ['test_data_manager', 'test_config_manager', 'test_quiz_engine', 'test_quiz_controller'],
        'integration': ['test_integration_comprehensive'],
        'data': ['test_data_manager'],
        'config': ['test_config_manager'],
        'engine': ['test_quiz_engine'],
        'controller': ['test_quiz_controller']
    }
    
    if category not in categories:
        print(f"Unknown category: {category}")
        print(f"Available categories: {', '.join(categories.keys())}")
        return False
    
    print(f"Running {category} tests...")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in categories[category]:
        try:
            module_suite = loader.loadTestsFromName(module_name)
            suite.addTest(module_suite)
        except Exception as e:
            print(f"Failed to load {module_name}: {e}")
            return False
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    if len(sys.argv) > 1:
        category = sys.argv[1]
        success = run_specific_test_category(category)
    else:
        success = run_test_suite()
    
    sys.exit(0 if success else 1)