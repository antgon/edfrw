"""
Tools for reading data from European Data Format (EDF) files.
"""

from collections import deque
import datetime as dt
import struct
import numpy as np

from edfrw import (EdfHeader, EdfSignal)


def header_fromfile(filename):
    """
    Read the header from an EDF file.

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
    """Open an EDF file for reading.

    Attributes
    ----------
    header : object of `class::EdfHeader`
        EDF file header.
    filename : str
        Path to edf file.
    signals : list
        List of signals in EDF file.
    duration_s : number
        Duration of the recording in seconds.

    Notes
    -----
    This class currently only works for reading EDF files. Data from
    EDF+C files can also be read but the "EDF Annotations" signal will
    not be properly parsed. EDF+D files are not supported.
    """

    def __init__(self, filename):
        """
        Open and EDF file for reading.

        Parameters
        ----------
        filename : str
            Path to the EDF file.
        """
        self.header = header_fromfile(filename)
        self.filename = filename
        self.signals = self.header.signals

        # These attributes represent the way each data record is
        # organised, and they are useful for accessing the data in
        # these records.
        self._labels = [signal.label for signal in self.signals]
        record_samples = [signal.number_of_samples_in_data_record
                          for signal in self.signals]
        self._record_samples = np.array(record_samples)
        # record_sizes?
        # EDF data are saved as int16 (i.e. one sample = 2 bytes)
        self._record_bytes = (self._record_samples * 2)
        self._record_pointers = (
            np.r_[0, np.cumsum(self._record_bytes)[:-1]])
        self._bytes_in_record = np.sum(self._record_bytes)

        # Total duration of the EDF recording. Valid only for
        # continuous (uninterrupted) records, i.e. plain EDF and EDF+C
        # files.
        self.duration_s = (self.header.number_of_data_records *
                           self.header.duration_of_data_record)

        # Note that EDFbrowser does not load files when the calculated
        # and the actual filesize values do not match. It is possible
        # to read and thus rescue files with such 'corrupted' headers:
        # read as many block as there are in the file, regardless of
        # the number of blocks reported in the header).

        # File size according to header
        # self.calc_filesize = (self.header.number_of_data_records *
        #                       self._bytes_per_record +
        #                       self.header.number_of_bytes_in_header)

        # Actual file size
        # self.filesize = self._f.seek(0, 2)

        self._open()

    def _open(self):
        self._f = open(self.filename, mode='rb')

    def close(self):
        """
        Close the file.
        """
        self._f.close()

    def __str__(self):
        dur_str = str(dt.timedelta(seconds=self.duration_s))
        s = (
            f'Subject ID:         {self.header.subject_id}\n'
            f'Recording ID:       {self.header.recording_id}\n' +
            f'Start date:         {self.header.startdate}\n' +
            f'Start time:         {self.header.starttime}\n' +
            f'Duration:           {dur_str}\n' +
            f'Nr of data records: {self.header.number_of_data_records}\n' +
            f'Dur of data record: {self.header.duration_of_data_record}\n' +
            f'Nr of signals:      {self.header.number_of_signals}\n' +
            f'Signal labels:      {self._labels}')
        return s

    def read_record(self, rec_number):
        """
        Return data from one record.

        Parameters
        ----------
        rec_number : integer
            Record number to read data from (index starts from 0).

        Returns
        -------
        samples : array of int16
            Data samples in record, in the original order and format as
            that stored in the EDF file (i.e. all samples from signal 0
            followed by all samples from signal 1, etc.)
        """
        if rec_number >= self.header.number_of_data_records:
            msg = (f'You requested record {rec_number} but the ' +
                   'maximum available is ' +
                   f'{self.header.number_of_data_records-1}.')
            raise ValueError(msg)
        pointer = (self.header.number_of_bytes_in_header +
                   (self._bytes_in_record * rec_number))
        self._f.seek(pointer)
        samples = self._f.read(self._bytes_in_record)
        # samples = np.frombuffer(samples, 'int16')
        return samples

    def read_signal_from_record(self, sig_number, rec_number):
        """
        Read a signal in a data record.

        Parameters
        ----------
        sig_number : int
            Number of the signal to read (starts from 0).
        rec_number : int
            Record number (starts from 0).

        Returns
        -------
        time, samples : arrays
            Time in seconds and signal data samples.
        """
        if sig_number >= self.header.number_of_signals:
            msg = (f'You requested signal {sig_number} but the ' +
                   'maximum available is ' +
                   f'{self.header.number_of_signals-1}.')
            raise ValueError(msg)

        if sig_number < 0:
            msg = f'Invalid signal number: {sig_number}'
            raise ValueError(msg)

        if rec_number >= self.header.number_of_data_records:
            msg = (f'You requested record {rec_number} but the ' +
                   'maximum available is ' +
                   f'{self.header.number_of_data_records-1}.')
            raise ValueError(msg)

        pointer = (self.header.number_of_bytes_in_header +
                   (self._bytes_in_record * rec_number) +
                   self._record_pointers[sig_number])
        self._f.seek(pointer)
        samples = self._f.read(self._record_bytes[sig_number])
        samples = np.frombuffer(samples, 'int16')
        samples = self.signals[sig_number].dig_to_phys(samples)

        time0 = self.header.duration_of_data_record * rec_number
        time = np.arange(
            self.signals[sig_number].number_of_samples_in_data_record)
        time = (time/self.signals[sig_number].sampling_freq) + time0

        return time, samples

    def read_signal(self, signal, from_second=0, to_second=np.Inf):
        """
        Read a signal from an EDF file.

        Parameters
        ----------
        signal : integer or string
            Signal to read. If an integer, it is the signal index
            (starting from 0); if a string it is the name (label) of
            the signal.
        from_second : numeric, default=0
            Time in seconds to read data from.
        to_second : numeric, default=np.Inf (end of the recording)
            Time in seconds to read data to.

        Returns
        -------
        time, samples : arrays of floats
            Time (in seconds) and signal data samples.

        Examples
        --------
        >>> edffile = EdfReader("myfile.edf")

        Assuming this file has a signal labelled "ADC", read that
        signal from time 20 to time 750 seconds.
        >>> time, samples = edffile.read_signal("ADC", 20, 750)
        """
        if to_second > self.duration_s:
            to_second = self.duration_s

        if type(signal) is str:
            sig_number = self._labels.index(signal)
        else:
            sig_number = int(signal)

        # The first and last time point will be located in these records
        rec_from = int(np.floor(
            from_second/self.header.duration_of_data_record))
        rec_to = int(np.ceil(
            to_second/self.header.duration_of_data_record))

        # If both start and end times are within the same data record,
        # just read that record.
        if rec_from == rec_to:
            time, samples = self.read_signal_from_record(sig_number,
                                                         rec_from)

        # If there is more than one record to read, read all these
        # records
        else:
            time = deque()
            samples = deque()
            for record in range(rec_from, rec_to):
                x, y = self.read_signal_from_record(sig_number, record)
                time.extend(x)
                samples.extend(y)
            time = np.array(time)
            samples = np.array(samples)

        # Drop samples outside the requested time range and return
        is_sample = (time >= from_second) & (time < to_second)
        return time[is_sample], samples[is_sample]
