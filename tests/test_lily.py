from unittest import TestCase

from twiddle import lily

class LilyTest(TestCase):

    def test_duration(self):

        TESTS = (
            (96, '4'),
            (48, '8'),
            (24, '16'),
            (96+48, '4.'),
            (48+24, '8.'),
            (24+12, '16.'),
            (96+48+24, '4..'),
            (48+24+12, '8..'),
            (24+12+6, '16..'),
        )

        for d, expected in TESTS:
            self.assertEqual(lily.duration_to_length(d, 96), expected)
