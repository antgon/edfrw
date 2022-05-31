"""
Manage EDF file headers.
"""

import warnings
import datetime as dt
import numpy as np

EDF_HDR_DATE_FMT = '%d.%m.%y'
EDF_HDR_TIME_FMT = '%H.%M.%S'
EDF_DOB_FMT = EDF_RECDATE_FMT = '%d-%b-%Y'
ISO_DATE_FMT = '%Y-%m-%d'


class EdfHeaderException(Exception):
    pass


class EdfSubjectId:
    """Subject (patient) identification.

    The subject (patient) identification is a string (80 characters
    long) in the header of a EDF file than contains information about
    the patient's code, name, sex, and date of birth.

    This class handles that information. It is seldom useful on its own
    but rather as an attribute of `class::Header`.

    Attributes
    ----------
    code : str
        Patient code
    sex : str
        Patient sex
    dob: datetime.date
        Patient date of birth
    name : str
        Patient name
    """

    _len = 80
    __slots__ = ['_code', '_sex', '_dob', '_name']

    def __init__(self, code='', sex='', dob='', name=''):
        """
        Properties that identify the subject.

        Parameters
        ----------
        code : str, default=''
            Patient code
        sex : str, {'X', 'M', 'F'}
        dob : str or datetime, default=''
            Date of birth. It must be entered as:
            (a) a string in EDF format 'dd-MMM-yy', as in '30-DEC-1999';
            (b) a string in iso format 'yyyy-mm-dd', as in
                '1999-12-30'; or
            (c) a datetime object.
        name : str, default =''
            The patient's name

        Any field that is not known can be entered as 'X' (as per the
        EDF standard) or as an empty string ''.
        """
        self.code = code
        self.sex = sex
        self.dob = dob
        self.name = name

    @property
    def code(self):
        """
        Get or set the patient's code.
        """
        return self._code

    @code.setter
    def code(self, code):
        code = code.strip()
        if not code:
            code = 'X'
        self._code = code.replace(' ', '_')

    @property
    def sex(self):
        """
        Get or set the patient's sex.
        """
        return self._sex

    @sex.setter
    def sex(self, sex):
        sex = sex.strip()
        if not sex:
            sex = 'X'
        if sex not in ('M', 'F', 'X'):
            error = ("'sex' can only be 'M' (male), 'F' (female), or" +
                     " 'X' (unknown)")
            raise ValueError(error)
        self._sex = sex

    @property
    def dob(self):
        """
        Get or set the date of birth (DOB).

        If DOB is not known it must be an empty string '' or 'X'. If it
        is known, it must be entered as

        (a) a string in EDF format 'dd-MMM-yy', as in '30-DEC-1999';
        (b) a string in iso format 'yyyy-mm-dd', as in '1999-12-30'; or
        (c) a datetime object.

        In any case the date will be stored as a datetime.date object.
        """
        return self._dob

    @dob.setter
    def dob(self, dob):
        if (not dob) or (dob == 'X'):
            self._dob = 'X'
        elif isinstance(dob, dt.datetime):
            self._dob = dob.date()
        elif isinstance(dob, dt.date):
            self._dob = dob
        elif isinstance(dob, str):
            try:
                dob = dt.datetime.strptime(dob, ISO_DATE_FMT)
            except ValueError:
                try:
                    dob = dt.datetime.strptime(dob, EDF_DOB_FMT)
                except ValueError as error:
                    raise ValueError(error)
            self._dob = dob.date()
        else:
            raise ValueError('Invalid date format')

    @property
    def name(self):
        """
        Get or set the patient's name.
        """
        return self._name

    @name.setter
    def name(self, name):
        name = name.strip()
        if not name:
            name = 'X'
        self._name = name.replace(' ', '_')

    def to_str(self):
        """
        Return patient ID record as a single string.

        The patient identification record in an EDF file must be a
        string no longer than 80 characters. This function concatenates
        the patient attributes to create such a string. This is useful
        for making the full EDF header record.

        Returns
        -------
        patient_id : str
            A string containing patient ID in the format specified by
            EDF.
        """
        try:
            dob = self._dob.strftime(EDF_DOB_FMT)
        except:
            dob = 'X'
        patient_id = '{} {} {} {}'.format(
            self.code, self.sex, dob, self.name)
        if len(patient_id) > self._len:
            raise EdfHeaderException("SubjectId header is too long")
        return patient_id

    def __format__(self, format_spec):
        fmt = self.to_str()
        return format(fmt, format_spec)

    def __str__(self):
        return self.to_str()


