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

import warnings
from datetime import datetime
import numpy as np

'''
Two other ways of reading the header:

(1) Reading bytes directly
head = f.read(256)
version = head[0:8]
subject = head[8:88]

(2) One 'fromfile' using a pre-defined dtype:
dty = np.dtype([('version', 'S8'), ('subject', 'S80')])
head = np.fromfile(f, dty, 1)
head['subject']
head.dtype.names
'''

'''
There are two different formats for dates in the EDF specs.

header.startdate is 'dd.mm.yy' as in '30.12.99' '%d.%m.%y'
subject_id.dob and recording_id.startdate are 'dd-MMM-yy' as in
'30-DEC-1999'

so to avoid issues:
 - input date can only be as datetime object or a str in (iso format
 'yyyy-mm-dd'
   or edf format)
 - store all internally as datetime object
 - when packing headers, format to string as required

'''

#def open_edf(fname, mode='r'):
#    if mode == 'r':
#        return(EdfReader(fname))
#    elif mode == 'w':
#        return(EdfWriter(fname))


def printhdr(hdr):
    for key in sorted(hdr.__dict__.keys()):
        val = hdr.__dict__[key]
        print('{:32} {}'.format(key, val))


def seconds_to_str(s):
    h = int(s // 3600)
    m = int(s // 60 % 60)
    s = s % 60
    return '{:02d}h {:02d}m {:05.2f}s'.format(h, m, s)


def remove_space(text):
    return text.replace(' ', '_')


EDF_HDR_DATE_FMT = '%d.%m.%y'
EDF_HDR_TIME_FMT = '%H.%M.%S'
EDF_DOB_FMT = EDF_RECDATE_FMT = '%d-%b-%Y'
ISO_DATE_FMT = '%Y-%m-%d'


class EdfHeaderException(Exception):
    pass


class SubjectId:
    _len = 80

    def __init__(self, code='X', sex='X', dob='X', name='X'):
        '''
        dob is expected to be:
            (a) a string in iso format 'yyyy-mm-dd', or
            (b) a datetime instance, or
            (c) 'X' if dob is unknown.
        '''
        self.code = code
        self.sex = sex
        self.dob = dob
        self.name = name

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, code):
        self._code = remove_space(code)

    @property
    def sex(self):
        return self._sex

    @sex.setter
    def sex(self, sex):
        if sex not in ('M', 'F', 'X'):
            error = ("'sex' can only be 'M' (male), 'F' (female), or" +
                     " 'X' (unknown)")
            raise ValueError(error)
        self._sex = sex

    @property
    def dob(self):
        return self._dob

    @dob.setter
    def dob(self, dob):
        '''
        DOB must be 'X' is it is not known. If it is known, it must be
        entered as
        (a) a string in EDF format 'dd-MMM-yy', as in '30-DEC-1999';
        (b) a string in iso format 'yyyy-mm-dd', as in '1999-12-30'; or
        (c) a datetime object.
        '''
        if dob == 'X':
            self._dob = dob
        else:
            if isinstance(dob, str):
                try:
                    dob = datetime.strptime(dob, ISO_DATE_FMT)
                except ValueError:
                    try:
                        dob = datetime.strptime(dob, EDF_DOB_FMT)
                    except ValueError as error:
                        raise ValueError(error)
            # The following line will raise an error if dob is not a
            # datetime object.
            self._dob = dob.date()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = remove_space(name)

    def to_str(self):
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


class RecordingId:
    _len = 80

    def __init__(self, startdate=None, experiment_id='X',
                 investigator_id='X', equipment_code='X'):
        '''
        startdate input expected to be:
            (a) a string in isoformat ('yyyy-mm-dd'), or
            (b) a `datetime` instance, as in e.g. datetime.now(), or
            (c) None, in which case the current date will be set.
            In all cases startdate will be converted to the string
            format required by the EDF specification.
        '''
        self.startdate = startdate
        self.experiment_id = experiment_id
        self.investigator_id = investigator_id
        self.equipment_code = equipment_code

    @property
    def startdate(self):
        return self._startdate

    @startdate.setter
    def startdate(self, startdate):
        # If startdate is a string, try to convert to datetime. A
        # ValueError is raised if the format does not match.
        if isinstance(startdate, str):
            try:
                startdate = datetime.strptime(startdate, ISO_DATE_FMT)
            except ValueError as error:
                try:
                    startdate = datetime.strptime(startdate,
                                                  EDF_RECDATE_FMT)
                except ValueError as error:
                    raise ValueError(error)

        # If startdate is None, create one using current date.
        elif startdate is None:
            startdate = datetime.now()

        self._startdate = startdate.date()

    @property
    def experiment_id(self):
        return self._experiment_id

    @experiment_id.setter
    def experiment_id(self, experiment_id):
        self._experiment_id = remove_space(experiment_id)

    @property
    def investigator_id(self):
        return self._investigator_id

    @investigator_id.setter
    def investigator_id(self, investigator_id):
        self._investigator_id = remove_space(investigator_id)

    @property
    def equipment_code(self):
        return self._equipment_code

    @equipment_code.setter
    def equipment_code(self, equipment_code):
        self._equipment_code = remove_space(equipment_code)

    def to_str(self):
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


class Signal(object):

    (LABEL, TRANSDUCER_TYPE, PHYSICAL_DIM, PHYSICAL_MIN, PHYSICAL_MAX,
     DIGITAL_MIN, DIGITAL_MAX, PREFILTERING, NSAMPLES, RESERVED
     ) = range(10)

    _fields = ('label', 'transducer_type', 'physical_dim',
               'physical_min', 'physical_max', 'digital_min',
               'digital_max', 'prefiltering',
               'number_of_samples_in_data_record', 'reserved')

    # Byte size of each field
    _sizes = (16, 80,  8,  8,  8,  8,  8, 80,  8, 32)

    # Slots are created by prepending an underscore to each field. An
    # extra field 'sampling_freq' (not part of the EDF specification) is
    # added for convenience.
    __slots__ = ['_' + field for field in _fields]
    __slots__.append('sampling_freq')
    __slots__.append('gain')

    def __init__(self, label='', transducer_type='', physical_dim='',
                 physical_min=-1, physical_max=1, digital_min=-32768,
                 digital_max=32767, prefiltering='', sampling_freq=0):
        '''
        'physical dimension' (for example uV) must start with a 'prefix'
        (in this example u), followed by the 'basic dimension' (in this
        example V). The 'basic dimension' for the EXG's is 'V', for
        temperature it is 'K', 'degC' or 'degF' and for SaO2 it is '%',
        all without the quotes. The prefix scales the 'physical
        dimension' according to Table 1. Powers in a 'basic dimension'
        (for instance the basic dimension used in frequency analysis can
        be Volts to the power 2 per Hertz) are noted by ^, in this
        example V^2/Hz.

        "In case of uncalibrated signals, physical dimension is left
        empty (that is 8 spaces), while 'Physical maximum' and 'Physical
        minimum' must still contain different values"

        For standards on labels and units, see
        http://www.edfplus.info/specs/edftexts.html
        '''
        # Initialise these values to ones to avoid division by zero
        # in _update_gain().
        self._digital_min, self._digital_max = (0, 1)
        self._physical_min, self._physical_max = (0, 1)

        self.label = label
        self.transducer_type = transducer_type
        self.physical_dim = physical_dim
        self.physical_min = physical_min
        self.physical_max = physical_max
        self.digital_min = digital_min
        self.digital_max = digital_max
        self.prefiltering = prefiltering
        self.number_of_samples_in_data_record = 0
        self._reserved = ''

        # Not part of the specification
        self.sampling_freq = sampling_freq

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        size = self._sizes[self.LABEL]
        if len(value) > size:
            warnings.warn('Label is too long.')
            value = value[:size]
        self._label = remove_space(value)

    @property
    def transducer_type(self):
        return self._transducer_type

    @transducer_type.setter
    def transducer_type(self, value):
        size = self._sizes[self.TRANSDUCER_TYPE]
        if len(value) > size:
            warnings.warn('Transducer type too long.')
            value = value[:size]
        self._transducer_type = value

    @property
    def physical_dim(self):
        return self._physical_dim

    @physical_dim.setter
    def physical_dim(self, value):
        size = self._sizes[self.PHYSICAL_DIM]
        if len(value) > size:
            warnings.warn('Physical dimension is too long.')
            value = value[:size]
        self._physical_dim = value

    @property
    def physical_min(self):
        return self._physical_min

    @physical_min.setter
    def physical_min(self, value):
        self._physical_min = float(value)
        self._update_gain()

    @property
    def physical_max(self):
        return self._physical_max

    @physical_max.setter
    def physical_max(self, value):
        self._physical_max = float(value)
        self._update_gain()

    @property
    def digital_min(self):
        return self._digital_min

    @digital_min.setter
    def digital_min(self, value):
        self._digital_min = int(value)
        self._update_gain()

    @property
    def digital_max(self):
        return self._digital_max

    @digital_max.setter
    def digital_max(self, value):
        self._digital_max = int(value)
        self._update_gain()

    @property
    def prefiltering(self):
        return self._prefiltering

    @prefiltering.setter
    def prefiltering(self, value):
        size = self._sizes[self.PREFILTERING]
        if len(value) > size:
            warnings.warn('Prefiltering is too long.')
            value = value[:size]
        self._prefiltering = value

    @property
    def number_of_samples_in_data_record(self):
        return self._number_of_samples_in_data_record

    @number_of_samples_in_data_record.setter
    def number_of_samples_in_data_record(self, value):
        self._number_of_samples_in_data_record = value

    def __str__(self):
        return self.label

    def __repr__(self):
        return '<EDFSignal ' + self.label + '>'

    def _update_gain(self):
        '''
        Calculate gain from settings. Used to convert between digital
        and physical values.
        '''
        # TODO maybe set gain and offset only if physical dimenstion
        # is defined. Otherwise gain = 1 and offset = 0 to get
        # actual adc values in output
        dy = self.physical_max - self.physical_min
        dx = self.digital_max - self.digital_min
        self.gain = dy / dx

    def dig_to_phys(self, sample):
        '''
        Convert a digital value to a physical value.

        Follows the equation of a straight line:
            y = mx + b
        '''
        return (self.gain * sample) + self.physical_min


class Header:

    # Fields and sizes (i.e. number of bytes) as per the EDF
    # specification.
    _fields = ('version', 'subject_id', 'recording_id', 'startdate',
               'starttime', 'number_of_bytes_in_header', 'reserved',
               'number_of_data_records', 'duration_of_data_record',
               'number_of_signals')
    _sizes = (8, 80, 80, 8, 8, 8, 44, 8, 8, 4)

    def __init__(self, subject_id,  recording_id, signals,
                 duration_of_data_record, date_time=None, reserved=''):
        '''
        subject_id and recording_id must be object from those classes.

        signals must be a list of objects of class Signal

        reserved must only start with 'EDF+C' or 'EDF+D' if there is an
        annotations signal.

        duration_of_data_record recommended to be an integer value
        '''
        self.version = '0'
        self.subject_id = subject_id
        self.recording_id = recording_id
        self.reserved = reserved
        # number_of_data_records is a counter so it is important
        # to initialise to 0
        self.number_of_data_records = 0
        self.duration_of_data_record = duration_of_data_record
        self.number_of_signals = len(signals)
        self.number_of_bytes_in_header = (
                256 + (self.number_of_signals * 256))

        for signal in signals:
            signal.number_of_samples_in_data_record = (
                self.duration_of_data_record * signal.sampling_freq)
        self.signals = signals

        if date_time is None:
            date_time = datetime.now()
        self.startdate = date_time
        self.starttime = date_time

        # Not part of the specification
        nsamples = [signal.number_of_samples_in_data_record for signal
                    in self.signals]
        self.number_of_samples_in_data_record = np.sum(nsamples)

    def pack(self):
        '''
        Returns the header as a bytes object formatted as required by
        the EDF specification.
        '''
        main_hdr = ''
        for n in self._sizes:
            main_hdr += '{:<' + str(n) + '}'
        startdate = datetime.strftime(self.startdate, EDF_HDR_DATE_FMT)
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

        # The signals part of the EDF header expects each field for all
        # signals instead of all fields of one signal then all field of
        # the next signl, etc. This is annoying, because it would be
        # easy to conatenate headr signals, but instead we have to
        # loop each field.
        sig_hdr = ''
        for field in Signal._fields:
            for signal in self.signals:
                if field == 'label':
                    val = signal.label
                    size = Signal._sizes[Signal.LABEL]
                elif field == 'transducer_type':
                    val = signal.transducer_type
                    size = Signal._sizes[Signal.TRANSDUCER_TYPE]
                elif field == 'physical_dim':
                    val = signal.physical_dim
                    size = Signal._sizes[Signal.PHYSICAL_DIM]
                elif field == 'physical_min':
                    val = signal.physical_min
                    size = Signal._sizes[Signal.PHYSICAL_MIN]
                elif field == 'physical_max':
                    val = signal.physical_max
                    size = Signal._sizes[Signal.PHYSICAL_MAX]
                elif field == 'digital_min':
                    val = signal.digital_min
                    size = Signal._sizes[Signal.DIGITAL_MIN]
                elif field == 'digital_max':
                    val = signal.digital_max
                    size = Signal._sizes[Signal.DIGITAL_MAX]
                elif field == 'prefiltering':
                    val = signal.prefiltering
                    size = Signal._sizes[Signal.PREFILTERING]
                elif field == 'number_of_samples_in_data_record':
                    val = signal.number_of_samples_in_data_record
                    size = Signal._sizes[Signal.NSAMPLES]
                elif field == 'reserved':
                    val = signal._reserved
                    size = Signal._sizes[Signal.RESERVED]
                fmt = '{:<' + str(size) + '}'
                val = fmt.format(val)
                sig_hdr += val
        sig_hdr = sig_hdr.encode('ascii')
        assert len(sig_hdr) == self.number_of_signals * 256

        return main_hdr + sig_hdr

    @property
    def subject_id(self):
        return self._subject_id

    @subject_id.setter
    def subject_id(self, value):
        assert isinstance(value, SubjectId)
        self._subject_id = value

    @property
    def recording_id(self):
        return self._recording_id

    @recording_id.setter
    def recording_id(self, value):
        assert isinstance(value, RecordingId)
        self._recording_id = value

    @property
    def startdate(self):
        return self._startdate

    @startdate.setter
    def startdate(self, value):
        '''
        startdate must be a string of format 'yyyy-mm-dd' or a datetime
        object.
        '''
        if type(value) is str:
            value = datetime.strptime(value, ISO_DATE_FMT)
        self._startdate = value.date()

    @property
    def starttime(self):
        return self._starttime

    @starttime.setter
    def starttime(self, value):
        '''
        starttime must be a string of format 'H:M:S' or a datetime
        object.
        '''
        if type(value) is str:
            value = datetime.strptime(value, '%H:%M:%S')
        self._starttime = value.time()



if __name__ == '__main__':

    # s = Signal()
    sampling_freq = 200  # Hz

    # In analogy to human EEG, first channel is frontal (right) relative
    # to posterior (right), and 2nd channel is central (right) relative
    # to posterior (right).
    eeg1 = Signal(label='EEG F4-P4', physical_dim='uV',
                  physical_min=-300,
                  physical_max=300, digital_min=-2048,
                  digital_max=2047,
                  prefiltering='HP:0.5Hz LP:100Hz',
                  sampling_freq=sampling_freq)

    eeg2 = Signal(label='EEG C4-P4', physical_dim='uV',
                  physical_min=-300,
                  physical_max=300, digital_min=-2048,
                  digital_max=2047,
                  prefiltering='HP:0.5Hz LP:100Hz',
                  sampling_freq=sampling_freq)

    subject_id = SubjectId(code='X', sex='X', dob='X', name='X')

    recording_id = RecordingId(startdate=None, experiment_id='X',
                               investigator_id='X', equipment_code='X')

    signals = [eeg1, eeg2]

    header = Header(subject_id,  recording_id, signals,
                    duration_of_data_record=5, date_time=None,
                    reserved='')

    fname = "foofile.edf"

    edf = EdfWriter(fname, subject_id, recording_id, signals,
                    saving_period_s=5, date_time=None)

    a = np.arange(1000).astype('int16')
    b = a + 10000

    edf.write_data_record(np.r_[a, b])
    edf.close()
