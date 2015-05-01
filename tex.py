#!/usr/bin/python3

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

import array
import struct
import sys

from PIL import Image


modifier_tables = (
    (2, 8, -2, -8),
    (5, 17, -5, -17),
    (9, 29, -9, -29),
    (13, 42, -13, -42),
    (18, 60, -18, -60),
    (24, 80, -24, -80),
    (33, 106, -33, -106),
    (47, 183, -47, -183)
)

def decode_etc1(data, width, alpha=False):
    data = array.array('I', data)
    block_index = 0
    pixel_count = len(data) * 4
    if not alpha:
        pixel_count *= 2
    new = array.array('I', range(pixel_count))
    while len(data) != 0:
        alpha_part1 = 0
        alpha_part2 = 0
        if alpha:
            alpha_part1 = data.pop(0)
            alpha_part2 = data.pop(0)
        pixel_indices = data.pop(0)
        block_info = data.pop(0)
        bc1 = [0, 0, 0]
        bc2 = [0, 0, 0]
        if block_info & 2 == 0:
            bc1[0] = block_info >> 28 & 15
            bc1[1] = block_info >> 20 & 15
            bc1[2] = block_info >> 12 & 15
            bc1 = [(x << 4) + x for x in bc1]
            bc2[0] = block_info >> 24 & 15
            bc2[1] = block_info >> 16 & 15
            bc2[2] = block_info >> 8 & 15
            bc2 = [(x << 4) + x for x in bc2]
        else:
            bc1[0] = block_info >> 27 & 31
            bc1[1] = block_info >> 19 & 31
            bc1[2] = block_info >> 11 & 31
            bc2[0] = block_info >> 24 & 7
            bc2[1] = block_info >> 16 & 7
            bc2[2] = block_info >> 8 & 7
            bc2 = [x + ((y > 3) and (y - 8) or y) for x, y in zip(bc1, bc2)]
            bc1 = [(x >> 2) + (x << 3) for x in bc1]
            bc2 = [(x >> 2) + (x << 3) for x in bc2]
        flip = block_info & 1
        tcw1 = block_info >> 5 & 7
        tcw2 = block_info >> 2 & 7
        for i in range(16):
            mi = ((pixel_indices >> i) & 1) + ((pixel_indices >> (i + 15)) & 2)
            c = None
            if flip == 0 and i < 8 or flip != 0 and (i // 2 % 2) == 0:
                m = modifier_tables[tcw1][mi]
                c = [max(0, min(255, x + m)) for x in bc1]
            else:
                m = modifier_tables[tcw2][mi]
                c = [max(0, min(255, x + m)) for x in bc2]
            c.append(255)
            offset = block_index % 4
            x = (block_index - offset) % (width // 2) * 2
            y = (block_index - offset) // (width // 2) * 8
            if offset & 1:
                x += 4
            if offset & 2:
                y += 4
            x += i // 4
            y += i % 4
            new[x + y * width] = struct.unpack('I', bytes(c))[0]
        block_index += 1
    return new.tobytes()

def convert_tex(tex_file, png_file):
    tex = open(tex_file, 'rb')

    magic = tex.read(4)
    header = array.array('I', tex.read(12))

    constant = header[0] & 0xfff
    unknown1 = (header[0] >> 12) & 0xfff
    size_shift = (header[0] >> 24) & 0xf
    unknown2 = (header[0] >> 28) & 0xf

    mipmap_count = header[1] & 0x3f
    width = (header[1] >> 6) & 0x1fff
    height = (header[1] >> 19) & 0x1fff

    unknown3 = header[2] & 0xff
    unknown4 = (header[2] >> 8) & 0xff
    unknown5 = (header[2] >> 16) & 0x1fff

    offsets = array.array('I', tex.read(4*mipmap_count))

    if unknown4 == 11:
        pixel_data = decode_etc1(tex.read(width*height//2), width)
        image = Image.frombytes('RGBA', (width, height), pixel_data, 'raw', 'RGBA')
        image.save(png_file)
    elif unknown4 == 12:
        pixel_data = decode_etc1(tex.read(width*height), width, True)
        image = Image.frombytes('RGBA', (width, height), pixel_data, 'raw', 'RGBA')
        image.save(png_file)
    else:
        print('unknown format')

    tex.close()

if __name__ == '__main__':
    convert_tex(sys.argv[1], 'test.png')

