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
import os
import struct

from PIL import Image


def deblock(mode, width, data):
    bw = (8, 8, 8, 4, 32, 16, 8, 4, 4, 4, 4)[mode]
    bh = (8, 8, 8, 8, 8, 8, 8, 8, 4, 4, 4)[mode]
    data = array.array('I', data)
    new = array.array('I')
    for i in range(len(data)):
        x = i % width
        y = i // width
        xb = x // bw
        x %= bw
        yb = y // bh
        y %= bh
        offset = bw*bh*xb + width*bh*yb + bw*y + x
        new.append(data[offset])
    return new.tobytes()


def decode(mode, data):
    if mode == 0:
        data = array.array('H', data)
        new = bytearray()
        for i in data:
            new.append(round((i & 31) * (255 / 31)))
            new.append(round((i >> 5 & 63) * (255 / 63)))
            new.append(round((i >> 11 & 31) * (255 / 31)))
            new.append(255)
        return bytes(new)
    if mode == 1:
        data = array.array('H', data)
        new = bytearray()
        for i in data:
            new.append(round((i & 31) * (255 / 31)))
            new.append(round((i >> 5 & 31) * (255 / 31)))
            new.append(round((i >> 10 & 31) * (255 / 31)))
            new.append((i >> 15) * 255)
        return bytes(new)
    if mode == 2:
        new = bytearray()
        for i in data:
            new.append((i & 15) * 17)
            new.append((i >> 4) * 17)
        return bytes(new)
    if mode == 3:
        return data
    if mode == 4:
        new = bytearray()
        for i in data:
            new.append(i & 15)
            new.append(i >> 4)
        return bytes(new)
    if mode == 5:
        return data
    if mode == 6:
        return array.array('H', data)
    if mode == 7:
        return array.array('I', data)
    if mode == 8:
        new = bytearray()
        for i in range(0, len(data), 8):
            c = [decode(0, data[i+4:i+6])]
            c.append(decode(0, data[i+6:i+8]))
            temp = array.array('H', data[i+4:i+8])
            if temp[0] > temp[1]:
                c.append(bytes([(2*c[0][0]+c[1][0])//3, (2*c[0][1]+c[1][1])//3, (2*c[0][2]+c[1][2])//3, 255]))
                c.append(bytes([(c[0][0]+2*c[1][0])//3, (c[0][1]+2*c[1][1])//3, (c[0][2]+2*c[1][2])//3, 255]))
            else:
                c.append(bytes([(c[0][0]+c[1][0])//2, (c[0][1]+c[1][1])//2, (c[0][2]+c[1][2])//2, 255]))
                c.append(b'\x00\x00\x00\xff')
            for d in data[i:i+4]:
                new.extend(c[d & 3])
                new.extend(c[d >> 2 & 3])
                new.extend(c[d >> 4 & 3])
                new.extend(c[d >> 6 & 3])
        return bytes(new)
    if mode == 9:
        # TODO - DXT3 format
        return None
    if mode == 10:
        # TODO - DXT5 format
        return None
    return None


def convert_tmh(tmh_file, mtl_file):
    with open(tmh_file, 'rb') as tmh, open(mtl_file, 'w') as mtl:
        tmh_header = struct.unpack('8s2I', tmh.read(16))
        if tmh_header[0] != b'.TMH0.14':
            print('Not a valid TMH file.')
            return
        for i in range(tmh_header[1]):
            image_header = struct.unpack('4I', tmh.read(16))
            pixel_header = struct.unpack('3I2H', tmh.read(16))
            pixel_data = decode(pixel_header[2], tmh.read(pixel_header[0] - 16))
            if image_header[3] == 1:
                clut_header = struct.unpack('4I', tmh.read(16))
                clut_data = decode(clut_header[2], tmh.read(clut_header[0] - 16))
                new = bytearray()
                for p in pixel_data:
                    new.extend(clut_data[p*4:p*4+4])
                pixel_data = bytes(new)
            pixel_data = deblock(pixel_header[2], pixel_header[3], pixel_data)
            image_format = 'RGBA'
            if pixel_header[2] > 7:
                image_format = 'BGRA'
            image = Image.frombytes('RGBA', pixel_header[3:], pixel_data, 'raw', image_format)
            dirname = os.path.dirname(mtl_file)
            basename = os.path.basename(mtl_file).replace('.mtl', '')
            mtl.write('newmtl texture{:02d}\n'.format(i))
            mtl.write('Ka 1.0 1.0 1.0\n')
            mtl.write('Kd 1.0 1.0 1.0\n')
            mtl.write('Ks 0.0 0.0 0.0\n')
            mtl.write('illum 1\n')
            mtl.write('map_Ka {}{:02d}.png\n'.format(basename, i))
            mtl.write('map_Kd {}{:02d}.png\n'.format(basename, i))
            image.transpose(Image.FLIP_TOP_BOTTOM).save('{}{:02d}.png'.format(os.path.join(dirname, basename), i))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract all textures from a TMH texture package file')
    parser.add_argument('inputfile', help='TMH input file')
    parser.add_argument('outputfile', help='MTL output file')
    args = parser.parse_args()
    convert_tmh(args.inputfile, args.outputfile)

