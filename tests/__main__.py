#!/usr/bin/env python3

"""
Run MateBot core unittests
"""


if __name__ == '__main__':
    import unittest
    from . import get_suite

    class MainProgram(unittest.TestProgram):
        def createTests(self, from_discovery=False, loader=None):
            self.test = get_suite()  # noqa

    MainProgram()
