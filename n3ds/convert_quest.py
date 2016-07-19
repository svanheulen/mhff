#!/usr/bin/python

# Copyright 2016 Seth VanHeulen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import struct
import zlib


def convert_quest(arc_file, output_file):
    arc = open(arc_file, 'rb').read()
    count = struct.unpack_from('H', arc, 6)[0]
    compressed_size, offset = struct.unpack_from('I4xI', arc, 12 + (count - 1) * 0x50 + 68)
    data = zlib.decompress(arc[offset:offset+compressed_size])
    data = data[:0x138] + data[0x138:0x138+68]*4 + data[0x138:]
    size = len(data)
    data = zlib.compress(data)
    with open(output_file, 'wb') as output:
        output.write(arc)
        output.seek(12 + (count - 1) * 0x50 + 68)
        output.write(struct.pack('II', len(data), size))
        output.seek(offset)
        output.write(data)

parser = argparse.ArgumentParser(description='Converts a MHX quest file to work with MHGen')
parser.add_argument('inputfile', help='Japanese quest input file')
parser.add_argument('outputfile', help='quest output file')
args = parser.parse_args()

convert_quest(args.inputfile, args.outputfile)

