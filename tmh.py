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
from PIL import Image


def decode_palette(mode, data):
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
    return None


def decode_pixels(mode, data):
    if mode == 4:
        new = bytearray()
        for i in data:
            new.append(i & 15)
            new.append(i >> 4)
        return bytes(new)
    if mode == 5:
        return data
    return None


def extract_tmh(tmh_file):
    with open(tmh_file, 'rb') as tmh:
        tmh_header = struct.unpack('8s2I', tmh.read(16))
        if tmh_header[0] != b'.TMH0.14':
            raise ValueError('Not a valid TMH file.')
        for i in range(tmh_header[1]):
            image_header = struct.unpack('4I', tmh.read(16))
            pixel_header = struct.unpack('3I2H', tmh.read(16))
            image = Image.new('P', pixel_header[3:])
            for t in range((pixel_header[0] - 16) // 128):
                w = 32
                if pixel_header[2] == 5:
                    w = 16
                tile = Image.frombytes('P', (w, 8), decode_pixels(pixel_header[2], tmh.read(128)))
                x = t * w
                y = (x // pixel_header[3]) * 8
                x %= pixel_header[3]
                image.paste(tile, (x, y))
            if pixel_header[2] != 8:
                palette_header = struct.unpack('4I', tmh.read(16))
                palette_data = decode_palette(palette_header[2], tmh.read(palette_header[0] - 16))
                if pixel_header[2] == 5:
                    for p in range(palette_header[3] // 256):
                        image.putpalette(palette_data[p*1024:p*1024+1024], 'RGBX')
                        image.save('%s-i%02d-p%02d.png' % (tmh_file, i, p))
                else:
                    for p in range(palette_header[3] // 16):
                        image.putpalette(palette_data[p*64:p*64+64], 'RGBX')
                        image.save('%s-i%02d-p%02d.png' % (tmh_file, i, p))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts all images from a TMH image pack file from Monster Hunter')
    parser.add_argument('tmhfile', help='TMH file to extract')
    args = parser.parse_args()
    extract_tmh(args.tmhfile)

