#
# This file is protected by Copyright. Please refer to the COPYRIGHT file
# distributed with this source distribution.
#
# This file is part of REDHAWK core.
#
# REDHAWK core is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# REDHAWK core is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/.
#

import unittest
import tempfile
import shutil
import os
import numpy
import time

from ossie.utils import sb
from ossie.utils.bluefile import bluefile, bluefile_helpers
from ossie.utils.bulkio import bulkio_helpers

class BluefileTest(unittest.TestCase):

    def test_formWritePath (self):
        """
        Ensure that bluefile.form_write_path does not throw an exception on a
        filename with no path.
        """
        try:
            bluefile.form_write_path('out')
        except AttributeError:
            self.fail('form_write_path raises an exception with no path')

class BlueFileHelpers(unittest.TestCase):

    TYPEMAP = { 'B' : ('char', int),
                'I' : ('short', int),
                'L' : ('long', int),
                'F' : ('float', float),
                'D' : ('double', float) }

    def setUp(self):
        try:
            import bulkio
            globals()['bulkio'] = bulkio
        except ImportError:
            raise ImportError('BULKIO is required for this test')
        self._tempfiles = []

    def tearDown(self):
        for tempfile in self._tempfiles:
            try:
                os.unlink(tempfile)
            except:
                pass
        sb.release()

    def test_FileSink(self):
        self._test_FileSink('SB')
        self._test_FileSink('SI')
        self._test_FileSink('SL')
        self._test_FileSink('SF')
        self._test_FileSink('SD')

        self._test_FileSink('CB')
        self._test_FileSink('CI')
        self._test_FileSink('CL')
        self._test_FileSink('CF')
        self._test_FileSink('CD')

    def _tempfileName(self, name):
        filename = 'test_bluefile_%s.tmp' % name
        self._tempfiles.append(filename)
        return filename

    def _flatten(self, data):
        for real, imag in zip(data.real, data.imag):
            yield real
            yield imag

    def _test_FileSink(self, format):
        filename = self._tempfileName('sink_%s' % format)

        complexData = format.startswith('C')
        typecode = format[1]
        dataFormat, dataType = self.TYPEMAP[typecode]
        indata = [dataType(x) for x in xrange(16)]

        source = sb.DataSource(dataFormat=dataFormat)
        sink = sb.FileSink(filename, midasFile=True)
        source.connect(sink)
        sb.start()
        source.push(indata, complexData=complexData, EOS=True)
        sink.waitForEOS()

        hdr, outdata = bluefile.read(filename)
        self.assertEqual(hdr['format'], format)
        if complexData:
            if dataFormat in ('double', 'float'):
                outdata = list(self._flatten(outdata))
            else:
                outdata = outdata.flatten()
        self.assertTrue(numpy.array_equal(indata, outdata), msg="Format '%s' %s != %s" % (format, indata, outdata))

    def _generateSourceData(self, format, size):
        if format in ('CF', 'CD'):
            return [complex(x) for x in xrange(size)]

        complexData = format.startswith('C')
        typecode = format[1]
        dataFormat, dataType = self.TYPEMAP[typecode]

        samples = size
        if complexData:
            samples *= 2
        data = [dataType(x) for x in xrange(samples)]
        if complexData:
            data = numpy.reshape(data, (size,2))

        return data

    def _test_FileSource(self, format):
        filename = self._tempfileName('source_%s' % format)

        complexData = format.startswith('C')
        typecode = format[1]
        dataFormat, dataType = self.TYPEMAP[typecode]

        indata = self._generateSourceData(format, 16)
        hdr = bluefile.header(1000, format)
        bluefile.write(filename, hdr, indata)

        source = sb.FileSource(filename, midasFile=True, dataFormat=dataFormat)
        sink = sb.DataSink()
        source.connect(sink)
        sb.start()
        outdata = sink.getData(eos_block=True)
        if complexData:
            self.assertEqual(sink.sri().mode, 1)
            if dataFormat in ('float', 'double'):
                outdata = bulkio_helpers.bulkioComplexToPythonComplexList(outdata)
            else:
                outdata = numpy.reshape(outdata, (len(outdata)/2,2))
        else:
            self.assertEqual(sink.sri().mode, 0)
        self.assertTrue(numpy.array_equal(indata, outdata), msg='%s != %s' % (indata, outdata))

    def test_FileSource(self):
        self._test_FileSource('SB')
        self._test_FileSource('SI')
        self._test_FileSource('SL')
        self._test_FileSource('SF')
        self._test_FileSource('SD')

        self._test_FileSource('CB')
        self._test_FileSource('CI')
        self._test_FileSource('CL')
        self._test_FileSource('CF')
        self._test_FileSource('CD')

    def _test_FileSinkType2000(self, format, subsize):
        filename = self._tempfileName('sink_2000_%s' % format)

        complexData = format.startswith('C')
        typecode = format[1]
        dataFormat, dataType = self.TYPEMAP[typecode]

        sink = sb.FileSink(filename, midasFile=True)
        sb.start()

        # Manually create our own SRI, because DataSource doesn't support
        # setting the Y-axis fields
        sri = bulkio.sri.create('test_stream')
        if complexData:
            sri.mode = 1
        else:
            sri.mode = 0
        sri.subsize = subsize
        sri.ystart = subsize / -2.0
        sri.ydelta = 1.0
        sri.yunits = 3

        # Generate test data; unlike the type 1000 tests, we have to generate
        # input data compatible with CORBA because we're bypassing DataSource
        frames = 4
        samples = subsize * frames
        if complexData:
            samples *= 2
        if dataFormat == 'char':
            indata = numpy.arange(samples, dtype=numpy.int8)
            packet = indata.tostring()
        else:
            indata = [dataType(x) for x in xrange(samples)]
            packet = indata

        # Push the SRI and data directly to the sink's port
        port = sink.getPort(dataFormat + 'In')
        port.pushSRI(sri)
        port.pushPacket(packet, bulkio.timestamp.now(), True, sri.streamID)

        sink.waitForEOS()

        hdr, outdata = bluefile.read(filename)
        self.assertEqual(hdr['format'], format)
        self.assertEqual(hdr['subsize'], subsize)
        self.assertEqual(hdr['ystart'], sri.ystart)
        self.assertEqual(hdr['ydelta'], sri.ydelta)
        self.assertEqual(hdr['yunits'], sri.yunits)
        self.assertEqual(len(outdata), frames)

        if complexData:
            if dataFormat == 'float':
                indata = numpy.array(indata, dtype=numpy.float32).view(numpy.complex64)
                indata = numpy.reshape(indata, (-1, subsize))
            elif dataFormat == 'double':
                indata = numpy.array(indata, dtype=numpy.float64).view(numpy.complex128)
                indata = numpy.reshape(indata, (-1, subsize))
            else:
                indata = numpy.reshape(indata, (-1, subsize, 2))
        else:
            indata = numpy.reshape(indata, (-1, subsize))

        self.assertTrue(numpy.array_equal(indata, outdata), msg="Format '%s' %s != %s" % (format, indata, outdata))

    def test_FileSinkType2000(self):
        self._test_FileSinkType2000('SB', 16)
        self._test_FileSinkType2000('SI', 1024)
        self._test_FileSinkType2000('SL', 1024)
        self._test_FileSinkType2000('SF', 1024)
        self._test_FileSinkType2000('SD', 1024)

        self._test_FileSinkType2000('CB', 32)
        self._test_FileSinkType2000('CI', 512)
        self._test_FileSinkType2000('CL', 512)
        self._test_FileSinkType2000('CF', 512)
        self._test_FileSinkType2000('CD', 512)

    def _test_FileSourceType2000(self, format, subsize):
        filename = self._tempfileName('source_2000_%s' % format)

        complexData = format.startswith('C')
        typecode = format[1]
        dataFormat, dataType = self.TYPEMAP[typecode]

        frames = 4
        indata = [self._generateSourceData(format, subsize) for x in xrange(frames)]
        hdr = bluefile.header(2000, format, subsize=subsize)
        bluefile.write(filename, hdr, indata)

        source = sb.FileSource(filename, midasFile=True, dataFormat=dataFormat)
        sink = sb.DataSink()
        source.connect(sink)
        sb.start()
        outdata = sink.getData(eos_block=True)
        if complexData:
            if format == 'CF':
                outdata = numpy.array(outdata, dtype=numpy.float32).view(numpy.complex64)
                outdata = numpy.reshape(outdata, (-1, subsize))
            elif format == 'CD':
                outdata = numpy.array(outdata, dtype=numpy.float64).view(numpy.complex128)
                outdata = numpy.reshape(outdata, (-1, subsize))
            else:
                outdata = numpy.reshape(outdata, (-1, subsize, 2))
            self.assertEqual(sink.sri().mode, 1)
        else:
            self.assertEqual(sink.sri().mode, 0)

        self.assertTrue(numpy.array_equal(indata, outdata), msg="Format '%s' %s != %s" % (format, indata, outdata))

    def test_FileSourceType2000(self):
        self._test_FileSourceType2000('SB', 16)
        self._test_FileSourceType2000('SI', 1024)
        self._test_FileSourceType2000('SL', 1024)
        self._test_FileSourceType2000('SF', 1024)
        self._test_FileSourceType2000('SD', 1024)

        self._test_FileSourceType2000('CB', 16)
        self._test_FileSourceType2000('CI', 512)
        self._test_FileSourceType2000('CL', 512)
        self._test_FileSourceType2000('CF', 512)
        self._test_FileSourceType2000('CD', 512)

    def test_FileSourceTimecode(self):
        filename = self._tempfileName('source_timecode')

        # Create a ramp file with a known timestamp
        start = bulkio.timestamp.now()
        xdelta = 0.25
        hdr = bluefile.header(1000, 'SF', xdelta=xdelta)
        hdr['timecode'] = bluefile_helpers.unix_to_j1950(start.twsec + start.tfsec)
        bluefile.write(filename, hdr, numpy.arange(1024))

        # Bytes per push is chosen specifically to require multiple packets
        source = sb.FileSource(filename, bytesPerPush=2048, midasFile=True, dataFormat='float')
        sink = sb.DataSink()
        source.connect(sink)
        sb.start()

        # There should have been at least two push packets (plus one more for
        # the end-of-stream, but that's not strictly required)
        outdata, tstamps = sink.getData(eos_block=True, tstamps=True)
        self.assertTrue(len(tstamps) >= 2)

        # Check that the first timestamp (nearly) matches the timestamp created
        # above
        offset, ts = tstamps[0]
        self.assertAlmostEqual(start - ts, 0.0)

        # Check that the synthesized timestamps match our expectations
        for index in xrange(1, len(tstamps)):
            offset, tnext = tstamps[1]
            self.assertAlmostEqual(tnext - ts, offset*xdelta)

    def test_FileSinkTimecode(self):
        filename = self._tempfileName('source_timecode')

        # Create a source with a known start time
        time_in = time.time()
        source = sb.DataSource(dataFormat='float', startTime=time_in)
        sink = sb.FileSink(filename, midasFile=True)
        source.connect(sink)
        sb.start()

        # The data isn't important, other than to cause a pushPacket with the
        # initial timestamp
        source.push(range(16), EOS=True)
        sink.waitForEOS()

        # Read back the timecode from the output file
        hdr = bluefile.readheader(filename)
        time_out = bluefile_helpers.j1950_to_unix(hdr['timecode'])
        self.assertAlmostEqual(time_in, time_out)
