import unittest, os

if __name__ == "__main__":
    loader = unittest.TestLoader()
    tests_dir = os.path.dirname(__file__)
    suite = loader.discover(tests_dir, pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
