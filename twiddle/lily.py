from fractions import Fraction 

import logging
logger = logging.getLogger(__name__)

LILY_NOTES = 'c_d_ef_g_a_b'
LILY_OCTAVES = (",,,,", ",,,", ",,", ",", "", "'", "''", "'''", "''''")

OCTAVE_UP       = r'\ottava #1'
OCTAVE_NORMAL   = r'\ottava #0'
OCTAVE_DOWN     = r'\ottava #-1'

def int_to_note(i, key=0, accidentals=('es', 'is')):

    if i is None:
        return "r"

    if isinstance(i, (list, tuple)):
        if len(i) == 1: return int_to_note(i[0])
        return "<{0}>".format(" ".join([ int_to_note(x, key) for x in i ]))

    pitch = LILY_NOTES[i % 12]
    a = ""
    if pitch == "_":
        if key >= 0:
            i -=1
            a = accidentals[1]
        else:
            i += 1
            a = accidentals[0]
        pitch = LILY_NOTES[i % 12] + a 

    return "%s%s" % (pitch, LILY_OCTAVES[i/12])


def duration_to_length(d, resolution):
    '''
    3/? = 1 dot
    7/? = 2 dot
    15/? = 3 dot

    base is denominator / 2^dots

    1 + 1/2 = 3/2 # 1.
    3/2 + 1/4 = 7/4 # 1..

    1/2 + 1/4 = 3/4 # 2.
    3/4 + 1/8 = 7/8 # 2..
    7/8 + 1/16 = 15/16 # 2...

    1/4 + 1/8 = 3/8 # 4.
    3/8 + 1/16 = 7/16 # 4..
    7/16 + 1/32 = 15/32 # 4...

    1/8 + 1/16 = 3/16 # 8.
    3/16 + 1/32 = 7/32 # 8..
    '''

    f = Fraction(d, resolution * 4)

    if f.denominator in [1, 2, 4, 8, 16, 32, 64, 128]:

        try:
            dots = (3, 7, 15, 31, 63).index(f.numerator) + 1
            base = f.denominator / (2 * dots)
            return "{0}{1}".format(base, "." * dots)
        except ValueError:
            pass # not dotted


        if f.numerator == 1: return str(f.denominator)

    logger.warning("Unable to represent %s as a duration", f)
    for i in (1, 2, 4, 8, 16, 32):
        if 1.0 / i < f: return "{0}*{1}".format(i, f*i)

class LilyBlock(list):
    glue = " "
    ends = "{}"
    newlines = "\n"
	
    def to_lily(self, state={}):
	if len(self) == 0: raise Exception("No content")

	output = self.glue.join([ x.to_lily(state) for x in self ])
		
	return "".join(["\\new ", self.__class__.__name__, " ", self.ends[0], self.newlines, output, self.newlines, self.ends[1]])


class Staff(LilyBlock):
    pass

class PianoStaff(LilyBlock):
    ends = ("<<", ">>")
    glue = "\n"
	
