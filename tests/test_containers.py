from unittest import TestCase

from twiddle.containers import EventList, VoiceList, SequenceError
from twiddle.objects import TimeRange, Event, Note
from twiddle.generators import from_string, from_tuples, sequence_builder, notes_from_tuples
from twiddle.views import TrackView

class EventListTest(TestCase):

    TEST_EVENTS = [Event(TimeRange(10, 20), Note(1, ())), Event(TimeRange(20, 30), Note(2, ()))]

    def test_init(self):
        c = EventList()
        self.assertEqual(c.time, (-1, -1))
        self.assertEqual(c.time.ticks, 0)

        c = EventList(self.TEST_EVENTS)
        self.assertEqual(c.time, (10, 30))

        c = EventList(self.TEST_EVENTS, TimeRange(5, 40))
        self.assertEqual(c.time, (5, 40))

    def test_append(self):
        c = EventList(time=TimeRange(10,10))
        c.append(Event(TimeRange(20, 30), 1))
        self.assertEqual(c.time, (10, 30))

        c.append(Event(TimeRange(30, 40), 2))
        self.assertEqual(c.time, (10, 40))

        self.assertTrue(c.is_sequential)

        # can add overlapping
        c.append(Event(TimeRange(35, 45), 3))
        self.assertEqual(c.time, (10, 45))

        # can add out of order
        c.append(Event(TimeRange(5, 15), 4))
        self.assertEqual(c.time, (5, 45))

        self.assertFalse(c.is_sequential)

        # should have sorted
        self.assertEqual([ x.time.start for x in c ], [5, 20, 30, 35])

    def test_insert(self):
        c = EventList([Event(TimeRange(10, 20), 1), Event(TimeRange(30, 40), 2)], TimeRange(5, 40))

        c.insert(Event(TimeRange(5, 15), 3))
        self.assertEqual([ x.item for x in c ], [3, 1, 2])

    def test_extend(self):
        c = EventList()

        c.extend([Event(TimeRange(10, 20), 1), Event(TimeRange(30, 40), 2)])
        self.assertEqual(c.time, (10, 40))

        # iterators
        c = EventList()
        c.extend(( x for x in self.TEST_EVENTS ))
        self.assertEqual(c.time, (10, 30))

        # generators

        def f():
            for e in self.TEST_EVENTS:
                yield e

        c = EventList()
        c.extend(f())
        self.assertEqual(c.time, (10, 30))

    def test_paste(self):
        c = EventList(self.TEST_EVENTS)
        self.assertEqual(c.time, (10, 30))
        
        c.paste(EventList(self.TEST_EVENTS))
        self.assertEqual(c.time, (10, 50))
        #self.assertEqual(c.render_section(), ['1-10', '2-10', '1-10', '2-10'])
        self.assertEqual([ x.time.start for x in c ], [10, 20, 30, 40])

        c.paste(EventList(self.TEST_EVENTS), 10)
        self.assertEqual(c.time, (10, 80))
        self.assertEqual([ x.time.start for x in c ], [10, 20, 30, 40, 60, 70])

        c = from_string('A-2 Bb-1 R-1 D-1')
        c.append(from_string('D-1 E-1 R-2 G-1', start=c.time.stop))

        self.assertEqual(c.time.stop, 10)

        c.paste(from_string('A-6 R-1 D-3'))
        self.assertEqual(c.time.stop, 20)

    def test_get(self):
        c = EventList(self.TEST_EVENTS)
        self.assertEqual(c.get(TimeRange(15, 25)).items(), [])
        self.assertEqual(repr(c.get(TimeRange(15, 40))),
                "[<2 (20,30)>](15,40)")

        c.add_event(20, "FOO")
        self.assertEqual(repr(c.get(TimeRange(10, 20))),
                "[<1 (10,20)>](10,20)")

    def test_slice(self):
        c = EventList(self.TEST_EVENTS)
        c.add_event(20, "FOO")
        self.assertEqual(repr(c.slice(TimeRange(15, 25))),
                "[<1 (15,20)>, <'FOO' (20)>, <2~ (20,25)>](15,25)")
        self.assertEqual(repr(c.slice(TimeRange(20, 25))),
                "[<'FOO' (20)>, <2~ (20,25)>](20,25)")
        self.assertEqual(repr(c.slice(TimeRange(15, 20))),
                "[<1 (15,20)>](15,20)")


    def test_lily_context(self):
        part = from_string('A-2 Bb-1 C-1 D-2 E-1 F-2 G-1 A-2')
        self.assertEqual(part.to_lily(), "a2 ais4 c4 d2 e4 f2 g4 a2")

        view = TrackView(resolution=part.resolution, meter=(4, 4))
        context = {'bar_info': view.bar_info(0)}

        self.assertEqual(part.to_lily(context), "a2 ais4 c4 | d2 e4 f4~ | f4 g4 a2 |")

    def test_lily_layout(self):
        part = from_string('A-2 Bb-1 R-1 D-2 E-1 R-2 G-1 A-6 R-1 D-3')
        view = TrackView(resolution=part.resolution, meter=(4, 4))

        self.assertEqual(part.render_section(view.bar_info(0), {'resolution': part.resolution}), 
                "a2 ais4 r4 | d2 e4 r4 | r4 g4 a2~ | a1 | r4 d2. |")

    def test_nested_layout(self):
        track = from_string('A-2 Bb-1 R-1 D-1')
        track.append(from_string('D-1 E-1 R-2 G-1', start=track.time.stop))

        self.assertEqual(track.time.stop, 10)
        self.assertEqual(track.render_section(), 'a2 ais4 r4 | d4 d4 e4 r4 | r4 g4')
        
        #track.paste(from_string('A-6 R-1 D-3'))

        #print(repr(track))
        #print(track.render_section())

        

