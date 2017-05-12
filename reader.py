#! /usr/bin/env python3
# coding=utf-8
'''
Copyright 2017 Antonio González

This file is part of edfrw.

edfrw is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your
option) any later version.

edfrw is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with edfrw. If not, see <http://www.gnu.org/licenses/>.
'''

import time
import struct
import datetime as dt
import numpy as np

from .headers import (RecordingId, SubjectId, seconds_to_str)

EDF_HDR_DATE_FMT = '%d.%m.%y'
EDF_HDR_TIME_FMT = '%H.%M.%S'

class HeaderReader:
    def __init__(self, f):
        hdr_fmt = ('<' + '8s' + '80s' + '80s' + '8s' + '8s' + '8s' +
                    '44s' + '8s' + '8s' + '4s')
        f.seek(0)
        hdr = f.read(256)
        hdr = struct.unpack(hdr_fmt, hdr)
        hdr = [line.decode('ascii').strip() for line in hdr]

        (version,                  # version of this data format (0)
         subject_id,               # local patient identification
         recording_id,             # local recording identification
         startdate,                # startdate of recording (dd.mm.yy)
         starttime,                # starttime of recording (hh.mm.ss)
         number_of_bytes,          # number of bytes in header record
         reserved,                 # reserved
         number_of_data_records,   # number of data records
         duration_of_data_records, # duration of a data record (s)
         number_of_signals         # number of signals in data record
        ) = hdr

        self.version = version
        self.subject_id = SubjectId(*subject_id.split(' '))
        self.recording_id = RecordingId(*recording_id.split(' ')[1:])
        self.startdate = dt.datetime.strptime(
                startdate, EDF_HDR_DATE_FMT).date()
        self.starttime = dt.datetime.strptime(
                starttime, EDF_HDR_TIME_FMT).time()
        self.number_of_bytes = int(number_of_bytes)
        self.reserved = reserved
        self.number_of_data_records = int(number_of_data_records)
        self.duration_of_data_records = float(duration_of_data_records)
        self.number_of_signals = int(number_of_signals)

        # Signal header.
        # After the main header (256 bytes) there are an additional 256
        # bytes of header for each signal. The curious thing is that
        # each entry is repeated ns times (instead of having all entries
        # for one signal, then all entries for the next signal, etc).
        # So each entry must be read 'ns' times, where 'ns' is the
        # number of signals in the file.
        # sig_fmt = '<' + ('{}s' * 10)
        # sig_bites = np.array([16, 80, 8, 8, 8, 8, 8, 80, 8, 32])
        # sig_bites *= self.number_of_signals
        # sig_fmt = sig_fmt.format(*sig_bites)
        # hdr = f.read(self.number_of_signals * 256)
        # hdr = struct.unpack(sig_fmt, hdr)
        # hdr = [line.decode('ascii').strip() for line in hdr]

        ns = self.number_of_signals

        label = np.fromfile(f, '<S16', ns)
        label = label.astype(str)
        self.label = np.array([s.strip() for s in label])

        transducer = np.fromfile(f, '<S80', ns)
        transducer = transducer.astype(str)
        self.transducer = np.array([s.strip() for s in transducer])

        physical_dim = np.fromfile(f, '<S8', ns)
        physical_dim = physical_dim.astype(str)
        self.physical_dim = np.array([s.strip() for s in physical_dim])

        physical_min = np.fromfile(f, '<S8', ns)
        self.physical_min = physical_min.astype(float)

        physical_max = np.fromfile(f, '<S8', ns)
        self.physical_max = physical_max.astype(float)

        digital_min = np.fromfile(f, '<S8', ns)
        self.digital_min = digital_min.astype(int)

        digital_max = np.fromfile(f, '<S8', ns)
        self.digital_max = digital_max.astype(int)

        prefiltering = np.fromfile(f, '<S80', ns)
        prefiltering = prefiltering.astype(str)
        self.prefiltering = np.array([s.strip() for s in prefiltering])

        number_of_samples = np.fromfile(f, '<S8', ns)
        self.number_of_samples = number_of_samples.astype(int)

        reserved = np.fromfile(f, '<S32', ns)
        reserved = reserved.astype(str)
        reserved = np.array([s.strip() for s in reserved])

        # Extra attributes.
        # These attributes are not part of the standard EDF header, but
        # are added because they are useful.

        # Sampling frequency of each field.
        # Each set of signals is saved every 'duration_of_data_records',
        # so if a signal's number_of_samples is e.g. 3000 and the
        # duration_of_data_records is 30 seconds, then the sampling
        # frequency will be 3000 / 30 = 100 Hz
        if self.duration_of_data_records == 0:
            self.sampling_freq = np.nan
        else:
            self.sampling_freq = (self.number_of_samples /
                self.duration_of_data_records)

        # String representing the total duration of the recording.
        s = self.number_of_data_records * self.duration_of_data_records
        self.duration = seconds_to_str(s)

class EdfReader(object):
    def __init__(self, fname):
        self._f = open(fname, mode = 'rb')
        self.header = HeaderReader(self._f)

    def close(self):
        self._f.close()

if __name__ == "__main__":
    import pandas as pd

    edf = EdfReader('data/SC4181E0-PSG.edf')
    signals = [pd.Series(), pd.Series(), pd.Series()]

    # This read all the data (which is a lot). Not very efficient.
    for nrec in range(edf.header.number_of_data_records):
        for nsig in range(edf.header.number_of_signals):
            nr = edf.header.number_of_samples[nsig]
            y = np.fromfile(edf._f, 'int16', nr)
            y = pd.Series(y)
            signals[nsig] = signals[nsig].append(y)
