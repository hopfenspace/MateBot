"""
MateBot unit tests for the whole API in certain user actions
"""

import unittest


class WorkingAPITests(unittest.TestCase):
    pass


class FailingAPITests(unittest.TestCase):
    pass


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for cls in [WorkingAPITests, FailingAPITests]:
        for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
            suite.addTest(cls(fixture))
    return suite


if __name__ == '__main__':
    unittest.main()
