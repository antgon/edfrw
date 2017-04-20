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


from .headers import Header

class EdfWriter(object):
    def __init__(self, fname, subject_id, recording_id, signals,
                 saving_period_s=5, date_time=None):
        self.fname = fname
        self._f = open(fname, 'wb')

        '''
        saving_period_s <int>   How often (in seconds) will the data be
                                saved to disk? This value sets EDF
                                header's `duration_of_data_record`,
                                which is the duration in seconds of one
                                data record.

        From the specification:
        The duration of each data record is recommended to be a whole
        number of seconds and its size (number of bytes) is recommended
        not to exceed 61440. Only if a 1s data record exceeds this size
        limit, the duration is recommended to be smaller than 1s (e.g.
        0.01).
        '''
        duration_of_data_record = int(saving_period_s)

        self.header = Header(
                subject_id=subject_id,
                recording_id=recording_id,
                signals=signals,
                date_time=date_time,
                duration_of_data_record=duration_of_data_record)

        self.number_of_signals = len(signals)

        self.write_header()

    def update_subject_id(self, subject_id):
        self.header.set_subject_id(subject_id)

    def update_recording_id(self, recording_id):
        self.header.set_recording_id(recording_id)

    def update_startdate(self, startdate):
        self.header.set_startdate(startdate)

    def update_starttime(self, starttime):
        self.header.set_starttime(starttime)

    def write_header(self):
        # pack the header
        hdr = self.header.pack()
        # keep a reference to the current pointer
        pointer = self._f.tell()
        # move to the beginning of the file and write the header
        self._f.seek(0)
        self._f.write(hdr)
        # if the pointer before updating the header was beyond the
        # limits of the header then move forward to that place
        if pointer > self.header.number_of_bytes_in_header:
            self._f.seek(pointer)

    def write_data_record(self, buffer):
        '''
        Signals are allowed to be acquired at different sampling rates.
        The data are saved in data blocks (named 'data records' in the
        specification). The total number of samples in the block is thus
        determined by adding the sizes of the individiual signals
        (`signal.number_of_samples_in_data_record`).

        Each data block holds all data aquired during a time interval of
        `header.duration_of_data_record` seconds, and the total number
        of data records in the file are `header.number_of_data_records`.

        Thus, to write a data block (data record), the data must be
        the concatenation of samples acquired during the period of time
        `duration_of_data_record` first all samples from signal 0, then
        signal 1, etc.

            signal_0.samples[sig_0_number_of_samples_in_data_record]
            signal_1.samples[sig_1_number_of_samples_in_data_record]
        '''
        assert(len(buffer) ==
               self.header.number_of_samples_in_data_record)
        self._f.write(buffer)
        self.header.number_of_data_records += 1

    def flush(self):
        self._f.flush()

    def close(self):
        self.write_header()
        self.flush()
        self._f.close()

    @property
    def closed(self):
        return self._f.closed

    def __enter__(self):
        return self

    def __exit__(self, ctx_type, ctx_value, ctx_traceback):
        self.close()
