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


def run_ge(commands, pmo, obj, offset):
    vertex_address = None
    index_address = None
    primative = []
    base_address = None
    vertex_type = {}
    offset_address = None
    face_order = None
    for command in commands:
        command_type = command >> 24
        if command_type == 0x01:
            vertex_address = command & 0xffffff
        elif command_type == 0x02:
            index_address = command & 0xffffff
        elif command_type == 0x04:
            primative.append({'type': (command >> 16) & 7, 'count': command & 0xffff, 'order': face_order})
        elif command_type == 0x10:
            base_address == command & 0xffffff
        elif command_type == 0x12:
            vertex_type['texture'] = command & 3
            vertex_type['color'] = (command >> 2) & 7
            vertex_type['normal'] = (command >> 5) & 3
            vertex_type['position'] = (command >> 7) & 3
            vertex_type['weight'] = (command >> 9) & 3
            vertex_type['index'] = (command >> 11) & 3
            vertex_type['skinning'] = ((command >> 14) & 7) + 1
            vertex_type['morphing'] = ((command >> 18) & 7) + 1
            vertex_type['bypass'] = (command >> 23) & 1
        elif command_type == 0x13:
            offset_address = command & 0xffffff
        elif command_type == 0x9b:
            face_order = command & 1
    vertex_format = ''
    transform = [None, 1, 1, 1]
    if vertex_type['weight'] != 0:
        vertex_format += str(vertex_type['skinning']) + (None, 'B', 'H', 'f')[vertex_type['weight']]
        transform[0] = (None, 0x80, 0x8000, 1)[vertex_type['weight']]
    if vertex_type['texture'] != 0:
        vertex_format += '2' + (None, 'B', 'H', 'f')[vertex_type['texture']]
        if vertex_type['bypass'] == 0:
            transform[1] = (None, 0x80, 0x8000, 1)[vertex_type['texture']]
    if vertex_type['color'] != 0:
        vertex_format += (None, None, None, None, 'H', 'H', 'H', 'I')[vertex_type['color']]
    if vertex_type['normal'] != 0:
        vertex_format += '3' + (None, 'b', 'h', 'f')[vertex_type['normal']]
        if vertex_type['bypass'] == 0:
            transform[2] = (None, 0x7f, 0x7fff, 1)[vertex_type['normal']]
    if vertex_type['position'] != 0:
        vertex_format += '3' + (None, 'b', 'h', 'f')[vertex_type['position']]
        if vertex_type['bypass'] == 0:
            transform[3] = (None, 0x7f, 0x7fff, 1)[vertex_type['position']]
    vertex_size = struct.calcsize(vertex_format)
    vertex_data = None
    if index_address is not None:
        vertex_data = pmo.read(index_address - vertex_address)
        vertex_data = vertex_data[:(len(vertex_data) // vertex_size) * vertex_size]
    else:
        vertex_data_size = 0
        for p in primative:
            vertex_data_size += p['count'] * vertex_size
        vertex_data = pmo.read(vertex_data_size)
    v_offset = 0
    vn_offset = 0
    vt_offset = 0
    for i in range(0, len(vertex_data), vertex_size):
        vertex = list(struct.unpack(vertex_format, vertex_data[i:i+vertex_size]))
        if vertex_type['weight'] is not 0:
            for w in range(vertex_type['skinning']):
                unused = vertex.pop(0) / transform[0]
        if vertex_type['texture'] is not 0:
            u = vertex.pop(0) / transform[1]
            v = vertex.pop(0) / transform[1]
            vt_offset += 1
            obj.write('vt %f %f\n' % (u, v))
        if vertex_type['color'] != 0:
            unused = vertex.pop(0)
        if vertex_type['normal'] != 0:
            i = vertex.pop(0) / transform[2]
            j = vertex.pop(0) / transform[2]
            k = vertex.pop(0) / transform[2]
            vn_offset += 1
            obj.write('vn %f %f %f\n' % (i, j, k))
        if vertex_type['position'] != 0:
            x = vertex.pop(0) / transform[3]
            y = vertex.pop(0) / transform[3]
            z = vertex.pop(0) / transform[3]
            v_offset += 1
            obj.write('v %f %f %f\n' % (x, y, z))
    for p in primative:
        index = range(p['count'])
        if vertex_type['index'] != 0:
            index = array.array((None, 'B', 'H', 'I')[vertex_type['index']])
            index.fromfile(pmo, p['count'])
        r = range(p['count'] - 2)
        if p['type'] == 3:
            r = range(0, p['count'], 3)
        for i in r:
            one = ['', '', '']
            two = ['', '', '']
            three = ['', '', '']
            if vertex_type['position'] != 0:
                one[0] = index[i] + offset[0]
                two[0] = index[i+1] + offset[0]
                three[0] = index[i+2] + offset[0]
            if vertex_type['texture'] != 0:
                one[1] = index[i] + offset[1]
                two[1] = index[i+1] + offset[1]
                three[1] = index[i+2] + offset[1]
            if vertex_type['normal'] != 0:
                one[2] = index[i] + offset[2]
                two[2] = index[i+1] + offset[2]
                three[2] = index[i+2] + offset[2]
            if p['order'] == 1:
                obj.write('f %s/%s/%s %s/%s/%s %s/%s/%s\n' % tuple(one + two + three))
            else:
                obj.write('f %s/%s/%s %s/%s/%s %s/%s/%s\n' % tuple(two + one + three))
    return [offset[0] + v_offset, offset[1] + vt_offset, offset[2] + vn_offset]


def convert_pmo(pmo_file, mtl_file, obj_file):
    with open(pmo_file, 'rb') as pmo, open(obj_file, 'w') as obj:
        header = struct.unpack('4s4sI4f2H8I', pmo.read(0x40))
        offset = [1, 1, 1]
        obj.write('mtllib %s\n' % mtl_file)
        for i in range(header[7]):
            pmo.seek(header[9] + i * 0x30)
            object_header = struct.unpack('8f2I4H', pmo.read(0x30))
            obj.write('g group%04d\n' % i)
            for j in range(object_header[12]):
                pmo.seek(header[10] + ((object_header[13] + j) * 0x10))
                group_header = struct.unpack('2BH3I', pmo.read(0x10))
                pmo.seek(header[13] + ((object_header[11] + group_header[0]) * 0x10))
                material_header = struct.unpack('4I', pmo.read(0x10))
                obj.write('usemtl texture%04d\n' % material_header[2])
                pmo.seek(header[14] + group_header[3])
                commands = array.array('I', pmo.read(group_header[4] - group_header[3]))
                offset = run_ge(commands, pmo, obj, offset)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts a Monster Hunter pmo model file to Wavefront OBJ format')
    parser.add_argument('pmofile', help='pmo model file to convert')
    parser.add_argument('mtlfile', help='MTL file to use')
    parser.add_argument('objfile', help='OBJ output file')
    args = parser.parse_args()
    convert_pmo(args.pmofile, args.mtlfile, args.objfile)

