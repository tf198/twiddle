from collections import namedtuple
from .containers import EventList
from .objects import TimeRange, Event, Instruction, Rest, BarCheck

def lcd(a, b):
    for i in range(2, min(a, b)+1):
        if a % i == 0 and b % i == 0: return i
    raise ValueError("No common denominator for %d and %d" % (a, b))

def rest_layout(rest_length, bar_length, divisions):
    '''
    Layout rests as best as possible
    >>> rest_layout(12, 12, 4)
    [12]
    '''

    l = bar_length
    result = []
    while True:
        while l <= rest_length:
            result.append(l)
            rest_length -= l
        if rest_length == 0: break
        try:
            f = lcd(l, divisions)
            l /= f
        except ValueError:
            result.append(l)
            break

    return result

class Boundary(namedtuple('Boundary', ('start_bar', 'start_tick', 'bar_length', 'divisions'))):

    def bar_at(self, tick):
        if tick < self.start_tick:
            raise IndexError('Cannot calculate bar prior to %d' % self.start_tick)
        return self.start_bar + (tick - self.start_tick) / self.bar_length

    def meter(self, resolution):
        return self.divisions, (resolution * 4 * self.divisions) / self.bar_length

    def is_bar_break(self, tick):
        if tick < self.start_tick:
            raise IndexError('Cannot calculate bar prior to %d' % self.start_tick)
        return (tick - self.start_tick) % self.bar_length == 0

    def split_note(self, e):
        
        offset = (e.time.start - self.start_tick) % self.bar_length
        bar_start = e.time.start - offset
        window = TimeRange(bar_start, bar_start+self.bar_length)

        while window.start < e.time.stop:
            n = e.slice(window)
            window += self.bar_length
            yield n
            if n.time.stop == window.start:
                yield Event(TimeRange(window.start, window.start),
                        BarCheck(self.bar_at(window.start)))


    def rest_layout(self, length):
        '''
        Layout rests as best as possible
        '''

        l = self.bar_length
        d = self.divisions
        result = []
        while True:
            while l <= length:
                result.append(l)
                length -= l
            if length == 0: break
            try:
                f = lcd(l, d)
                l /= f
            except ValueError:
                result.append(l)
                break

        return result

    def get_rests(self, tick, tick_length):
        if tick < self.start_tick:
            raise IndexError('Cannot calculate bar prior to %d' % self.start_tick)

        tick -= self.start_tick

        # first need to get to a bar start
        if tick % self.bar_length:
            rest_ticks = min(tick_length, self.bar_length - tick % self.bar_length)

            for r in sorted(rest_layout(rest_ticks, self.bar_length, self.divisions)):
                yield Event(TimeRange(tick, tick+r), Rest('r'))
                tick += r
            tick_length -= rest_ticks
            if tick % self.bar_length == 0:
                yield Event(TimeRange(tick, tick), BarCheck(self.bar_at(tick+self.start_tick)))
            else:
                return

        # full bars
        full_bars = int(tick_length  / self.bar_length)
        if full_bars:
            rest_length = full_bars * self.bar_length
            yield Event(TimeRange(tick, tick + rest_length), Rest('R', full_bars))
            tick_length -= rest_length
            tick += rest_length
            yield Event(TimeRange(tick, tick), BarCheck(self.bar_at(tick+self.start_tick)))

        # remaining rests
        if tick_length:
            for r in rest_layout(tick_length, self.bar_length, self.divisions):
                yield Event(TimeRange(tick, tick+r), Rest('r'))
                tick += r
        

def calc_bar_length(resolution, meter):
    return resolution * 4  * meter[0] / meter[1]

