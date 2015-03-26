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
    data = array.array('Q', data)
    pixel_count = len(data) * 8
    if not alpha:
        pixel_count *= 2
    new = array.array('I', range(pixel_count))
    a = [255]*16
    for i in range(len(data)):
        if alpha and i % 2 == 0:
            #for j in range(16):
            #    a[j] = (data[i] >> (j * 4) & 15) * 17
            pass
        else:
            diffbit = data[i] & (1 << 33)
            flipbit = data[i] & (1 << 32)
            codeword1 = data[i] >> 37 & 7
            codeword2 = data[i] >> 34 & 7
            color1 = None
            color2 = None
            if diffbit == 0:
                r1 = data[i] >> 60 & 15
                r2 = data[i] >> 56 & 15
                g1 = data[i] >> 52 & 15
                g2 = data[i] >> 48 & 15
                b1 = data[i] >> 44 & 15
                b2 = data[i] >> 40 & 15
                color1 = [(r1 << 4) + r1, (g1 << 4) + g1, (b1 << 4) + b1]
                color2 = [(r2 << 4) + r2, (g2 << 4) + g2, (b2 << 4) + b2]
            else:
                r1 = data[i] >> 59 & 31
                dr2 = data[i] >> 56 & 7
                if dr2 > 3:
                    dr2 -= 8
                r2 = r1 + dr2
                g1 = data[i] >> 51 & 31
                dg2 = data[i] >> 48 & 7
                if dg2 > 3:
                    dg2 -= 8
                g2 = g1 + dg2
                b1 = data[i] >> 43 & 31
                db2 = data[i] >> 40 & 7
                if db2 > 3:
                    db2 -= 8
                b2 = b1 + db2
                color1 = [(r1 >> 2) + (r1 << 3), (g1 >> 2) + (g1 << 3), (b1 >> 2) + (b1 << 3)]
                color2 = [(r2 >> 2) + (r2 << 3), (g2 >> 2) + (g2 << 3), (b2 >> 2) + (b2 << 3)]
            block = array.array('I')
            for j in range(16):
                modifier_index = ((data[i] >> j) & 1) + (((data[i] >> (j + 16)) & 1) << 1)
                color = None
                if flipbit == 0 and j < 8:
                    modifier = modifier_tables[codeword1][modifier_index]
                    color = [color1[0] + modifier, color1[1] + modifier, color1[2] + modifier]
                elif flipbit == 0:
                    modifier = modifier_tables[codeword2][modifier_index]
                    color = [color2[0] + modifier, color2[1] + modifier, color2[2] + modifier]
                elif flipbit != 0 and (j // 2 % 2) == 0:
                    modifier = modifier_tables[codeword1][modifier_index]
                    color = [color1[0] + modifier, color1[1] + modifier, color1[2] + modifier]
                else:
                    modifier = modifier_tables[codeword2][modifier_index]
                    color = [color2[0] + modifier, color2[1] + modifier, color2[2] + modifier]
                color[0] = min(255, max(0, color[0]))
                color[1] = min(255, max(0, color[1]))
                color[2] = min(255, max(0, color[2]))
                color.append(a[j])
                base = i
                if alpha:
                    base = (i // 2)
                offset = base % 4
                x = (base - offset) % (width // 2) * 2
                y = (base - offset) // (width // 2) * 8
                if offset == 1:
                    x += 4
                elif offset == 2:
                    y += 4
                elif offset == 3:
                    x += 4
                    y += 4
                x = x + j // 4
                y = y + j % 4
                new[x + y * width] = struct.unpack('I', bytes(color))[0]
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

