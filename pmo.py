#!/usr/bin/python3

# Copyright 2013 Seth VanHeulen
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
import sys


def run_ge(commands):
    vertex_format = None
    index_format = None
    transform = [1, 1, 1]
    primatives = []
    order = None
    for command in commands:
        c = command >> 24;
        if c == 0x04:
            primatives.append([command & 0xffff, (command >> 16) & 7, order])
        elif c == 0x12:
            texture = (None, 'b', 'h', 'f')[command & 3]
            color = (None, None, None, None, '2x', '2x', '2x', '4x')[(command >> 2) & 7]
            normal = (None, 'b', 'h', 'f')[(command >> 5) & 3]
            position = (None, 'b', 'h', 'f')[(command >> 7) & 3]
            weight = (None, 1, 2, 4)[(command >> 9) & 3]
            index_format = (None, 'B', 'H', None)[(command >> 11) & 3]
            skinning = ((command >> 14) & 7) + 1
            morphing = ((command >> 18) & 7) + 1
            bypass = (command >> 23) & 1
            vertex_format = ''
            if weight is not None:
                vertex_format += '%dx' % (skinning * weight)
            if texture is not None:
                vertex_format += '2%s' % texture
                if bypass == 0:
                    transform[0] = 1 << (struct.calcsize(texture) * 8 - 1)
            if color is not None:
                vertex_format += color
            if normal is not None:
                vertex_format += '3%s' % normal
                if bypass == 0:
                    transform[1] = (1 << (struct.calcsize(normal) * 8 - 1)) - 1
            if position is not None:
                vertex_format += '3%s' % position
                if bypass == 0:
                    transform[2] = (1 << (struct.calcsize(position) * 8 - 1)) - 1
        elif c == 0x9b:
            order = command & 1
    return vertex_format, index_format, transform, primatives

def convert_pmo(pmo_file, out_file):
    with open(pmo_file, 'rb') as pmo, open(out_file, 'w') as out:
        header = struct.unpack('4s4sI4f2H2I4x3I8x', pmo.read(0x40))
        pmo.seek(header[10])
        section = []
        for i in range((header[11] - header[10]) // 0x10):
            section.append(struct.unpack('2BH3I', pmo.read(0x10)))
        vertex_offset = 1
        for s in section:
            pmo.seek(header[13] + s[3])
            vertex_format, index_format, transform, primatives = run_ge(array.array('I', pmo.read(s[4] - s[3])))
            vertex_size = struct.calcsize(vertex_format)
            vertex_count = (s[5] - s[4]) // vertex_size
            if s[5] == 0:
                vertex_count = 0
                for p in primatives:
                    vertex_count += p[0]
            pmo.seek(header[13] + s[4])
            for i in range(vertex_count):
                vertex = struct.unpack(vertex_format, pmo.read(vertex_size))
                out.write('vt %f %f\n' % (vertex[0] / transform[0], vertex[1] / transform[0]))
                out.write('vn %f %f %f\n' % (vertex[2] / transform[1], vertex[3] / transform[1], vertex[4] / transform[1]))
                out.write('v %f %f %f\n' % (vertex[5] / transform[2], vertex[6] / transform[2], vertex[7] / transform[2]))
            pmo.seek(header[13] + s[5])
            for p in primatives:
                index = range(p[0])
                if index_format is not None:
                    index = array.array(index_format)
                    index.fromfile(pmo, p[0])
                index = [i + vertex_offset for i in index]
                r = range(p[0]-2)
                if p[1] == 3:
                    r = range(0, p[0], 3)
                for i in r:
                    if p[2] == 1:
                        out.write('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % (index[i], index[i], index[i], index[i+1], index[i+1], index[i+1], index[i+2], index[i+2], index[i+2]))
                    else:
                        out.write('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % (index[i+1], index[i+1], index[i+1], index[i], index[i], index[i], index[i+2], index[i+2], index[i+2]))
            vertex_offset += vertex_count

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts a Monster Hunter pmo model file to Wavefront OBJ format')
    parser.add_argument('pmofile', help='pmo model file to convert')
    parser.add_argument('outfile', help='OBJ output file')
    args = parser.parse_args()
    convert_pmo(args.pmofile, args.outfile)

