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
import math
import os


def read_toc(data_file):
    data = open(data_file, 'rb')
    toc_size = array.array('I', data.read(4))[0] * 2048
    file_size = data.seek(0, os.SEEK_END)
    data.seek(0)
    toc = array.array('I', data.read(toc_size))
    data.close()
    file_count = toc.index(file_size // 2048)
    return toc, file_count

def extract_file(data_file, index):
    toc, file_count = read_toc(data_file)
    if index >= file_count:
        raise IndexError()
    data = open(data_file, 'rb')
    data.seek(toc[index] * 2048)
    out_data = data.read((toc[index+1] - toc[index]) * 2048)
    data.close()
    return out_data

def replace_file(data_file, index, in_data):
    toc, file_count = read_toc(data_file)
    if index >= file_count:
        raise IndexError()
    old_blocks = toc[index+1] - toc[index]
    new_blocks = int(math.ceil(len(in_data) / 2048))
    data = open(data_file, 'r+b')
    moves = []
    if new_blocks > old_blocks:
        moves = range(file_count-1, index, -1)
    elif new_blocks < old_blocks:
        moves = range(index+1, file_count)
    for i in moves:
        data.seek(toc[i] * 2048)
        temp_data = data.read((toc[i+1] - toc[i]) * 2048)
        data.seek((toc[i] + new_blocks - old_blocks) * 2048)
        data.write(temp_data)
    for i in moves:
        toc[i] += new_blocks - old_blocks
    toc[file_count] += new_blocks - old_blocks
    for i in range(file_count+1, len(toc), 2):
        if toc[i] == index:
            toc[i+1] = len(in_data)
    data.seek(0)
    data.write(toc.tostring())
    data.seek(toc[index] * 2048)
    data.write(in_data)
    data.seek(toc[file_count] * 2048)
    data.truncate()
    data.close()

def extract(data_file, out_path):
    temp, file_count = read_toc(data_file)
    toc = []
    for i in range(file_count):
        toc.append([temp[i] * 2048, (temp[i+1] - temp[i]) * 2048])
    for i in range(file_count + 1, len(temp), 2):
        if temp[i] >= file_count or temp[i] <= 0:
            break
        toc[temp[i]][1] = temp[i+1]
    data = open(data_file, 'rb')
    for i in range(len(toc)):
        data.seek(toc[i][0])
        open(os.path.join(out_path, '%04d' % i), 'wb').write(data.read(toc[i][1]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts all files from the DATA.BIN file from Monster Hunter')
    subparsers = parser.add_subparsers()
    parser_a = subparsers.add_parser('a')
    parser_a.add_argument('inputfile', help='DATA.BIN input file')
    parser_a.add_argument('outputpath', nargs='?', default='', help='output path')
    parser_x = subparsers.add_parser('x')
    parser_x.add_argument('inputfile', help='DATA.BIN input file')
    parser_x.add_argument('fileindex', type=int, help='index of the file to extract')
    parser_x.add_argument('outputfile', help='output file')
    parser_r = subparsers.add_parser('r')
    parser_r.add_argument('inputfile', help='DATA.BIN input file')
    parser_r.add_argument('fileindex', type=int, help='index of the file to replace')
    parser_r.add_argument('replacementfile', help='replacement input file')
    args = vars(parser.parse_args())
    if args.get('replacementfile'):
        replace_file(args['inputfile'], args['fileindex'], open(args['replacementfile'], 'rb').read())
    elif args.get('outputfile'):
        open(args['outputfile'], 'wb').write(extract_file(args['inputfile'], args['fileindex']))
    else:
        extract(args['inputfile'], args['outputpath'])

