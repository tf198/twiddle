import unittest
import doctest
from twiddle import views

def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(views))
    return tests