class TrackView(object):

    def __init__(self, resolution, partial=0, meter=(4, 4), key="c"):
        self.resolution = resolution
        self.partial = partial
        self.meters = []
        self.keys = [(0, key)]
        self.set_meter(1, meter)

    def set_meter(self, start, meter):
        self.meters.append((start, meter))
        self.meters.sort()
       
        current_bar = 1 
        bar_length = 0
        if self.partial:
            initial = self.meters[0][1]
            bar_length = calc_bar_length(self.resolution, initial)
            ticks = self.partial * bar_length / initial[0]
        else:
            ticks = 0

        self._boundaries = []
        for start_bar, meter in self.meters:
            ticks += bar_length * (start_bar-current_bar)
            bar_length = calc_bar_length(self.resolution, meter)
            self._boundaries.append(Boundary(start_bar, ticks, bar_length, meter[0]))
            current_bar = start_bar


    def set_key(self, bar, key):
        self.keys.append((self.beat(bar), key))
        self.keys.sort()

    def beat(self, bar, beat=1, divisions=None):
        for b in self._boundaries:
            if b.start_bar >= bar: break

        bar_start = b.start_tick + b.bar_length * (bar-b.start_bar)
        if beat == 1: return bar_start

        if divisions is None:
            divisions = b.divisions
        return bar_start + (beat - 1) * b.bar_length / divisions

    def key(self, bar):
        tick = self.beat(bar)
        last = 'c'
        for start, key in self.keys:
            if start > tick: break
            last = key
        return last

    def bar(self, n):
        ' Returns the notes within the given bar '
        return self.get_range((n, 1), (n+1, 1))

    def bars(self, start, end):
        ' Returns the notes within the given bar range '
        if isinstance(start, int):
            start = (start, 1)
        if isinstance(end, int):
            end = (end+1, 1)
        return self.get_range(start, end)

    def notes(self, start, end):
        ' Returns the notes within the given range (alias for get_range())'
        return self.get_range(start, end)

    def get_range(self, start, end):
        return TimeRange(self.beat(*start), self.beat(*end))

    def bar_info(self, tick):
        ' Returns the Boundary object at the given tick '
        last = None
        for b in self._boundaries:
            if tick < b.start_tick: break
            last = b
        return last

    def split_sections(self, notes):
        clock = notes.time.start

        boundaries = self._boundaries + [Boundary(None, notes.time.stop, None, None)]

        for i in range(len(boundaries)-1):
            b = boundaries[i]
            stop = boundaries[i+1].start_tick

            section = notes.slice(TimeRange(b.start_tick, stop))
            section.add_event(b.start_tick, Instruction(r"\time %d/%d" % b.meter(notes.resolution)))

            for start, key in self.keys:
                if section.time.contains(start):
                    s, section = section.split(start)
                    yield b, key, s
                    section.add_event(start, Instruction(r"\key %s \major" % key))

            yield b, key, section

class OldBarView(object):

    def __init__(self, notes, partial=0):
        self.notes = notes
        self.meters = []
        self.partial = partial

    def add_meter(self, bar, meter):
        self.meters.append((bar, meter))
        self.meters.sort()

    def bar_iter(self):
        clock = self.notes.start + self.partial
        bar = 1
        tick_length = self.bar_length((4, 4))
        for change, meter in self.meters:
            while bar < change:
                yield bar, clock, clock + tick_length
                bar += 1
                clock += tick_length
            tick_length = self.bar_length(meter)
        while clock < self.notes.stop:
            yield bar, clock, clock + tick_length
            bar += 1
            clock += tick_length


    def bar_length(self, meter):
        return (self.notes.resolution * 4 * meter[0]) / meter[1]

    def bar_to_tick(self, n):
        if n == 0: return 0, self.partial

        bar_length = self.bar_length((4,4)) # (4/4)
        current_bar = 1
        ticks = self.partial

        for start_bar, meter in self.meters:
            if n < start_bar: break
            ticks += (start_bar - current_bar) * bar_length
            current_bar = start_bar
            bar_length = self.bar_length(meter)
            
        return ticks + (n-current_bar) * bar_length, bar_length

    def tick_to_bar(self, t):

        bar_length = self.bar_length((4,4))

        t -= self.partial
        current_bar = 1

        for start_bar, meter in self.meters:
            block = (start_bar - current_bar) * bar_length
            if block >= t: break
            t -= block
            bar_length = self.bar_length(meter)
            current_bar = start_bar
            
        return current_bar + int(math.floor((float(t) / bar_length)))

    def note_at(self, bar, beat=1):
        pass

    def bar(self, i):

        start, length = self.bar_to_tick(i)

        return self.notes.slice(start, start+length)
        return self.notes.tick_slice(start, length)

    def bars(self, first, last):
        start, _ = self.bar_to_tick(first)
        end, length = self.bar_to_tick(last)
        return self.notes.slice(start, end+length)


    def bar_layout(self):
        
        bar_length = self.notes.resolution # 4/4

        yield 0, self.partial
        clock = self.partial
        
        for start_bar, meter in self.meters:
            for i in range(current_bar, start_bar):
                yield clock, bar_length
                clock += bar_length
            bar_length = self.bar_length(meter)

        while clock < self.notes.duration:
            yield clock, bar_length
            clock += bar_length

    def to_lily(self, state={}):
        split_at = self.bar_length((2, 4))
        return "".join(("%s | %% Bar %d\n" % (x.to_lily(), x.stop/split_at) for x in self.notes.split(split_at)))


