import sys
sys.path.insert(0, r"d:/Tekwoks_task")
import test_api_extended

try:
    test_api_extended.run_extended_tests()
    print("API tests completed successfully")
except Exception as e:
    print("API tests failed:", e)
    raise