class EdfRecordingId:
    """Recording identification.

    The 'local recording identification field' is a string of 80
    characters in the header of a EDF file. It contains information
    about the start date, experiment ID, investigator ID, and equipment
    code, each of these separated by a space.

    This class handles that information. It is seldom useful on its own
    but rather as an attribute of `class::Header`.

    Attributes
    ----------
    equipment_code : str
    experiment_id : str
    investigator_id : str
    startdate : datetime.date
    """
    _len = 80
    __slots__ = ['_startdate', '_experiment_id', '_investigator_id',
                 '_equipment_code']

    def __init__(self, startdate=None, experiment_id='',
                 investigator_id='', equipment_code=''):
        """
        The 'local recording identification field'.

        The recording identification field forms part of the EDF
        header. All these subfields together will be concatenated
        (separated by spaces) to form one string which must not exceed
        80 characters. Note that the text 'Startdate' is always
        prepended to this string, and this must betaken into account
        for the character count.

        Fields that are unknown (empty strings) will be replaced by an
        'X' as per the EDF specification.

        Parameters
        ----------
        startdate : str or datetime or None, default=None
            The start date. Expected to be:
            (a) a string in isoformat ('yyyy-mm-dd'), or
            (b) a `datetime` instance, as in e.g. datetime.now(), or
            (c) a date string with format '%d-%b-%Y', as in e.g.
            '02-AUG-1951', which is the format required by EDF for this
            field, or
            (d) None, in which case the current date will be used
        experiment_id : str, default=''
            "The  hospital administration code of the investigation,
            i.e. EEG number" (Kemp, 2003)
        investigator_id : str, default=''
            "A code identifying the responsible investigator" (Kemp,
            2003)
        equipment_code : str, default=''
            "A code specifying the used equipment" (Kemp, 2003)
        """
        self.startdate = startdate
        self.experiment_id = experiment_id
        self.investigator_id = investigator_id
        self.equipment_code = equipment_code

    @property
    def startdate(self):
        """
        Get or set the recording start date.

        To set the date, any of these values are acceptable:
            (a) a string in isoformat ('yyyy-mm-dd'), or
            (b) a `datetime` instance, as in e.g. datetime.now(), or
            (c) a date string with format '%d-%b-%Y', which is the
                format required by EDF for this field.
            (d) None, in which case the current date will be used.

        In all cases startdate will be saved internally as a datetime
        object.
        """
        return self._startdate

    @startdate.setter
    def startdate(self, startdate):
        # If startdate is None, create one using current date.
        if startdate is None:
            self._startdate = dt.datetime.now().date()
        elif isinstance(startdate, dt.datetime):
            self._startdate = startdate.date()
        elif isinstance(startdate, dt.date):
            self._startdate = startdate
        # If startdate is a string, try to convert to datetime. A
        # ValueError is raised if the format does not match.
        elif isinstance(startdate, str):
            try:
                startdate = dt.datetime.strptime(startdate,
                                                 ISO_DATE_FMT)
            except ValueError:
                try:
                    startdate = dt.datetime.strptime(startdate,
                                                     EDF_RECDATE_FMT)
                except ValueError as error:
                    raise ValueError(error)
            self._startdate = startdate.date()
        else:
            raise ValueError('Invalid date format')

    @property
    def experiment_id(self):
        """
        Get or set the experiment ID.

        Any spaces will be replaced by underscores, as required by EDF.
        """
        return self._experiment_id

    @experiment_id.setter
    def experiment_id(self, experiment_id):
        experiment_id = str(experiment_id)
        experiment_id = experiment_id.strip()
        if not experiment_id:
            experiment_id = 'X'
        self._experiment_id = experiment_id.replace(' ', '_')

    @property
    def investigator_id(self):
        """
        Get or set the investigator ID.

        Any spaces will be replaced by underscores, as required by EDF.
        """
        return self._investigator_id

    @investigator_id.setter
    def investigator_id(self, investigator_id):
        investigator_id = str(investigator_id)
        investigator_id = investigator_id.strip()
        if not investigator_id:
            investigator_id = 'X'
        self._investigator_id = investigator_id.replace(' ', '_')

    @property
    def equipment_code(self):
        """
        Get or set the equipment code.

        Any spaces will be replaced by underscores.
        """
        return self._equipment_code

    @equipment_code.setter
    def equipment_code(self, equipment_code):
        equipment_code = str(equipment_code)
        equipment_code = equipment_code.strip()
        if not equipment_code:
            equipment_code = 'X'
        self._equipment_code = equipment_code.replace(' ', '_')

    def to_str(self):
        """
        Return the recording identification as a single string.

        The local recording identification in an EDF file must be a
        string no longer than 80 characters. This function concatenates
        the recording attributes to create such a string. This is useful
        for making the full EDF header record.

        Returns
        -------
        rec_id : str
            A string containing the recording identification in the
            format specified by EDF.
        """
        rec_id = 'Startdate {} {} {} {}'.format(
            self.startdate.strftime(EDF_RECDATE_FMT),
            self.experiment_id,
            self.investigator_id,
            self.equipment_code)
        if len(rec_id) > self._len:
            raise EdfHeaderException('RecordingId header is too long')
        return rec_id

    def __format__(self, format_spec):
        fmt = self.to_str()
        return format(fmt, format_spec)

    def __str__(self):
        return self.to_str()


