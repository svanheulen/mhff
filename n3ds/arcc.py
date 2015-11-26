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
import array
import struct

from Crypto.Cipher import Blowfish


def decrypt(buff, key):
    buff = array.array('I', buff)
    buff.byteswap()
    buff = array.array('I', Blowfish.new(key).decrypt(buff.tobytes()))
    buff.byteswap()
    return buff.tobytes()

def decrypt_arcc(arcc_file, key, arc_file):
    arcc = open(arcc_file, 'rb')
    magic, version, file_count, unknown = struct.unpack('4sHHI', arcc.read(12))
    if magic != b'ARCC':
        raise ValueError('header: invalid magic')
    if version != 0x11:
        raise ValueError('header: invalid version')
    arc = open(arc_file, 'wb')
    arc.write(struct.pack('4sHHI', b'ARCC', 0x11, file_count, unknown))
    toc = decrypt(arcc.read(file_count * 0x50), key)
    arc.write(toc)
    for i in range(file_count):
        size, offset = struct.unpack('68xI4xI', toc[i*0x50:(i+1)*0x50])
        arcc.seek(offset)
        arc.seek(offset)
        arc.write(decrypt(arcc.read(size), key))
    arcc.close()
    arc.close()

parser = argparse.ArgumentParser(description='Decrypts an ARCC file from MHX')
parser.add_argument('inputfile', help='ARCC input file')
parser.add_argument('key', help='encryption key')
parser.add_argument('outputfile', help='ARC output file')
args = parser.parse_args()

decrypt_arcc(args.inputfile, args.key, args.outputfile)

