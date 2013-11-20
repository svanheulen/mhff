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


def run_ge(pmo, scale):
    file_address = pmo.tell()
    index_offset = 0
    vertices = []
    faces = []
    vertex_address = None
    index_address = None
    vertex_format = None
    position_trans = None
    normal_trans = None
    color_trans = None
    texture_trans = None
    weight_trans = None
    index_format = None
    face_order = None
    while True:
        command = array.array('I', pmo.read(4))[0]
        command_type = command >> 24
        # NOP - No Operation
        if command_type == 0x00:
            pass
        # VADDR - Vertex Address (BASE)
        elif command_type == 0x01:
            if vertex_address is not None:
                index_offset = len(vertices)
            vertex_address = file_address + (command & 0xffffff)
        # IADDR - Index Address (BASE)
        elif command_type == 0x02:
            index_address = file_address + (command & 0xffffff)
        # PRIM - Primitive Kick
        elif command_type == 0x04:
            primative_type = (command >> 16) & 7
            index_count = command & 0xffff
            command_address = pmo.tell()
            index = range(len(vertices) - index_offset, len(vertices) + index_count - index_offset)
            if index_format is not None:
                index = array.array(index_format)
                pmo.seek(index_address)
                index.fromfile(pmo, index_count)
                index_address = pmo.tell()
            vertex_size = struct.calcsize(vertex_format)
            for i in index:
                pmo.seek(vertex_address + vertex_size * i)
                raw_vertex = list(struct.unpack(vertex_format, pmo.read(vertex_size)))
                vertex = {}
                vertex['z'] = (raw_vertex.pop() / position_trans) * scale[2]
                vertex['y'] = (raw_vertex.pop() / position_trans) * scale[1]
                vertex['x'] = (raw_vertex.pop() / position_trans) * scale[0]
                if normal_trans is not None:
                    vertex['k'] = raw_vertex.pop() / normal_trans
                    vertex['j'] = raw_vertex.pop() / normal_trans
                    vertex['i'] = raw_vertex.pop() / normal_trans
                if color_trans is not None:
                    raw_vertex.pop() # NOTE: the OBJ format does not support vertex colors
                if texture_trans is not None:
                    vertex['v'] = raw_vertex.pop() / texture_trans
                    vertex['u'] = raw_vertex.pop() / texture_trans
                if weight_trans is not None:
                    pass # NOTE: the OBJ format does not support vertex weights
                if len(vertices) <= (i + index_offset):
                    vertices.extend([None] * (i + index_offset + 1 - len(vertices)))
                vertices[i + index_offset] = vertex
            pmo.seek(command_address)
            r = range(index_count - 2)
            if primative_type == 3:
                r = range(0, index_count, 3)
            elif primative_type != 4:
                ValueError('Unsupported primative type: 0x{:02X}'.format(primative_type))
            for i in r:
                face = {'v3': index[i+2] + index_offset}
                if ((i + face_order) % 2) or ((primative_type == 3) and face_order):
                    face['v2'] = index[i] + index_offset
                    face['v1'] = index[i+1] + index_offset
                else:
                    face['v1'] = index[i] + index_offset
                    face['v2'] = index[i+1] + index_offset
                faces.append(face)
        # RET - Return from Call
        elif command_type == 0x0b:
            break
        # BASE - Base Address Register
        elif command_type == 0x10:
            pass
        # VTYPE - Vertex Type
        elif command_type == 0x12:
            vertex_format = ''
            weight = (command >> 9) & 3
            if weight != 0:
                count = ((command >> 14) & 7) + 1
                vertex_format += str(count) + (None, 'B', 'H', 'f')[weight]
                weight_trans = (None, 0x80, 0x8000, 1)[weight]
            bypass_transform = (command >> 23) & 1
            texture = command & 3
            if texture != 0:
                vertex_format += (None, '2B', '2H', '2f')[texture]
                texture_trans = 1
                if not bypass_transform:
                    texture_trans = (None, 0x80, 0x8000, 1)[texture]
            color = (command >> 2) & 7
            if color != 0:
                vertex_format += (None, None, None, None, 'H', 'H', 'H', 'I')[color]
                color_trans = (None, None, None, None, 'rgb565', 'rgba5', 'rgba4', 'rgba8')[color]
            normal = (command >> 5) & 3
            if normal != 0:
                vertex_format += (None, '3b', '3h', '3f')[normal] # NOTE: when bypassing transform Z may be unsigned
                normal_trans = 1
                if not bypass_transform:
                    normal_trans = (None, 0x7f, 0x7fff, 1)[normal]
            position = (command >> 7) & 3
            if position != 0:
                if bypass_transform:
                    vertex_format += (None, '2bB', '2hH', '3f')[position] # TODO: handle float Z clamping
                    position_trans = 1
                else:
                    vertex_format += (None, '3b', '3h', '3f')[position]
                    position_trans = (None, 0x7f, 0x7fff, 1)[position]
            index_format = (None, 'B', 'H', 'I')[(command >> 11) & 3]
            if (command >> 18) & 7 > 0:
                raise ValueError('Can not handle morphing')
        # ??? - Offset Address (BASE)
        elif command_type == 0x13:
            pass
        # ??? - Origin Address (BASE)
        elif command_type == 0x14:
            pass
        # FFACE - Front Face Culling Order
        elif command_type == 0x9b:
            face_order = command & 1
        else:
            raise ValueError('Unknown GE command: 0x{:02X}'.format(command_type))
    return vertices, faces


