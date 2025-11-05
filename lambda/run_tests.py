#!/usr/bin/env python3
import unittest
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

_script_dir = os.path.dirname(__file__)

if __name__ == "__main__":
    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover(_script_dir, pattern="test_*.py")
    print(f"Running {suite.countTestCases()} tests...")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)
