#!/usr/bin/python

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
import os
import struct
import zlib


file_types = [
    ['rCameraList', 'lcm'],
    ['rChainCol', 'ccl'],
    ['rCnsTinyChain', 'ctc'],
    ['rCollision', 'sbc'],
    ['rEffectAnim', 'ean'],
    ['rEffectList', 'efl'],
    ['rEnemyCmd', 'emc'],
    ['rEnemyData', 'emd'],
    ['rEnemyTuneData', 'etd'],
    ['rEventActorTbl', 'evt'],
    ['rGrass2', 'gr2'],
    ['rGrass2Setting', 'gr2s'],
    ['rGrassWind', 'grw'],
    ['rItemPopList', 'ipl'],
    ['rItemPopSet', 'ips'],
    ['rLayout', 'lyt'],
    ['rLayoutAnimeList', 'lanl'],
    ['rLayoutFont', 'lfd'],
    ['rLayoutMessage', 'lmd'],
    ['rLtProceduralTexture', 'ptex'], # not inside any arc
    ['rLtShader', 'lfx'], # not inside any arc
    ['rLtSoundBank', 'sbk'],
    ['rLtSoundCategoryFilter', 'cfl'],
    ['rLtSoundRequest', 'srq'],
    ['rLtSoundReverb', 'rev_ctr'],
    ['rLtSoundSourceADPCM', 'mca'],
    ['rLtSoundStreamRequest', 'stq'],
    ['rMHSoundEmitter', 'ses'],
    ['rMHSoundSequence', 'mss'],
    ['rMaterial', 'mrl'],
    ['rMhMotionEffect', 'mef'],
    ['rModel', 'mod'],
    ['rMotionList', 'lmt'],
    ['rMovieOnDisk', 'moflex'], # not inside any arc
    ['rQuestData', 'mib'],
    ['rScheduler', 'sdl'],
    ['rSoundAttributeSe', 'ase'],
    ['rSoundCurveSet', 'scs'],
    ['rSoundDirectionalSet', 'sds'],
    ['rStageAreaInfo', 'sai'],
    ['rStageCameraData', 'scd'],
    ['rStageInfoSet', 'sis'],
    ['rSwkbdMessageStyleTable', 'skst'],
    ['rSwkbdMessageTable', 'skmt'],
    ['rSwkbdSubGroup', 'sksg'],
    ['rTexture', 'tex']
]

def extract_arc(arc_file, output_path):
    if not os.path.isdir(output_path):
        raise ValueError('output path: must be existing directory')
    arc = open(arc_file, 'rb')
    arc_header = struct.unpack('4sHHI', arc.read(12))
    if arc_header[0] != b'ARC\x00':
        raise ValueError('header: invalid magic')
    if arc_header[1] != 0x13:
        raise ValueError('header: invalid version')
    if arc_header[2] == 0:
        raise ValueError('header: invalid file count')
    file_type_codes = [(zlib.crc32(file_type[0].encode()) ^ 0xffffffff) & 0x7fffffff for file_type in file_types]
    for i in range(arc_header[2]):
        file_entry = struct.unpack('64sIIII', arc.read(0x50))
        pos = arc.tell()
        arc.seek(file_entry[4])
        file_data = arc.read(file_entry[2])
        if len(file_data) != file_entry[2]:
            raise ValueError('file entry: wrong compressed file size')
        file_data = zlib.decompress(file_data)
        if len(file_data) != file_entry[3] & 0x0fffffff:
            raise ValueError('file entry: wrong decompressed file size')
        arc.seek(pos)
        file_type = 'UNKNOWN'
        file_extension = '{:08X}'.format(file_entry[1])
        if file_entry[1] in file_type_codes:
            file_type, file_extension = file_types[file_type_codes.index(file_entry[1])]
        file_name = os.path.join(*file_entry[0].decode().strip('\x00').split('\\')) +'.' + file_extension
        print('extracting: {}, type: {}, compressed size: {}, size: {}'.format(file_name, file_type, file_entry[2], file_entry[3] & 0x0fffffff))
        file_name = os.path.join(output_path, file_name)
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        open(file_name, 'wb').write(file_data)
    arc.close()

parser = argparse.ArgumentParser(description='Extracts an ARC file from Monster Hunter 4 Ultimate')
parser.add_argument('inputfile', help='ARC input file')
parser.add_argument('outputpath', nargs='?', default='./', help='output path')
args = parser.parse_args()

extract_arc(args.inputfile, args.outputpath)

