#from mingus.containers import Note
from .objects import Event, Note, TimeRange
from .containers import EventList

import logging
logger = logging.getLogger(__name__)

NOTES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb")

def notes_from_string(s, clock=0):

    for n in s.split(" "):
        note, duration = n.split('-')
        duration = int(duration)
        if note != 'R':
            pitch = NOTES.index(note) % 12 + 48
            yield Event(TimeRange(clock, clock+duration), Note(pitch, ()))
        clock += duration

def from_string(s, resolution=1, start=0):
    return EventList(resolution=resolution).extend(notes_from_string(s, start))

def notes_from_tuples(seq):

    for start, stop, item in seq:
        yield Event(start, stop, [item])

def from_tuples(seq):
    n = NoteSequence()
    n.extend(notes_from_tuples(seq))
    return n

def notes_from_midi(track, quantize=48):

    clock = 0
    pending = {}

    if track.tick_relative:
        track.make_ticks_abs()

    for e in track:
        tick = int(round(float(e.tick) / quantize)) * quantize
        clock = tick
        if e.name == 'Note Off' or (e.name == 'Note On' and e.velocity == 0):
            start = pending[e.pitch]
            if start != clock:
                yield Event(TimeRange(start, clock), Note(e.pitch, ()))
        elif e.name == 'Note On':
            pending[e.pitch] = clock
        else:
            logger.debug(e)

def group_chords(seq):

    last = None
    for event in seq:
        if last is not None and last.time == event.time:
            last.item &= event.item
        else:
            if last is not None: yield last
            last = event
    if last is not None:
        yield last



def sequence_builder(seq, resolution):
    '''
    seq: a sorted list of events
    '''

    result = SequentialContainer(resolution=resolution)
    multi = None
    last = None


    for event in seq:
        if multi is not None and event.start >= multi.stop: # can close our multi
            logger.debug("Closing simultaneous container at %d", multi.stop)
            multi.close()
            multi = None

        if multi is None:
            try:
                if last and last.start == event.start and last.stop == event.stop:
                    last.item &= event.item
                else:
                    last = event
                    result.append(event)
            except SequenceError:
                prev = result.pop()
                logger.debug("Creating simultaneous container at %d", prev.start)
                multi = SimultaneousContainer(start=prev.start, resolution=resolution)
                multi.place_item(prev)
                multi.place_item(event)
                result.append(multi)
        else:
            multi.place_item(event)

    return result

