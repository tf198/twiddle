from .containers import VoiceList
from .views import TrackView

def init_midi():
    import argparse

    parser = argparse.ArgumentParser(description="Twiddle a midifile")
    parser.add_argument('-q', '--quantize', type=int, default=48, help="Quantize input")
    parser.add_argument('-l', '--level', default="info", help="Logging level")

    options = parser.parse_args()

    import logging
    logging.basicConfig(level=getattr(logging, options.level.upper(), logging.INFO))

    return options
