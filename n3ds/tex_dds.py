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

import argparse
import array
import os


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
        alpha_part1 = 0xffffffff
        alpha_part2 = 0xffffffff
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
            if i < 8:
                c.append(((alpha_part1 >> (i * 4)) & 15) * 17)
            else:
                c.append(((alpha_part2 >> ((i - 8) * 4)) & 15) * 17)
            offset = block_index % 4
            x = (block_index - offset) % (width // 2) * 2
            y = (block_index - offset) // (width // 2) * 8
            if offset & 1:
                x += 4
            if offset & 2:
                y += 4
            x += i // 4
            y += i % 4
            new[x + y * width] = array.array('I', bytes(c[::-1]))[0]
        block_index += 1
    return new.tobytes()

def decode_half_byte(data):
    new = bytearray()
    for i in data:
        new.append((i & 15) * 17)
        new.append((i >> 4) * 17)
    return bytes(new)

def unpart1by1(n):
    n &= 0x55555555
    n = (n ^ (n >> 1)) & 0x33333333
    n = (n ^ (n >> 2)) & 0x0f0f0f0f
    n = (n ^ (n >> 4)) & 0x00ff00ff
    return (n ^ (n >> 8)) & 0x0000ffff

def deinterleave2(n):
    return unpart1by1(n), unpart1by1(n >> 1)

def deblock(width, size, data):
    new = bytearray(data)
    for i in range(len(data)//size):
        offset = i % 128
        block = i // 128
        x, y = deinterleave2(offset)
        if width >= 16:
            x += 16 * (block % (width // 16))
            y += 8 * (block // (width // 16))
        for j in range(size):
            new[(x+y*width)*size+j] = data[i*size+j]
    return bytes(new)

def convert_tex(tex_file, dds_file):
    tex = open(tex_file, 'rb')
    tex_header = array.array('I', tex.read(16))
    if tex_header[0] != 0x584554:
        raise ValueError('unknown magic')
    constant = tex_header[1] & 0xfff
    if constant not in [0xa5, 0xa6]:
        raise ValueError('unknown constant')
    unknown1 = (tex_header[1] >> 12) & 0xfff
    size_shift = (tex_header[1] >> 24) & 0xf # always == 0
    cube_map = (tex_header[1] >> 28) & 0xf # 2 = normal, 6 = cube map
    mipmap_count = tex_header[2] & 0x3f
    width = (tex_header[2] >> 6) & 0x1fff
    height = (tex_header[2] >> 19) & 0x1fff
    texture_count = tex_header[3] & 0xff
    color_type = (tex_header[3] >> 8) & 0xff
    if color_type not in (1, 2, 3, 4, 5, 7, 11, 12, 14, 15, 16, 17):
        raise ValueError('unknown color type')
    unknown3 = (tex_header[3] >> 16) & 0x1fff # always == 1
    dds_header = array.array('I', [0x20534444, 124, 0x100f, height, width, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0, 0, 0, 0x1000, 0, 0, 0, 0])
    if cube_map == 6:
        dds_header[27] |= 0x8
        dds_header[28] = 0xfe00
        tex.seek(0x6c, os.SEEK_CUR) # data related to cube maps in some way
    offsets = array.array('I', tex.read(mipmap_count * texture_count * 4))
    pixel_data_start = tex.tell()
    pixel_data = []
    if mipmap_count > 1:
        dds_header[2] |= 0x20000
        dds_header[7] = mipmap_count
        dds_header[27] |= 0x400008
    if color_type == 1:
        dds_header[20] = 0x41
        dds_header[22] = 16
        dds_header[23] = 0xf000
        dds_header[24] = 0xf00
        dds_header[25] = 0xf0
        dds_header[26] = 0xf
    elif color_type == 2:
        dds_header[20] = 0x41
        dds_header[22] = 16
        dds_header[23] = 0xf800
        dds_header[24] = 0x7c0
        dds_header[25] = 0x3e
        dds_header[26] = 0x1
    elif color_type in (3, 11, 12):
        dds_header[20] = 0x41
        dds_header[22] = 32
        dds_header[23] = 0xff000000
        dds_header[24] = 0xff0000
        dds_header[25] = 0xff00
        dds_header[26] = 0xff
    elif color_type == 4:
        dds_header[20] = 0x40
        dds_header[22] = 16
        dds_header[23] = 0xf800
        dds_header[24] = 0x7e0
        dds_header[25] = 0x1f
    elif color_type in (5, 14, 15, 16): # format may not be correct
        dds_header[20] = 0x20000
        dds_header[22] = 8
        dds_header[23] = 0xff
    elif color_type == 7:
        dds_header[20] = 0x20001
        dds_header[22] = 16
        dds_header[23] = 0xff00
        dds_header[26] = 0xff
    elif color_type in (17):
        dds_header[20] = 0x40
        dds_header[22] = 24
        dds_header[23] = 0xff0000
        dds_header[24] = 0xff00
        dds_header[25] = 0xff
    dds_header[5] = (width * dds_header[22] + 7) // 8
    main_data_size = width * height
    if color_type in (11, 14, 15):
        main_data_size //= 2
    if color_type in (1, 2, 4, 7):
        main_data_size *= 2
    if color_type == 17:
        main_data_size *= 3
    if color_type == 3:
        main_data_size *= 4
    for i in range(mipmap_count):
        for j in range(texture_count):
            tex.seek(pixel_data_start + offsets[i * texture_count + j])
            data = tex.read(main_data_size // (1 << (i * 2)))
            if color_type in (14, 15):
                data = decode_half_byte(data)
            if color_type in (11, 12):
                data = decode_etc1(data, width // (1 << i), color_type == 12)
            else:
                data = deblock(width // (1 << i), dds_header[22] // 8, data)
            pixel_data.append(data)
    tex.close()
    dds = open(dds_file, 'wb')
    dds.write(dds_header.tobytes())
    for data in pixel_data:
        dds.write(data)
    dds.close()

parser = argparse.ArgumentParser(description='Convert a TEX file from Monster Hunter 4 Ultimate to an image')
parser.add_argument('inputfile', help='TEX input file')
parser.add_argument('outputfile', help='image output file')
args = parser.parse_args()

convert_tex(args.inputfile, args.outputfile)

