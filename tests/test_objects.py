from unittest import TestCase
from twiddle.objects import *

class TimeRangeTest(TestCase):

    def test_ticks(self):
        self.assertEqual(TimeRange(398, 476).ticks, 78)

    def test_union(self):

        self.assertEqual(TimeRange(10, 20) & TimeRange(30, 40), (10, 40))
        self.assertEqual(TimeRange(-1, -1) & TimeRange(10, 20), (10, 20))

    def test_intersection(self):

        self.assertEqual(TimeRange(10, 20) | TimeRange(5, 15), (10, 15))

    def test_intersects(self):
        t = TimeRange(10, 20)

        self.assertFalse(t.intersects(TimeRange(0, 5)))
        self.assertFalse(t.intersects(TimeRange(5, 10)))
        self.assertTrue(t.intersects(TimeRange(5, 15)))
        self.assertTrue(t.intersects(TimeRange(10, 15)))
        self.assertTrue(t.intersects(TimeRange(15, 20)))
        self.assertTrue(t.intersects(TimeRange(15, 25)))
        self.assertFalse(t.intersects(TimeRange(20, 30)))

        self.assertFalse(TimeRange(20, 20).intersects(TimeRange(20, 30)))
        self.assertTrue(TimeRange(20, 30).intersects(TimeRange(20, 20)))

    def test_contains(self):
        window = TimeRange(10, 20)

        self.assertTrue(window.contains(TimeRange(15, 16)))
    
    def test_multiply(self):
        t = TimeRange(12, 24) # beats 2-3 at resolution 12

        self.assertEqual(t * 2, (24, 48)) # at resolution 24
        self.assertEqual(t * (9, 12), (9, 18)) # at resolution 9

    def test_add(self):
        t = TimeRange(12, 24)
        self.assertEqual(t + 6, (18, 30))

    def test_subtract(self):
        t = TimeRange(12, 24)
        self.assertEqual(t - 3, (9, 21))

class EventTest(TestCase):

    def test_attr(self):
        note = Event(TimeRange(10, 20), Note(64, ('!', )))
        self.assertEqual(note.to_lily({'resolution': 10}), "e'4!")

    def test_shift(self):
        e1 = Event(TimeRange(10, 20), "A")
        e2 = e1.shift(15)
        self.assertEqual(e1.time, (10, 20)) 
        self.assertEqual(e2.time, (25, 35))

class ObjectTest(TestCase):

    def test_keysignature(self):
        self.assertEqual(KeySignature(0).to_lily(), r'\key c \major')
        self.assertEqual(KeySignature(1).to_lily(), r'\key g \major')
        self.assertEqual(KeySignature(0, True).to_lily(), r'\key a \minor')

    def test_event_to_lily(self):
        e = Event(TimeRange(0, 1), KeySignature(0))
        self.assertEqual(e.to_lily(), r'\key c \major')
