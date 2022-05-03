#! /usr/bin/env python3
# coding=utf-8
"""
Copyright 2017-2022 Antonio González

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
"""
import struct
import numpy as np

from edfrw import (EdfHeader, EdfSignal)


def header_fromfile(filename):
    """
    Reads the header from an EDF file.

    Parameters
    ----------
    filename : str
        Path to the EDF file

    Returns
    -------
    header : object of `class::EdfHeader`
    """
    # String that represents the first 256 bytes in the header in the
    # format required by struct.unpack
    hdr_fmt = '<'
    for size in EdfHeader._sizes:
        hdr_fmt += '{}s'.format(size)

    # Main header (first 256 characters in EDF file)
    header = EdfHeader()
    with open(filename, 'rb') as edffile:
        edffile.seek(0)
        hdr_str = edffile.read(256)

        # Unpack the header
        hdr_str = struct.unpack(hdr_fmt, hdr_str)
        # Convert from bytes to str
        hdr_str = [field.decode('ascii') for field in hdr_str]
        # update Header with the new values
        for (field, value) in zip(EdfHeader._fields, hdr_str):
            # `EdfHeader.number_of_signals` is a read-only attribute.
            # A trailing underscore is required to be able to set this
            # value.
            if field == 'number_of_signals':
                field = '_number_of_signals'
                value = int(value)
            setattr(header, field, value)

        # Signal header.
        # After the main header (256 bytes) there are an additional 256
        # bytes of header for each signal. The curious thing is that
        # each entry is repeated ns times (instead of having all entries
        # for one signal, then all entries for the next signal, etc).
        # So each entry must be read 'ns' times, where 'ns' is the
        # number of signals in the file.
        edffile.seek(256)
        sig_str = edffile.read(256 * header.number_of_signals)

    sig_sizes = np.array(EdfSignal._sizes).repeat(
        header.number_of_signals)
    # String that represents bytes in the header that contain signal
    # information (as required by struct.unpack)
    sig_fmt = '<'
    for size in sig_sizes:
        sig_fmt += '{}s'.format(size)
    sig_str = struct.unpack(sig_fmt, sig_str)

    signals = []
    for n in range(header.number_of_signals):
        new_signal = EdfSignal()
        new_signal_str = sig_str[n::header.number_of_signals]
        for index, field in enumerate(EdfSignal._fields):
            value = new_signal_str[index].decode('ascii')
            setattr(new_signal, field, value)
        # The EdfSignal attribute 'sampling_freq' is not part of the EDF
        # specification but it is useful, so it is added.
        new_signal.sampling_freq = (
            new_signal.number_of_samples_in_data_record /
            header.duration_of_data_record)
        signals.append(new_signal)

    header.signals = signals
    return header


class EdfReader(object):
    def __init__(self, filename):
        """
        Open an EDF file for reading data

        Parameters
        ----------
        filename : str
            Path to the EDF file
        """
        self.header = header_fromfile(filename)
        self.filename = filename
        self._open()
        self._sampling_interval = []

        samples_per_record = 0
        for signal in self.header.signals:
            samples_per_record += (
                signal.number_of_samples_in_data_record)
            self._sampling_interval.append(1/signal.sampling_freq)

        # EDF data are saved as int16 so the size (in bytes) of the
        # block (record) is twice the number of samples
        self._bytes_per_record = samples_per_record * 2

        # File size according to header
        self.calc_filesize = (self.header.number_of_data_records
                              * self._bytes_per_record
                              + self.header.number_of_bytes_in_header)

        # Actual file size
        self.filesize = self._f.seek(0, 2)

        # Note that EDFbrowser does not load files when the calculated
        # and the actual filesize values do not match but it is still
        # possible to read and thus rescue files with such 'corrupted'
        # headers just by reading as many block as there are in the file
        # (regardless of the number of blocks reported in the header).

    def _open(self):
        self._f = open(self.filename, mode='rb')

    def read_record(self, rec_number):
        """
        Returns data from one record.

        Parameters
        ----------
        rec_number : integer
            Record number to read data from (starting from 0)
        """
        if rec_number > self.header.number_of_data_records:
            msg = (f'You requested record {rec_number} but there are' +
                   f' only {self.header.number_of_data_records}' +
                   ' records.')
            print(msg)
            return

        pointer = (self.header.number_of_bytes_in_header +
                   (self._bytes_per_record * rec_number))
        self._f.seek(pointer)
        samples = self._f.read(self._bytes_per_record)
        samples = np.frombuffer(samples, 'int16')
        
        # TODO: Reshaping the samples like this only works if all the 
        # signals in the EDF file contain the same number of samples.
        # This is how EdfWriter is implemented at the moment, so this 
        # works for all EDF files created with this library. However,
        # the EDF specification allows for records containing signals 
        # sampled at different rates, in which case signals in each
        # record will contain different number of samples.
        samples = samples.reshape(self.header.number_of_signals, -1)

        return samples

    def close(self):
        self._f.close()


if __name__ == "__main__":
    filename = '../daq/data/SC4181E0-PSG.edf'
    edf = EdfReader(filename)
    edf.header.print()