class VoiceListTest(TestCase):
    
    def setUp(self):
        self.parts = VoiceList()
        self.parts['One'] = from_string('A-10 B-10 C-10 D-10', 10)
        self.parts['Two'] = from_string('E-10 F-20 G-10', 10)

    def test_setup(self):
        self.assertEqual(self.parts['One'].duration, self.parts['Two'].duration)

    def test_get(self):
        s = self.parts.get(TimeRange(15, 40))
        self.assertEqual(s['One'].to_lily(), "c4 d4")
        self.assertEqual(s['Two'].to_lily(), "g4")

    def test_slice(self):
        s = self.parts.slice(TimeRange(15, 35))
        self.assertEqual(s['One'].to_lily(), "b8 c4 d8~")


"""
class SequentialContainerTest(TestCase):

    def test_append(self):

        c = SequentialContainer(start=10)
        c.append(NoteEvent(20, 30, 1))
        self.assertEqual(c.start, 10)
        self.assertEqual(c.duration, 20)

        c.append(NoteEvent(30, 40, 2))
        self.assertEqual(c.duration, 30)

        self.assertTrue(c.is_sequential())

        # cant add overlapping
        with self.assertRaises(SequenceError):
            c.append(NoteEvent(35, 45, 3))

        # cant add out of order
        with self.assertRaises(SequenceError):
            c.append(NoteEvent(5, 15, 4))

        self.assertTrue(c.is_sequential())

    def test_insert(self):
        c = SequentialContainer([NoteEvent(10, 20, 1), NoteEvent(30, 40, 2)], 5, 40)
        self.assertEqual(c.duration, 35)

        c.insert(NoteEvent(20, 30, 3))

        c.insert(NoteEvent(5, 10, 4))
        self.assertEqual(c.start, 5)
        self.assertEqual(c.duration, 35)

        c.insert(NoteEvent(0, 5, 5))
        self.assertEqual(c.start, 0)
        self.assertEqual(c.duration, 40)

        c.insert(NoteEvent(45, 55, 6))
        self.assertEqual(c.duration, 55)

        with self.assertRaises(SequenceError):
            c.insert(NoteEvent(0, 5, 7))

        with self.assertRaises(SequenceError):
            c.insert(NoteEvent(50, 60, 8))

class SimultaneousContainerTest(TestCase):

    TEST_NOTES = (
      (0, 10, 'A'),
      (0, 10, 'A'),
      (10, 20, 'B'),
      (15, 40, 'C'),
      (30, 50, 'D'),
      (45, 55, 'E'),
      (45, 55, 'F'),
      (55, 70, 'G'),
      (80, 90, 'H')
    )

    def test_build(self):
        c = sequence_builder(notes_from_tuples(self.TEST_NOTES), 10)
        print(c)


class NoteSequenceTest(TestCase):


    def test_basic(self):

        notes = from_string('A-10 B-10 C-20')
        self.assertEqual(str(notes), 'A-10 B-10 C-20')

    def test_split(self):
        notes = from_string('A-10 R-3 B-5 R-6 C-6 R-2')
        notes.stop += 2
        self.assertEqual(len(notes), 3)
        self.assertEqual(notes.duration, 32)

        result = " | ".join((str(x) for x in notes.split(4)))
        self.assertEqual(result,
                "A-4~ | A-4~ | A-2 R-2 | R-1 B-3~ | B-2 R-2 | R-4 | C-4~ | C-2 R-2")

        self.assertEqual(" | ".join((str(x) for x in notes.split(3, 1))),
                "A-1~ | A-3~ | A-3~ | A-3 | R-3 | B-3~ | B-2 R-1 | R-3 | R-2 C-1~ | C-3~ | C-2 R-1 | R-1")


class MultiSeqenceTest(TestCase):

    TEST_NOTES = (
      (0, 10, 'A'),
      (0, 10, 'A'),
      (10, 20, 'B'),
      (15, 40, 'C'),
      (30, 50, 'D'),
      (45, 55, 'E'),
      (45, 55, 'F'),
      (55, 70, 'G'),
      (80, 90, 'H')
    )

    def test_parse(self):
        notes = from_tuples(self.TEST_NOTES)
        self.assertEqual(str(notes), 
                'AA-10 [ B-10 R-10 D-20 R-5 | R-5 C-25 R-5 EF-10 ] G-15 R-10 H-10')

        self.assertEqual(notes[1][0].duration, notes[1][1].duration)
"""
