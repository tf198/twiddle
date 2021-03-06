from collections import namedtuple
from lily import int_to_note, duration_to_length

import logging
logger = logging.getLogger(__name__)

class TimeError(Exception):
    pass

class TimeRange(namedtuple('TimeRange', ('start', 'stop'))):
    '''

    '''

    @staticmethod
    def from_events(seq):
        try:
            return TimeRange(min(( x.time.start for x in seq )), max(( x.time.stop for x in seq )))
        except ValueError:
            return TimeRange(-1, -1)

    @property
    def ticks(self):
        ' Length in ticks '
        return self.stop - self.start

    def union(self, other):
        start, stop = self
        if start == -1 or other.start < start: start = other.start
        if other.stop > stop: stop = other.stop
        return TimeRange(start, stop)

    def intersection(self, other):
        start = max(self.start, other.start)
        stop = min(self.stop, other.stop)
        if stop < start:
            raise TimeError("{0} doesn't intersect {1}".format(self, other))
        return TimeRange(start, stop)

    def extend(self, tick):
        return TimeRange(start, max(self.stop, tick))

    def is_after(self, other):
        return self.start >= other.start

    def __add__(self, ticks):
        ' Shift the start and end points by the given offset '
        return TimeRange(self.start + ticks, self.stop + ticks)

    def __sub__(self, ticks):
        ' Shift the start and end points backwards by the given offset '
        return TimeRange(self.start - ticks, self.stop - ticks)

    def __mul__(self, factor):
        if isinstance(factor, tuple):
            return TimeRange(self.start * factor[0] / factor[1], self.stop * factor[0] / factor[1])
        return TimeRange(self.start * factor, self.stop * factor)

    def __and__(self, other):
        ' Union of two TimeRanges '
        return self.union(other)

    def __or__(self, other):
        ' Intersection of two TimeRanges '
        return self.intersection(other)

    def intersects(self, other):
        ''' Whether the two windows intersect.
        Returns true for zero length events at start but not at end
        '''
        if other.start < self.start and other.stop <= self.start: return False
        if other.start >= self.stop: return False
        return True

    def contains(self, other):
        ''' Whether the given tick occurs within this range.
        Returns true for zero length events at start but not at end
        '''
        if isinstance(other, int):
            other = TimeRange(other, other)

        if other.start >= self.stop or other.stop > self.stop: return False
        if other.start < self.start: return False
        return True

    def __repr__(self):
        return "(%r,%r)" % (self.start, self.stop)

class Event(object):
    """
    An Event has a time and an item.
    All methods return new instances.
    """
    __slots__ = ('time', 'item')

    def __init__(self, time, item):
        self.time = time
        self.item = item

    @property
    def duration(self):
        return self.time.ticks
    
    def set_time(self, **kwargs):
        self.time = self.time._replace(**kwargs)

    def slice(self, tick_range):
        '''
        Returns a copy of the event bounded by the given tick range
        '''
        e = Event(self.time | tick_range, self.item)
        if self.time.stop > tick_range.stop:
            e.item += "~"

        return e

    def shift(self, offset):
        return Event(self.time + offset, self.item)

    def __gt__(self, other):
        return self.time > other.time

    def __repr__(self):
        if self.time.ticks:
            return "<{0!r} {1}>".format(self.item, self.time)
        return "<{0!r} ({1})>".format(self.item, self.time.start)

    def to_lily(self, context={}):
        context['tick_length'] = self.time.ticks
        return self.item.to_lily(context)

def merge(a, b, t):
    result = []
    for x in (a, b):
        if isinstance(x, (list, tuple)):
            result.extend(x)
        else:
            result.append(x)
    return t(set(result))


class Note(object):
    __slots__ = ('pitch', 'attr')

    def __init__(self, pitch, attr=()):
        self.pitch = pitch
        self.attr = attr

    def add_attr(self, attr):
        '''
        Appends the given attribute to this note.
        '''
        self.attr += (attr, )

    def remove_attr(self, attr):
        '''
        Removes a given attribute
        '''
        self.attr = tuple(( x for x in self.attr if x != attr ))

    def __add__(self, attr):
        return Note(self.pitch, self.attr + (attr, ))

    def __and__(self, other):
        '''
        Returns the union of the two Notes.
        Pitches are combined.
        '''
        return Note(merge(self.pitch, other.pitch, list), merge(self.attr, other.attr, tuple))

    def to_lily(self, context={}):
        d = duration_to_length(context['tick_length'], context['resolution'])
        return "{0}{1}{2}".format(int_to_note(self.pitch, key=context.get('key', 'c')), 
                d, "".join(self.attr))

    def __repr__(self):
        return "%r%s" % (self.pitch, "".join(self.attr))

class Rest(object):
    __slots__ = ('c', 'repeat')

    def __init__(self, c, repeat=0):
        self.c = c
        self.repeat = repeat

    def to_lily(self, context={}):
        if self.repeat > 1:
            d = duration_to_length(context['tick_length'] / self.repeat, context['resolution'])
            return "{0}{1}*{2}".format(self.c, d, self.repeat)
        d = duration_to_length(context['tick_length'], context['resolution'])
        return "{0}{1}".format(self.c, d)

class BarCheck(object):
    __slots__ = ('bar', )

    def __init__(self, bar):
        self.bar = bar

    def to_lily(self, context={}):
        if context.get('bar_breaks'):
            return "| % bar {0}\n".format(self.bar-1)
        return "|"

class Instruction(str):
    __slots__ = ()

    def to_lily(self, context={}):
        return "\n%s\n" % self

class Comment(str):
    __slots__ = ()

    def to_lily(self, context={}):
        return "% {0}\n".format(self)

class Raw(str):
    __slots__ = ()

    def to_lily(self, context={}):
        return "% raw output\n{0}\n% end raw output\n".format(self)

class KeySignature(object):
    __slots__ = ('key', 'minor')

    def __init__(self, key, minor=False):
        self.key = key
        self.minor = minor

    def to_lily(self, context={}):
        p = 60 + self.key * 7
        if self.minor:
            p -= 3

        key = int_to_note(p, self.key).strip("',")
        logger.info("KEY: %s -> %s", self.key, key)
        return r'\key {0} \{1}'.format(key, 'minor' if self.minor else 'major')

    def __repr__(self):
        return "<Key {0}>".format(self.key)
