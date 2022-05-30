"""
edfrw
=====

A library for reading and writing European Data Format (EDF) files. EDF
is a format for data storage that is particularly useful for recording
biosignals. The format is described in detail in
http://www.edfplus.info/.

"""

import sys
if (sys.version_info.major < 3) or (sys.version_info.minor < 5):
    raise Exception('PyDaq requires Python 3.5 or greater')

from .headers import (EdfHeader, EdfSignal, EdfRecordingId,
                      EdfSubjectId)
from .writer import EdfWriter
from .reader import EdfReader

__version__ = '1.0.0'


# Convenience function to read or write an EDF file.
def open_edf(filename, mode='r'):
    if mode == 'r':
        return(EdfReader(filename))
    elif mode == 'w':
        return(EdfWriter(filename))
