from unittest import TestCase

from twiddle.containers import EventList
from twiddle.views import TrackView, Boundary
from twiddle.objects import Note, Event, TimeRange

class BoundaryTest(TestCase):

    def test_bar_at(self):
        b = Boundary(6, 60, 12, 4)

        self.assertEqual(b.bar_at(60), 6)
        self.assertEqual(b.bar_at(71), 6)
        self.assertEqual(b.bar_at(72), 7)

    def test_is_bar_break(self):
        b = Boundary(6, 60, 12, 4)
        
        self.assertTrue(b.is_bar_break(60))
        self.assertTrue(b.is_bar_break(72))
        self.assertFalse(b.is_bar_break(61))
        self.assertFalse(b.is_bar_break(71))

    def test_get_rests(self):
        b = Boundary(3, 48, 24, 4)
        
        def rest_output(tick, length):
            context = {'resolution': 6}
            return " ".join(( x.to_lily(context) for x in b.get_rests(tick, length) ))

        self.assertEqual(rest_output(54, 6), "r4")
        self.assertEqual(rest_output(54, 48), "r4 r2 | R1 | r4")
        self.assertEqual(rest_output(54, 96), "r4 r2 | R1*3 | r4")
        self.assertEqual(rest_output(51, 48), "r8 r4 r2 | R1 | r8")

    def test_split_note(self):
        b = Boundary(3, 48, 24, 4)

        def note_output(start, length, pitch=57):
            context = {'resolution': 6}
            e = Event(TimeRange(start, start+length), Note(pitch, ()))
            return " ".join(( x.to_lily(context) for x in b.split_note(e) ))

        self.assertEqual(note_output(54, 6), "a4")
        self.assertEqual(note_output(54, 24), "a2.~ | a4")
        self.assertEqual(note_output(48, 24), "a1 |")
        self.assertEqual(note_output(48, 96), "a1~ | a1~ | a1~ | a1 |")
        self.assertEqual(note_output(78, 6), "a4")
        self.assertEqual(note_output(90, 6), "a4 |")
        

class TrackViewTest(TestCase):

    def test_set_meter(self):
        c = TrackView(3)
        self.assertEqual(c._boundaries, [(1, 0, 12, 4)])

        c = TrackView(3, meter=(3, 4), partial=1)
        c.set_meter(3, (4, 4))
        self.assertEqual(c._boundaries, [(1, 3, 9, 3), (3, 21, 12, 4)])

    def test_beat(self):

        c = TrackView(3) # 12 ticks per bar
        # [(bar=1, tick=0, length=12, divisions=4)]
        # use tick + length * ((n-bar) + (division-1) /divisions)

        self.assertEqual(c.beat(4), 36)
        # 0 + 12 * (4 - 1 + 0)

        self.assertEqual(c.beat(4, 1), 36)
        # 0 + 12 * (3 + 0)
        self.assertEqual(c.beat(4, 2), 39)
        # 0 + 12 * (3 + (1/4))

        c = TrackView(3, partial=2)
        # [(bar=1, tick=6, length=12, divisions=4)]
        self.assertEqual(c.beat(1), 6)
        # 6 + 12 * (1-1)
        self.assertEqual(c.beat(0, 4), 3)
        # 6 + 12 * (-1 + 3/4)
        self.assertEqual(c.beat(4), 42)

        c = TrackView(3, meter=(3, 4), partial=1)
        # [(bar=0, tick=0, length=9, divisions=3)]
        self.assertEqual(c.beat(1), 3)
        self.assertEqual(c.beat(3), 21)

        c.set_meter(3, (4, 4))
        self.assertEqual(c.beat(3), 21)
        self.assertEqual(c.beat(4), 33)
        self.assertEqual(c.beat(4, 4), 42)

    def test_keys(self):
        c = TrackView(3)
        self.assertEqual(c.key(12), 0)

        c = TrackView(3, key='D')
        c.set_meter(3, (3,4))
        c.set_key(3, 'F')
        
        self.assertEqual(c.key(2), 2)
        self.assertEqual(c.key(3), -1)

    def test_bar(self):
        c = TrackView(3)

        self.assertEqual(c.bar(3), (24, 36))

    def test_bars(self):
        c = TrackView(3)
        self.assertEqual(c.bars(3, 4), (24, 48))

    def test_get_range(self):
        c = TrackView(3)
        self.assertEqual(c.get_range((3, 2), (5, 1)), (27, 48))

    def test_bar_info(self):
        c = TrackView(1, meter=(3, 4))
        c.set_meter(3, meter=(2, 4))
        c.set_meter(4, meter=(3, 4))

        self.assertEqual(c.beat(3), 6)
        self.assertEqual(c.bar_info(0), (1, 0, 3, 3))
        self.assertEqual(c.bar_info(5), (1, 0, 3, 3))
        self.assertEqual(c.bar_info(6), (3, 6, 2, 2))

        self.assertEqual(c.beat(4), 8)
        self.assertEqual(c.bar_info(7), (3, 6, 2, 2))
        self.assertEqual(c.bar_info(8), (4, 8, 3, 3))

        self.assertEqual(c.bar_info(1000), (4, 8, 3, 3))

    def test_split_sections(self):
        c = TrackView(1, meter=(3, 4))
        c.set_meter(3, meter=(2, 4))
        c.set_meter(4, meter=(3, 4))

        c.split_sections(EventList(time=TimeRange(0, 10), resolution=1))