class EdfSignal:
    """Properties of a signal.

    These properties are stored in the header of an EDF file (after
    the first 256 bytes which contain the 'main' header). Each signal
    header is 256 bytes long.

    Attributes
    ----------
    digital_max : int
    digital_min : int
    gain : number
    label : str
    number_of_samples_in_data_record : int
    physical_dim : str
    physical_max : number
    physical_min : number
    prefiltering : str
    reserved : str
    sampling_freq : number
    transducer_type : str

    Examples
    --------
    Example 1: A voltage signal digitised with a 12-bit ADC,
    single-ended, input range 0 to 5 V. Sampling rate (fs) is 30 Hz.
    `saving_period_s` is how often (in seconds) the data are saved to
    disk.

    >>> fs = 30
    >>> signal = edfrw.EdfSignal(label='ADC', sampling_freq=fs,
    ...     physical_dim="V",
    ...     number_of_samples_in_data_record=saving_period_s*fs,
    ...     physical_min=0, physical_max=5,
    ...     digital_min=0, digital_max=4095)

    Example 2: A voltage signal, digitised with a 16-bit ADC with input
    range -10 to 10 V. Sampling rate (fs) is 1000 Hz.

    >>> fs = 1000
    >>> signal = edfrw.EdfSignal(label='ADC', sampling_freq=fs,
    ...     number_of_samples_in_data_record=saving_period_s*fs,
    ...     physical_dim="V", physical_min=-10, physical_max=10,
    ...     digital_min=-0x8000, digital_max=0x7fff)

    Example 3: A digital signal as a boolean (off = 0, on = 1)

    >>> signal = edfrw.EdfSignal(label='ON-OFF', sampling_freq=fs,
    ...     number_of_samples_in_data_record=saving_period_s*fs,
    ...     physical_min=0, physical_max=1, digital_min=0,
    ...     digital_max=1)
    """

    (LABEL, TRANSDUCER_TYPE, PHYSICAL_DIM, PHYSICAL_MIN, PHYSICAL_MAX,
     DIGITAL_MIN, DIGITAL_MAX, PREFILTERING, NSAMPLES, RESERVED
     ) = range(10)

    _fields = ('label', 'transducer_type', 'physical_dim',
               'physical_min', 'physical_max', 'digital_min',
               'digital_max', 'prefiltering',
               'number_of_samples_in_data_record', 'reserved')

    # Byte size of each field
    _sizes = (16, 80,  8,  8,  8,  8,  8, 80,  8, 32)

    # Slots are created by prepending an underscore to each field. The
    # fields 'sampling_freq' and 'gain' are not part of the EDF
    # specification; they are added for convenience.
    __slots__ = ['_' + field for field in _fields]
    __slots__.append('sampling_freq')
    __slots__.append('_gain')

    def __init__(self, label='', transducer_type='', physical_dim='',
                 physical_min=-32768, physical_max=32767,
                 digital_min=-32768, digital_max=32767, prefiltering='',
                 number_of_samples_in_data_record=0, sampling_freq=0):
        """
        Properties of a signal in an EDF file.

        Parameters
        ----------
        label : str, max. length=16, default=''
        transducer_type : str of size 80, default=''
            The type of sensor used, e.g. 'thermistor' or 'Ag-AgCl
            electrode'.
        physical_dim : str, max. length=8, default=''
            The physical dimension. A string that must start with a
            prefix (e.g. 'u' for 'micro') followed by the basic
            dimension (e.g. 'V' for volts). Other examples of basic
            dimensions are 'K', 'degC' or 'degF' for temperature, and
            '%' for SaO2. Powers are denoted by '^', as in 'V^2/Hz'. An
            empty string represents an uncalibrated signal. For
            standards on labels and units, see
            http://www.edfplus.info/specs/edftexts.html
        physical_min : number, default=-32768
        physical_max : number, default=32767
            The physical minimum and maximum should correspond to the
            digital extremes `digital_min` and `digital_max` and be
            expressed in the physical dimension `physical_dim`.
            The values of `physical_min` and `physical_max` must be
            different.
        digital_min : number, default=-32768
        digital_max : number, default=32767
            "The digital minimum and maximum of each signal should
            specify the extreme values that can occur in the data
            records. These often are the extreme output values of the
            A/D converter." (Kemp et al. 1992). `digital_max` must be
            larger than `digital_min`. Together, the two `digital_` and
            the two `physical_` values specify the offset and the
            amplification of the signal.
        prefiltering : str, max. length=80, default=''
            Specifies if this signal was filtered; e.g. for high-pass,
            low-pass, or notch filtering, 'HP:0.1Hz', 'LP:75Hz',
            'N:50Hz'
        number_of_samples_in_data_record : integer, default=0
            The number of 16-bit integers that this signal occupies
        sampling_freq : number, default=0
            The sampling frequency. This subfield is not part of the EDF
            specification. It is added for convenience.

        Notes
        -----
        Use only ascii characters.

        The data in EDF files are saved as two's complement, 16-bit
        integers. Thus, the range between `digital_min` and
        `digital_max` must not exceed 2**16 - 1 = 65535.
        """
        # Initialise these values arbitrarily to avoid errors in
        # _update_gain, which is called every time the values are set
        # by their @property setters.
        self._digital_min = 0
        self._digital_max = 1
        self._physical_min = 0
        self._physical_max = 1
        self._gain = 1

        # Set EDF fields.
        self.label = label
        self.transducer_type = transducer_type
        self.physical_dim = physical_dim
        self.physical_min = physical_min
        self.physical_max = physical_max
        self.digital_min = digital_min
        self.digital_max = digital_max
        self.prefiltering = prefiltering
        self.number_of_samples_in_data_record = (
            number_of_samples_in_data_record)
        self.reserved = ''

        # Not part of the specification
        self.sampling_freq = sampling_freq

    def _warning_length(self, param, max_size):
        """
        A helper function to warn the user whenever the length
        of a field exceeds that allowed by the EDF specification.
        """
        message = (f'{param} must be no longer than {max_size}' +
                   'characters. Some information will be lost.')
        warnings.warn(message)

    @property
    def label(self):
        """
        Get or set the signal label.
        """
        return self._label

    @label.setter
    def label(self, value):
        size = self._sizes[self.LABEL]
        if len(value) > size:
            self._warning_length('Label', size)
            value = value[:size]
        self._label = value.strip()

    @property
    def transducer_type(self):
        "Get or set the transducer type."
        return self._transducer_type

    @transducer_type.setter
    def transducer_type(self, value):
        size = self._sizes[self.TRANSDUCER_TYPE]
        if len(value) > size:
            self._warning_length('Transducer type', size)
            value = value[:size]
        self._transducer_type = value.strip()

    @property
    def physical_dim(self):
        """
        Get or set the signal's physical dimension.
        """
        return self._physical_dim

    @physical_dim.setter
    def physical_dim(self, value):
        size = self._sizes[self.PHYSICAL_DIM]
        if len(value) > size:
            self._warning_length('Physical dimension', size)
            value = value[:size]
        self._physical_dim = value.strip()

    @property
    def physical_min(self):
        """
        Get or set the signal's physical minimum.
        """
        return self._physical_min

    @physical_min.setter
    def physical_min(self, value):
        self._physical_min = float(value)
        self._update_gain()

    @property
    def physical_max(self):
        """
        Get or set the signal's physical maximum.
        """
        return self._physical_max

    @physical_max.setter
    def physical_max(self, value):
        self._physical_max = float(value)
        self._update_gain()

    @property
    def digital_min(self):
        """
        Get or set the signal's digital minimum value.
        """
        return self._digital_min

    @digital_min.setter
    def digital_min(self, value):
        self._digital_min = int(value)
        self._update_gain()

    @property
    def digital_max(self):
        """
        Get or set the signal's digital maximum value.
        """
        return self._digital_max

    @digital_max.setter
    def digital_max(self, value):
        self._digital_max = int(value)
        self._update_gain()

    @property
    def prefiltering(self):
        """
        Get or set the signal's prefiltering information.

        Examples
        --------
        If the signal was low-pass filtered with a 10 Hz cut-off,
        >>> signal.prefiltering = "LP:10Hz"
        """
        return self._prefiltering

    @prefiltering.setter
    def prefiltering(self, value):
        size = self._sizes[self.PREFILTERING]
        if len(value) > size:
            self._warning_length('Prefiltering', size)
            value = value[:size]
        self._prefiltering = value.strip()

    @property
    def number_of_samples_in_data_record(self):
        """
        Get or set the number of samples in each data record.
        """
        return self._number_of_samples_in_data_record

    @number_of_samples_in_data_record.setter
    def number_of_samples_in_data_record(self, value):
        self._number_of_samples_in_data_record = int(value)

    @property
    def reserved(self):
        return self._reserved

    @reserved.setter
    def reserved(self, value):
        self._reserved = value.strip()

    def __str__(self):
        return self.label

    def __repr__(self):
        return '<EDFSignal ' + self.label + '>'

    @property
    def gain(self):
        """
        Get the signal gain.

        The gain maps physical to digital dimensions. This property is
        calculated automatically whenever the digital or physical
        min/max values are set.
        """
        return self._gain

    def _update_gain(self):
        """
        Calculate the signal gain.
        """
        dy = self.physical_max - self.physical_min
        dx = self.digital_max - self.digital_min
        self._gain = dy / dx

    def dig_to_phys(self, value):
        """
        Convert a digital value to a physical value.

        Parameters
        ----------
        value : uint16 or array of uint16_t
            A digital value to convert. EDF digital values are always
            unsigned, 16-bit integers.

        Returns
        -------
        phys : float or array of float
            The corresponding physical value.

        Notes
        -----
        These equations follow those used in EDFBrowser to convert from
        EDF to ascii ([ascii_export.cpp](https://gitlab.com/Teuniz/
        EDFbrowser/-/blob/master/ascii_export.cpp))
        """
        offset = self.physical_max / self.gain - self.digital_max
        return self.gain * (np.int16(value) + offset)

    def phys_to_dig(self, value):
        """
        Convert a physical value to a digital value.

        Parameters
        ----------
        value : float or array of floats
            The physical value(s) to convert

        Returns
        -------
        dig : uint16_t or array of uint16_t
            The digital value

        Notes
        -----
        Follows the equation of a straight line (point-slope form):

            y = m * (x - x1) + y1

            x = (y - y1)/m + x1
        """
        dig = (value - self.physical_max)/self.gain + self.digital_max
        return np.uint16(dig)

    def __str__(self):
        s = ""
        for key in self.__slots__:
            key = key.strip("_")
            val = self.__getattribute__(key)
            s += f"{key:32} {val}\n"
        return s


