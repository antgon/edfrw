"""
Write data to files in European Data Format (EDF).
"""


class EdfWriter(object):
    """Open an EDF for writing.

    Attributes
    ----------
    filename : str
        EDF file name.
    header : object of `class::EdfHeader`
        File header.
    saving_period_s : int
        How often to write data to the EDF file.
    closed : bool
        Whether the file has been closed.
    """

    # Size and position in the header of number_of_data_records (nr)
    _nr_size = 8
    _nr_pos = 236

    def __init__(self, filename, header, saving_period_s):
        """
        Create and open an EDF file for writing.

        Parameters
        ----------
        filename : str
            EDF file name.
        header : instance of `headers.Header`
            The file header.
        saving_period_s : integer
            How often (in seconds) will the data be saved to disk? This
            value sets EDF header's `duration_of_data_record`, which is
            the duration in seconds of one data record.

            From the specification: "The duration of each data record is
            recommended to be a whole number of seconds and its size
            (number of bytes) is recommended not to exceed 61440. Only
            if a 1s data record exceeds this size limit, the duration is
            recommended to be smaller than 1s (e.g. 0.01)."
        """
        self.filename = filename
        self._f = open(self.filename, 'wb')
        self.header = header
        self.header.duration_of_data_record = saving_period_s
        # *number_of_data_records* is used as a counter in the function
        # *write_data_record*, so it is important to initialise to 0.
        self.header.number_of_data_records = 0
        for signal in self.header.signals:
            signal.number_of_samples_in_data_record = (
                signal.sampling_freq * saving_period_s)
        self.write_header()

    def write_header(self):
        """
        Write the EDF header to the current file.

        Packs the header record attributes in the format required by EDF
        and writes these values at the beginning of the current file.
        """
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
        """
        Write one data record.

        Parameters
        ----------
        buffer : uint16
            The data to be save to disk. It must be an unsigned 16-bit
            integer, two-complement values, as required by the EDF file
            format specification.

        Notes
        -----
        Signals are allowed to be acquired at different sampling rates.
        The data are saved in data blocks (named 'data records' in the
        specification). The total number of samples in the block is thus
        determined by adding the sizes of the individual signals
        (`signal.number_of_samples_in_data_record`).

        Each data block holds all data acquired during a time interval
        of `header.duration_of_data_record` seconds, and the total
        number of data records in the file are
        `header.number_of_data_records`.

        Thus, to write a data block (data record), the data must be
        the concatenation of samples acquired during the period of time
        `duration_of_data_record` first all samples from signal 0, then
        signal 1, etc:

        >>> signal_0.samples[sig_0_number_of_samples_in_data_record]
        >>> signal_1.samples[sig_1_number_of_samples_in_data_record]
        """
        # assert(len(buffer) ==
        #        self.header.number_of_samples_in_data_record)
        self._f.write(buffer)
        self.header.number_of_data_records += 1
        # It's a good idea to update the number of data records in the
        # header every time data are added to the file; that way,
        # if something goes wrong during acquisition, at least the
        # data already saved will be useful.
        self.update_number_of_records()

    def update_number_of_records(self):
        """
        Update the number of data records in the file header.

        Writes to the header the most recent value of
        'number_of_data_records' (referred to as 'nr' in the EDF
        specification).

        By definition, this value is 8-bits long and it starts at
        position 236 in the header.
        """
        # Keep a reference to the current pointer in the file.
        current_pointer = self._f.tell()
        # Pack the number_of_data_records into bytes of the right size.
        nr = '{:<{}}'.format(
            self.header.number_of_data_records, self._nr_size)
        nr = nr.encode()
        # Move pointer to the position in header and write value.
        self._f.seek(self._nr_pos)
        self._f.write(nr)
        # Return to the original position in the file.
        self._f.seek(current_pointer)

    def flush(self):
        self._f.flush()

    def close(self):
        """
        Close the EDF file
        """
        self.update_number_of_records()
        self.flush()
        self._f.close()

    @property
    def closed(self):
        return self._f.closed

    def __enter__(self):
        return self

    def __exit__(self, ctx_type, ctx_value, ctx_traceback):
        self.close()