def create_mesh(obj, offsets, mesh):
    for i in range(len(mesh)):
        v_old = offsets['v']
        vt_old = offsets['vt']
        vn_old = offsets['vn']
        obj.write('usemtl texture{:02d}\n'.format(mesh[i][2]))
        for vertex in mesh[i][0]:
            obj.write('v {x:f} {y:f} {z:f}\n'.format(**vertex))
            offsets['v'] += 1
            if vertex.get('u') is not None:
                obj.write('vt {u:f} {v:f}\n'.format(**vertex))
                offsets['vt'] += 1
            if vertex.get('i') is not None:
                obj.write('vn {i:f} {j:f} {k:f}\n'.format(**vertex))
                offsets['vn'] += 1
        for face in mesh[i][1]:
            obj.write('f {:d}'.format(face['v1'] + v_old))
            if mesh[i][0][face['v1']].get('u') is not None:
                obj.write('/{:d}/'.format(face['v1'] + vt_old))
            else:
                obj.write('//')
            if mesh[i][0][face['v1']].get('i') is not None:
                obj.write('{:d}'.format(face['v1'] + vn_old))
            obj.write(' {:d}'.format(face['v2'] + v_old))
            if mesh[i][0][face['v2']].get('u') is not None:
                obj.write('/{:d}/'.format(face['v2'] + vt_old))
            else:
                obj.write('//')
            if mesh[i][0][face['v2']].get('i') is not None:
                obj.write('{:d}'.format(face['v2'] + vn_old))
            obj.write(' {:d}'.format(face['v3'] + v_old))
            if mesh[i][0][face['v3']].get('u') is not None:
                obj.write('/{:d}/'.format(face['v3'] + vt_old))
            else:
                obj.write('//')
            if mesh[i][0][face['v3']].get('i') is not None:
                obj.write('{:d}'.format(face['v3'] + vn_old))
            obj.write('\n')


def convert_mh3_pmo(pmo, obj):
    offsets = {'v': 1, 'vt': 1, 'vn': 1}
    pmo_header = struct.unpack('I4f2H8I', pmo.read(0x38))
    for i in range(pmo_header[5]):
        mesh = []
        obj.write('g mesh{:02d}\n'.format(i))
        pmo.seek(pmo_header[7] + i * 0x30)
        mesh_header = struct.unpack('8f2I4H', pmo.read(0x30))
        scale = mesh_header[:3]
        for j in range(mesh_header[12]):
            pmo.seek(pmo_header[8] + ((mesh_header[13] + j) * 0x10))
            vertex_group_header = struct.unpack('2BH3I', pmo.read(0x10))
            pmo.seek(pmo_header[11] + (mesh_header[11] + vertex_group_header[0]) * 16)
            material = struct.unpack('4I', pmo.read(16))[2]
            pmo.seek(pmo_header[12] + vertex_group_header[3])
            mesh.append(run_ge(pmo, scale) + (material,))
        create_mesh(obj, offsets, mesh)


def convert_mh2_pmo(pmo, obj):
    offsets = {'v': 1, 'vt': 1, 'vn': 1}
    pmo_header = struct.unpack('I4f2H8I', pmo.read(0x38))
    scale = pmo_header[2:5]
    for i in range(pmo_header[5]):
        mesh = []
        obj.write('g mesh{:02d}\n'.format(i))
        pmo.seek(pmo_header[7] + i * 0x20)
        mesh_header = struct.unpack('2f2I4H2I', pmo.read(0x20))
        for j in range(mesh_header[6]):
            pmo.seek(pmo_header[8] + ((mesh_header[7] + j) * 0x10))
            vertex_group_header = struct.unpack('2BH3I', pmo.read(0x10))
            pmo.seek(pmo_header[11] + (mesh_header[5] + vertex_group_header[0]) * 16)
            material = struct.unpack('4I', pmo.read(16))[2]
            pmo.seek(pmo_header[12] + vertex_group_header[3])
            mesh.append(run_ge(pmo, scale) + (material,))
        create_mesh(obj, offsets, mesh)


def convert_pmo(pmo_file, mtl_file, obj_file):
    with open(pmo_file, 'rb') as pmo, open(obj_file, 'w') as obj:
        type, version = struct.unpack('4s4s', pmo.read(8))
        if type == b'pmo\x00' and version == b'102\x00':
            obj.write('mtllib {}\n'.format(mtl_file))
            convert_mh3_pmo(pmo, obj)
        elif type == b'pmo\x00' and version == b'1.0\x00':
            obj.write('mtllib {}\n'.format(mtl_file))
            convert_mh2_pmo(pmo, obj)
        else:
            raise ValueError('Invalid PMO file')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts a Monster Hunter PMO file to Wavefront OBJ format')
    parser.add_argument('pmofile', help='PMO input file')
    parser.add_argument('mtlfile', help='MTL input file')
    parser.add_argument('outputfile', help='OBJ output file')
    args = parser.parse_args()
    convert_pmo(args.pmofile, args.mtlfile, args.outputfile)

