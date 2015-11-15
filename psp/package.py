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


def extract_package(package_file):
    with open(package_file, 'rb') as package:
        file_count = array.array('I', package.read(4))[0]
        file_info = array.array('I', package.read(file_count * 8))
        for i in range(file_count):
            package.seek(file_info[i*2])
            open('%s-%04d' % (package_file, i), 'wb').write(package.read(file_info[i*2+1]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts all files from a package file from Monster Hunter')
    parser.add_argument('inputfile', help='package input file')
    args = parser.parse_args()
    extract_package(args.inputfile)