class EdfHeader:
    """The header in a EDF file.

    Attributes
    ----------
    duration_of_data_record : number
    number_of_bytes_in_header : int
    number_of_data_records : int
    number_of_signals : int
    recording_id : object of class EdfRecordingId
    reserved : str
    signals : list of EdfSignal
    startdate : datetime.date
    starttime : datetime.time
    subject_id : object of class EdfSubjectId
    version : str, always '0'
    """
    # Fields and sizes (i.e. number of bytes) as per the EDF
    # specification.
    _fields = ('version', 'subject_id', 'recording_id', 'startdate',
               'starttime', 'number_of_bytes_in_header', 'reserved',
               'number_of_data_records', 'duration_of_data_record',
               'number_of_signals')

    _sizes = (8, 80, 80, 8, 8, 8, 44, 8, 8, 4)

    __slots__ = ['version', '_subject_id', '_recording_id',
                 '_startdate', '_starttime',
                 '_number_of_bytes_in_header', 'reserved',
                 '_number_of_data_records', '_duration_of_data_record',
                 '_number_of_signals', '_signals']

    def __init__(self, subject_code='', subject_sex='', subject_dob='',
                 subject_name='', experiment_id='', investigator_id='',
                 equipment_code='', duration_of_data_record=0,
                 date_time=None, reserved='', signals=[]):
        """
        Initialises an EDF header.

        Parameters
        ----------
        subject_code : str, default=''
        subject_sex : str, default=''
        subject_dob : str, default=''
        subject_name= : str, default=''
            The parameters `subject_*` are used to construct an object
            of `class::EdfSubjectId`. See that class for details.
        experiment_id : str, default=''
        investigator_id : str, default=''
        equipment_code : str, default=''
        date_time : str or datetime or None, default=None
            The parameters `experiment_id`, `investigator_id`,
            `equipment_code` and `date_time` are used to construct and
            object of `class::EdfRecordingId`. See that class for
            details.
        duration_of_data_record : number, default=0
            This can be a float, but is is recommended to be an integer
            value
        reserved : str, default=''
            Must be an empty string if the file conforms to the EDF
            format, or 'EDF+C' or 'EDF+D' if the file includes an
            annotations signal (EDF+ format).
        signals : list of EdfSignal objects, default=[]
            A list of objects of `class::Signal`
        """
        self.version = '0'  # Version is always 0.
        if date_time is None:
            date_time = dt.datetime.now()
        self.startdate = date_time
        self.starttime = date_time
        self.subject_id = EdfSubjectId(subject_code, subject_sex,
                                       subject_dob, subject_name)
        self.recording_id = EdfRecordingId(date_time, experiment_id,
                                           investigator_id,
                                           equipment_code)
        self.reserved = reserved

        # From the EDF+ specs: "The 'number of data records' can only be
        # -1 during recording. As soon as the file is closed, the
        # correct number is known and must be entered."
        self.number_of_data_records = -1

        self.duration_of_data_record = duration_of_data_record
        self.signals = signals

    def pack(self):
        """
        Return the header as a bytes object.

        The header record, which includes the subject, recording, and
        signal(s) attributes, are concatenated into a single bytes
        (ascii string) object, as required by the EDF specification.
        This object can be then used to e.g. write the header record in
        an opened EDF file.

        Returns
        -------
        main_hdr : str (ascii)
            The record header, formatted as per the EDF requirements.
        """
        main_hdr = ''
        for n in self._sizes:
            main_hdr += '{:<' + str(n) + '}'
        startdate = dt.datetime.strftime(self.startdate,
                                         EDF_HDR_DATE_FMT)
        starttime = '{:02}.{:02}.{:02}'.format(self.starttime.hour,
                                               self.starttime.minute,
                                               self.starttime.second)
        main_hdr = main_hdr.format(
            self.version,
            self.subject_id,
            self.recording_id,
            startdate,
            starttime,
            self.number_of_bytes_in_header,
            self.reserved,
            self.number_of_data_records,
            self.duration_of_data_record,
            self.number_of_signals)
        main_hdr = main_hdr.encode('ascii')
        assert len(main_hdr) == 256

        # Loop along each signal and concatenate their parameters to
        # make the signal header as expected by EDF.
        sig_hdr = ''
        for field in EdfSignal._fields:
            for signal in self.signals:
                if field == 'label':
                    val = signal.label
                    size = EdfSignal._sizes[EdfSignal.LABEL]
                elif field == 'transducer_type':
                    val = signal.transducer_type
                    size = EdfSignal._sizes[EdfSignal.TRANSDUCER_TYPE]
                elif field == 'physical_dim':
                    val = signal.physical_dim
                    size = EdfSignal._sizes[EdfSignal.PHYSICAL_DIM]
                elif field == 'physical_min':
                    val = signal.physical_min
                    size = EdfSignal._sizes[EdfSignal.PHYSICAL_MIN]
                elif field == 'physical_max':
                    val = signal.physical_max
                    size = EdfSignal._sizes[EdfSignal.PHYSICAL_MAX]
                elif field == 'digital_min':
                    val = signal.digital_min
                    size = EdfSignal._sizes[EdfSignal.DIGITAL_MIN]
                elif field == 'digital_max':
                    val = signal.digital_max
                    size = EdfSignal._sizes[EdfSignal.DIGITAL_MAX]
                elif field == 'prefiltering':
                    val = signal.prefiltering
                    size = EdfSignal._sizes[EdfSignal.PREFILTERING]
                elif field == 'number_of_samples_in_data_record':
                    val = signal.number_of_samples_in_data_record
                    size = EdfSignal._sizes[EdfSignal.NSAMPLES]
                elif field == 'reserved':
                    val = signal._reserved
                    size = EdfSignal._sizes[EdfSignal.RESERVED]
                fmt = '{:<' + str(size) + '}'
                val = fmt.format(val)
                sig_hdr += val
        sig_hdr = sig_hdr.encode('ascii')
        assert len(sig_hdr) == self.number_of_signals * 256

        return main_hdr + sig_hdr

    def __str__(self):
        """
        Display the contents of the header.
        """
        s = ""
        for field in self._fields:
            val = self.__getattribute__(field)
            s += f"{field:27}{val}\n"
        return s

    @property
    def subject_id(self):
        """
        Get or set the subject (patient) ID record.

        The subject ID can be a single string with values [code, sex,
        dob, name] separated by spaces (as is the case when reading the
        patient ID from the header of and EDF file), or an object of
        class ``EdfSubjectId``.

        Examples
        --------
        Use a single string, values are space-separated.

        >>> header.subject_id = "the_code X 1990-01-01 the_name"

        or use EdfSubjectID

        >>> id = EdfSubjectID(code, sex, dob, name)
        >>> header.subject_id = id
        """
        return self._subject_id

    @subject_id.setter
    def subject_id(self, value):
        if isinstance(value, str):
            try:
                code, sex, dob, name = value.split()
                value = EdfSubjectId(code, sex, dob, name)
            except ValueError:
                raise EdfHeaderException('subject_id not understood')
        if not isinstance(value, EdfSubjectId):
            raise EdfHeaderException(
                'subject_id must be of class edfrw.EdfSubjectId')
        self._subject_id = value

    @property
    def recording_id(self):
        """
        Get or set the recording identification.

        The recording ID can be a single string with values [start_str,
        startdate, experiment_id, investigator_id, equipment_code]
        separated by spaces (as is the case when reading the recording
        ID from the header of and EDF file), or an object of class
        ``EdfRecordingId``.

        Examples
        --------
        Using one, space-separated string of values:

        >>> rec_id = ("start_str startdate experiment_id " +
                "investigator_id  equipment_code")
        >>> header.recording_id = rec_id

        Using EdfRecordingId:

        >>> rec_id = EdfRecordingId(startdate, experiment_id,
        ...     investigator_id, equipment_code)
        >>> header.recording_id = rec_id
        """
        return self._recording_id

    @recording_id.setter
    def recording_id(self, value):
        if isinstance(value, str):
            try:
                (start_str, startdate, experiment_id, investigator_id,
                 equipment_code) = value.split()
                value = EdfRecordingId(startdate, experiment_id,
                                       investigator_id, equipment_code)
            except ValueError:
                raise EdfHeaderException('recording_id not understood')
        if not isinstance(value, EdfRecordingId):
            raise EdfHeaderException(
                'recording_id must be of class edfrw.EdfRecordingId')
        self._recording_id = value

    @property
    def startdate(self):
        """
        Set or get the recording start date.

        Parameters
        ----------       
        value : str or datetime
            It must be either
            (a) a string 'yyyy-mm-dd', e.g. '2016-10-25', or
            (b) a string 'd.m.y' as required by EDF, e.g. '16.10.25', or
            (c) a datetime object

        Returns
        -------        
        startdate : datetime object
        """
        return self._startdate

    @startdate.setter
    def startdate(self, value):
        if type(value) is str:
            try:
                value = dt.datetime.strptime(value, ISO_DATE_FMT)
            except:
                try:
                    value = dt.datetime.strptime(
                        value, EDF_HDR_DATE_FMT)
                except ValueError as error:
                    raise EdfHeaderException(error)
        self._startdate = value.date()

    @property
    def starttime(self):
        """
        Get or set the recording start time.

        Parameters
        ----------
        value : str or datetime
            It must be either
            (a) a string 'H.M.S' as required by EDF, e.g. '12.15.05',
                or
            (b) a string in standard format 'H:M:S', e.g. '12:15:05',
                or
            (b) a datetime object.
        """
        return self._starttime

    @starttime.setter
    def starttime(self, value):
        if type(value) is str:
            try:
                value = dt.datetime.strptime(value, '%H:%M:%S')
            except:
                try:
                    value = dt.datetime.strptime(value, EDF_HDR_TIME_FMT)
                except ValueError as error:
                    raise EdfHeaderException(error)
        self._starttime = value.time()

    @property
    def number_of_bytes_in_header(self):
        """
        Get or set the number of bytes in the data header.

        This value depends on the number of signals, so it should be
        updated whenever the number of signals changes.
        """
        return self._number_of_bytes_in_header

    @number_of_bytes_in_header.setter
    def number_of_bytes_in_header(self, value):
        self._number_of_bytes_in_header = int(value)

    @property
    def number_of_data_records(self):
        return self._number_of_data_records

    @number_of_data_records.setter
    def number_of_data_records(self, value):
        self._number_of_data_records = int(value)

    @property
    def duration_of_data_record(self):
        """
        Get or set the duration (in seconds) of the data record.

        This value is recommended (but not required) to be an integer.
        """
        return self._duration_of_data_record

    @duration_of_data_record.setter
    def duration_of_data_record(self, value):
        self._duration_of_data_record = float(value)

    @property
    def number_of_signals(self):
        """
        Get the number of signals in the EDF file.
        """
        return self._number_of_signals

    @property
    def signals(self):
        """
        Get or set the list of signals in an EDF file.

        This attribute is a list of ``EdfSignal`` signal objects.
        """
        return self._signals

    @signals.setter
    def signals(self, values):
        # Some values in the header depend on the number of signals.
        # Thus, these values must be updated whenever the signals list
        # changes.
        self._number_of_signals = len(values)
        self.number_of_bytes_in_header = (
            256 + (self._number_of_signals * 256))
        self._signals = values
