#!/usr/bin/python

# Copyright 2015 Seth VanHeulen
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
import os
import struct
import zlib


parser = argparse.ArgumentParser(description='Extracts an ARC file from Monster Hunter 4 Ultimate')
parser.add_argument('inputfile', type=argparse.FileType('rb'), help='ARC input file')
args = parser.parse_args()

header = struct.unpack('IHHI', args.inputfile.read(12))
for i in range(header[2]):
    entry = struct.unpack('64sIIII', args.inputfile.read(0x50))
    pos = args.inputfile.tell()
    args.inputfile.seek(entry[4])
    data = args.inputfile.read(entry[2])
    args.inputfile.seek(pos)
    name = '{}.{:08X}'.format(os.path.join(*entry[0].decode().strip('\x00').split('\\')), entry[1])
    os.makedirs(os.path.dirname(name), exist_ok=True)
    open(name, 'wb').write(zlib.decompress(data))
args.inputfile.close()

