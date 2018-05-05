from .objects import Note, Event, TimeRange

import logging
logger = logging.getLogger(__name__)

def quantize(step):

    def f(notes):
        m = float(notes.resolution * 4 / step)
        def f(i):
            return int(round(i / m) * m)

        for e in notes:
            stop = e.start + e.item.duration
            e.start = f(e.start)
            new_duration = f(stop - e.start)
            
            e.item = e.item._replace(duration=new_duration)
    return f

def add_attr(container, attr):
    for e in container:
        try:
            e.add_attr(attr)
        except AttributeError: # not a Note event
            pass
    return container

def group(container, interval, start, end):

    notes = container.note_events()
    for i in range(interval, len(notes)+1, interval):
        notes[i-interval].item.add_attr(start)
        notes[i-1].item.add_attr(end)
    
    return container

def slur(container, interval):
    return group(container, interval, '(', ')')

def beam(container, interval):
    return group(container, interval, '[', ']')

def cres(container):
    notes = container.note_events()
    container[0].item.add_attr(r'\<')
    container[-1].item.add_attr(r'\!')
    return container

def extend(container, max_gap):
    gap_ticks = float(container.resolution * 4 / max_gap)
    logger.debug("Removing gaps shorter than %d", gap_ticks)

    notes = container.note_events() + [Event(TimeRange(container.time.stop, container.time.stop), None)]
    for i in range(len(notes)-1):
        gap = notes[i+1].time.start - notes[i].time.stop
        if gap > 0 and gap <= gap_ticks:
            # logger.debug("Extending note at %d by %d", notes[i].time.start, gap)

            notes[i].set_time(stop=notes[i+1].time.start)
            #if isinstance(notes[i], ParallelEventList):
            #    for s in notes[i]: s.set_time(stop=notes[i].time.stop)

    return container 

def transpose(container, offset):
    for note in container.note_iter():
        if isinstance(note.item.pitch, int):
            note.item.pitch = note.item.pitch + offset
        else:
            note.item.pitch = [ p + offset for p in note.item.pitch ]

    return container

def flatten(container):
    return container

def octave_up(container, r):
    container.add_event(r.start, r'\ottava #1')
    container.add_event(r.stop, r'\ottava #0')
    return container

def attribute_list(container, items):
    for position, attr in items:
        container.get(position).add_attr('\\' + attr)
    return container

def sequential(container):

    result = SequentialEventList(time=seq.time, resolution=seq.resolution)
    parallel = None
    last = TimeRange(-1, -1)

    for event in container:
        if parallel is not None and event.time.is_after(parallel.time): # can close our ParallelEventList
            logger.debug("Closing simultaneous container at %d", multi.stop)
            parallel.close()
            parallel = None

        if multi is None:
            try:
                result.append(event)
            except SequenceError:
                prev = result.pop()
                logger.debug("Creating simultaneous container at %d", prev.time.start)
                parallel = ParallelEventList(time=prev.time, resolution=resolution)
                parallel.append(prev)
                parallel.append(event)
                result.append(parallel)
        else:
            parallel.append(event)

    return result
