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
            new[x + y * width] = array.array('I', bytes(c))[0]
        block_index += 1
    return new.tobytes()

def decode_565(data):
    data = array.array('H', data)
    new = bytearray()
    for i in data:
        new.append(round((i & 31) * (255 / 31)))
        new.append(round((i >> 5 & 63) * (255 / 63)))
        new.append(round((i >> 11 & 31) * (255 / 31)))
    return bytes(new)

def decode_1555(data):
    data = array.array('H', data)
    new = bytearray()
    for i in data:
        new.append((i & 1) * 255)
        new.append(round((i >> 1 & 31) * (255 / 31)))
        new.append(round((i >> 6 & 31) * (255 / 31)))
        new.append(round((i >> 11 & 31) * (255 / 31)))
    return bytes(new)

def decode_4444(data):
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

def convert_tex(tex_file, png_file):
    tex = open(tex_file, 'rb')

    magic = tex.read(4)
    if magic != b'TEX\x00':
        raise ValueError('not a TEX file')
    header = array.array('I', tex.read(12))

    constant = header[0] & 0xfff
    if constant != 0xa5:
        raise ValueError('unknown constant')
    unknown1 = (header[0] >> 12) & 0xfff
    size_shift = (header[0] >> 24) & 0xf # always == 0
    unknown2 = (header[0] >> 28) & 0xf # 2 = normal, 6 = cube map

    mipmap_count = header[1] & 0x3f
    width = (header[1] >> 6) & 0x1fff
    height = (header[1] >> 19) & 0x1fff

    texture_count = header[2] & 0xff
    color_type = (header[2] >> 8) & 0xff
    unknown3 = (header[2] >> 16) & 0x1fff # always == 1

    if unknown2 == 6:
        cube_map_junk = tex.read(0x6c) # data related to cube maps in some way
        height *= 6
    offsets = array.array('I', tex.read(4*mipmap_count*texture_count))
    pixel_data_start = tex.tell()
    pixel_data = None
    if mipmap_count > 1:
        pixel_data = tex.read(offsets[1] - offsets[0])
        if unknown2 == 6:
            for i in range(6):
                tex.seek(pixel_data_start + offsets[i*mipmap_count])
                pixel_data += tex.read(offsets[i*mipmap_count+1] - offsets[i*mipmap_count])
    else:
        pixel_data = tex.read()

    tex.close()

    if color_type == 1:
        image = Image.frombytes('RGBA', (width, height), deblock(width, 4, decode_4444(pixel_data)), 'raw', 'ABGR')
        image.save(png_file)
    elif color_type == 2:
        image = Image.frombytes('RGBA', (width, height), deblock(width, 4, decode_1555(pixel_data)), 'raw', 'ABGR')
        image.save(png_file)
    elif color_type == 3:
        image = Image.frombytes('RGBA', (width, height), deblock(width, 4, pixel_data), 'raw', 'ABGR')
        image.save(png_file)
    elif color_type == 4:
        image = Image.frombytes('RGB', (width, height), deblock(width, 3, decode_565(pixel_data)), 'raw', 'BGR')
        image.save(png_file)
    elif color_type == 5: # format may not be correct
        image = Image.frombytes('L', (width, height), deblock(width, 1, pixel_data), 'raw', 'L')
        image.save(png_file)
    elif color_type == 7:
        pixel_data = array.array('H', pixel_data)
        pixel_data.byteswap()
        image = Image.frombytes('LA', (width, height), deblock(width, 2, pixel_data.tobytes()), 'raw', 'LA')
        image.save(png_file)
    elif color_type == 11:
        image = Image.frombytes('RGBA', (width, height), decode_etc1(pixel_data, width), 'raw', 'RGBA')
        image.save(png_file)
    elif color_type == 12:
        image = Image.frombytes('RGBA', (width, height), decode_etc1(pixel_data, width, True), 'raw', 'RGBA')
        image.save(png_file)
    elif color_type == 14: # format may not be correct
        image = Image.frombytes('L', (width, height), deblock(width, 1, decode_4444(pixel_data)), 'raw', 'L')
        image.save(png_file)
    elif color_type == 15: # format may not be correct
        image = Image.frombytes('L', (width, height), deblock(width, 1, decode_4444(pixel_data)), 'raw', 'L')
        image.save(png_file)
    elif color_type == 16: # format may not be correct
        image = Image.frombytes('L', (width, height), deblock(width, 1, pixel_data), 'raw', 'L')
        image.save(png_file)
    elif color_type == 17:
        image = Image.frombytes('RGB', (width, height), deblock(width, 3, pixel_data), 'raw', 'BGR')
        image.save(png_file)
    else:
        raise ValueError('unknown texture color type')

parser = argparse.ArgumentParser(description='Convert a TEX file from Monster Hunter 4 Ultimate to an image')
parser.add_argument('inputfile', help='TEX input file')
parser.add_argument('outputfile', help='image output file')
args = parser.parse_args()

convert_tex(args.inputfile, args.outputfile)

