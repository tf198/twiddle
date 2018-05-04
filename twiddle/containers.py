import logging
logger = logging.getLogger(__name__)

from .objects import Note, Event, Instruction, Comment, TimeRange

DEBUG = True

if DEBUG:
    logger.warn("Running sequence validation - decreased performance")

class SequenceError(Exception):
    pass

class EventList(list):
    '''
    A collection of Events
    '''
    __slots__ = ('time', 'resolution')

    def __init__(self, items=(), time=None, resolution=96):
        self.resolution = resolution
        list.__init__(self, items)
        if time is None:
            time = TimeRange.from_events(self)
        self.time = time

    @property
    def duration(self):
        return self.time.ticks

    @property
    def is_sequential(self):
        last = self.time
        for e in self:
            if e.time < last: return False
            last = e.time
        return True

    def validate(self):
        last = TimeRange(-1, -1)
        for e in self:
            if self.time | e.time == None: raise SequenceError("%r outside of %r" % (e, self.time))
            if self.time < last: raise SequenceError("Sequence jumps back at %r" % e)

    def add_event(self, tick, event):
        self.insert(Event(TimeRange(tick, tick), Instruction(event)))
        return self

    def append(self, event, sequential=False):
        '''
        Appends an event.
        If the event is out of sequence the container is sorted after.
        '''
        if sequential and event.time.start < self.time.stop:
            raise SequenceError("Cannot go back in time")

        list.append(self, event)
        if event.time.start < self.time.stop:
            self.sort()

        self.time &= event.time
        if DEBUG: self.validate()
        return self

    def insert(self, event):
        '''
        Inserts an event.
        This is an alias for append() as there is no distinction.
        '''
        return self.append(event)

    def at_resolution(self, r):
        '''
        Does a deep copy, changing the resolution of all events.
        '''

        for x in self:
            yield Event(x.time * (r, self.resolution), x.item)
    
    def extend(self, seq):
        '''
        Appends all the items from container to this one.
        '''
        if not isinstance(seq, self.__class__):
            seq = self.__class__(seq, resolution=self.resolution)
        if len(seq) == 0: return self

        if seq.resolution != self.resolution:
            seq = self.__class__(seq.at_resolution(self.resolution))
        
        list.extend(self, seq)
        self.time &= seq.time

        self.sort()
        if DEBUG: self.validate()
        return self

    def paste(self, seq, offset=0):
        '''
        Appends all the items from container to this one.
        The items are offset to follow sequentially from the current.
        You can specify a gap by giving a positive offset.
        '''
        offset += self.time.stop - seq.time.start
        self.extend(( x.shift(offset) for x in seq ))

    def __iadd__(self, other):
        ' Convenience method for cut-n-paste score operations '
        self.paste(other)

    def get(self, window):
        '''
        Get all elements that occur within a given TimeRange
        If an integer tick position is passed then the result will be all elements starting
        at that position.
        '''
    
        if isinstance(window, int):
            seq = [ e for e in self if e.time.start == window ]
            return EventList(seq, resolution=self.resolution)

        return self.__class__([ x for x in self if window.contains(x.time) ], window, self.resolution)

    def slice(self, window):
        result = []
        for e in self:
            if window.intersects(e.time):
                result.append(e.slice(window))
        return self.__class__(result, window, self.resolution)

    def split(self, position):
        return (
            self.slice(TimeRange(self.time.start, position)),
            self.slice(TimeRange(position, self.time.stop))
        )

    def __getitem__(self, key):

        if isinstance(key, TimeRange):
            return self.get(key)

        return list.__getitem__(self, key)


    def note_iter(self):
        for x in self:
            if isinstance(x.item, Note): yield x
            if isinstance(x, EventList):
                for o in x: yield o

    def note_events(self):
        return [ x for x in self if isinstance(x.item, Note) ]

    def add_attr(self, attr):
        for x in self.note_iter():
            x.item.add_attr(attr)

    def get_track_view(self, **kwargs):
        from .views import TrackView
        return TrackView(resolution=self.resolution, **kwargs)

    def apply(self, f, *args, **kwargs):
        '''
        Convenience function to call other functions
        '''
        if isinstance(f, basestring):
            from . import functions
            f = getattr(functions, f)

        return f(self, *args, **kwargs)

    def __and__(self, other):
        result = self.__class__()
        result.extend(self)
        result.extend(other)
        return result

    def __exit__(self, e, *args):
        if e:
            logger.exception("Failed to apply functions")
            raise e

    def __enter__(self):
        return self

    def render_track(self, track_view=None, context={}, **kwargs):

        if track_view is None:
            track_view = self.get_track_view(**kwargs)

        output = []
        for bar_info, key, notes in track_view.split_sections(self):
            context['key'] = key
            output.append(notes.render_section(bar_info, context))
        return "\n".join(output)

    def render_section(self, bar_info=None, context={}, **kwargs):
        clock = self.time.start
        
        if bar_info is None:
            bar_info = self.get_track_view(**kwargs).bar_info(1)
        context['resolution'] = self.resolution

        output = []
        for e in self:
            if clock < e.time.start: # need to add rests before
                for r in bar_info.get_rests(clock, e.time.start-clock):
                    output.append(r.to_lily(context))
                clock = e.time.start

            if e.time.start < clock:
                logger.warning("Dropping overlapping note %s at bar %d" % 
                        (e.to_lily(context), bar_info.bar_at(e.time.start)))
            else:
                if isinstance(e, EventList):
                    output.append(e.render_section(bar_info, context))
                elif isinstance(e.item, Note):
                    for n in bar_info.split_note(e):
                        output.append(n.to_lily(context))
                else:
                    output.append(e.to_lily(context))
                clock = e.time.stop

        # output any trailing rests
        if clock < self.time.stop:
            for r in bar_info.get_rests(clock, self.time.stop-clock):
                output.append(r.to_lily(context))

        return " ".join(output)

    def render_notes(self, context={}):

        return " ".join(( x.to_lily(context) for x in self))


    def to_lily(self, context={}):
        context['resolution'] = self.resolution

        if 'track_view' in context:
            new_context = { k: context[k] for k in context if k != 'track_view' }
            return self.render_track(context['track_view'], new_context)

        if 'bar_info' in context:
            return self.render_section(context['bar_info'], context)

        return self.render_notes(context)


    def items(self):
        return [ x.item for x in self ]
    
    def __repr__(self):
        l = len(self)
        if l == 0 or l > 20:
            output = "%d events" % len(self)
        else:
            output = ", ".join((repr(x) for x in self))
        return "[{0}]{1}".format(output, self.time)

class ParallelEventList(list):
    __slots__ = ('time', )

    def __init__(self, time=None):
        list.__init__(self)
        if time is None:
            time = TimeRange(-1, -1)
        self.time = time

    def append(self, event):
        for s in self:
            try:
                return s.append(event)
            except SequenceError:
                pass
        list.append(self, SequentialEventList(time=self.time, resolution=self.resolution))

class VoiceList(dict):

    def __init__(self, voices=()):
        dict.__init__(self, voices)

    @classmethod
    def from_midi(cls, filename, quantize=48):
        import midi
        from . import generators
        pattern = midi.read_midifile(filename)

        result = VoiceList()
        for i, track in enumerate(pattern):
            #t = generators.sequence_builder(generators.notes_from_midi(track, quantize), pattern.resolution)
            t = EventList(resolution=pattern.resolution).extend(generators.group_chords(generators.notes_from_midi(track, quantize)))
            result['Track{0}'.format(chr(i+65))] = t

        result.resolution = pattern.resolution
        return result

    def select(self, voices):
        result = VoiceList()

        if isinstance(voices, dict):
            for name, track in voices.items():
                result[name] = self[track]
        else:
            for name in voices:
                result[name] = self[name]

        return result

    def get(self, r):
        return VoiceList(( (name, self[name].get(r)) for name in self ))

    def slice(self, r):
        return VoiceList(( (name, self[name].slice(r)) for name in self ))

    def extend(self, v):
        for k in self:
            self[k].extend(v[k])

    def __getitem__(self, key):
        if isinstance(key, (TimeRange, int)):
            return self.get(key)
        return dict.__getitem__(self, key)


    def __enter__(self):
        return self

    def __exit__(self, e, *args):
        if e:
            logger.exception(e)
            raise e

    def __getattr__(self, name):

        ALLOWED = ('add_event', 'apply', 'add_attr')

        if not name in ALLOWED:
            raise AttributeError("Not a valid method: %s" % name)

        def f(*args, **kwargs):
            result = VoiceList()
            for k in self:
                result[k] = getattr(self[k], name)(*args, **kwargs)
            return result

        return f

    def to_lily(self, context={}):

        context['bar_breaks'] = True

        return "\n\n".join([ "{0} = {{\n{1}\n}}".format(track, self[track].to_lily(context))
            for track in self])
