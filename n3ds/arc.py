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
    # Monster Hunter 4 Ultimate file types
    ['rArchive', 'arc'],
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
    ['rLtProceduralTexture', 'ptex'],
    ['rLtShader', 'lfx'],
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
    ['rMovieOnDisk', 'moflex'],
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
    ['rTexture', 'tex'],
    # Monster Hunter X file types
    ['rAIWayPoint', 'way'],
    ['rActivityData', 'atd'],
    ['rAmuletData', 'amlt'],
    ['rAmuletSkillData', 'amskl'],
    ['rAmuletSlotData', 'amslt'],
    ['rAngryParam', 'angryprm'],
    ['rAreaActTblData', 'areaacttbl'],
    ['rAreaCommonLink', 'areacmnlink'],
    ['rAreaEatData', 'areaeatdat'],
    ['rAreaInfo', 'areainfo'],
    ['rAreaLinkData', 'arealinkdat'],
    ['rAreaPatrolData', 'areapatrol'],
    ['rAreaSelectData', 'areaseldat'],
    ['rArmorBuildData', 'abd'],
    ['rArmorColorData', 'acd'],
    ['rArmorResistData', 'ard'],
    ['rArmorSeData', 'ased'],
    ['rArmorSeriesData', 'asd'],
    ['rBodyData', 'bdd'],
    ['rBowgunShellData', 'bgsd'],
    ['rCommonScript', 'cms'],
    ['rDecoData', 'deco'],
    ['rEmDouMouKaData', 'mdd'],
    ['rEmSetList', 'esl'],
    ['rEmSizeCalcTblElement', 'emsizetbl'],
    ['rEmSizeYureTbl', 'emyure'],
    ['rEnemyDtBase', 'dtb'],
    ['rEnemyDtBaseParts', 'dtp'],
    ['rEnemyDtTune', 'dtt'],
    ['rEnemyNandoData', 'nan'],
    ['rEnemyResidentDtBase', 'rdb'],
    ['rEquipBaseColorData', 'ebcd'],
    ['rFestaPelTiedSe', 'pts'],
    ['rFestaResourceList', 'frl'],
    ['rFestaSoundEmitter', 'ses'],
    ['rFestaSoundSequence', 'mss'],
    ['rFishData', 'fsh'],
    ['rFreeUseParam', 'fup'],
    ['rFueMusicData', 'fmt'],
    ['rFueMusicInfData', 'fmi'],
    ['rFueMusicScData', 'fms'],
    ['rGUI', 'gui'],
    ['rGUIFont', 'gfd'],
    ['rGUIIconInfo', 'gii'],
    ['rGUIMessage', 'gmd'],
    ['rHagi', 'hgi'],
    ['rHitDataEnemy', 'hde'],
    ['rHitDataPlayer', 'hdp'],
    ['rHitDataShell', 'hds'],
    ['rHitSize', 'hts'],
    ['rHunterArtsData', 'hta'],
    ['rInsectAbirity', 'insectabirity'],
    ['rInsectAttr', 'isa'],
    ['rInsectData', 'isd'],
    ['rInsectEssenceSkill', 'insectessenceskill'],
    ['rInsectLevel', 'isl'],
    ['rInsectParam', 'isp'],
    ['rItemData', 'itm'],
    ['rItemPreData', 'itp'],
    ['rItemPreTypeData', 'ipt'],
    ['rKireajiData', 'kad'],
    ['rKowareObjData', 'kod'],
    ['rLayoutAnime', 'lan'],
    ['rMapTimeData', 'maptime'],
    ['rMonsterPartsManager', 'mpm'],
    ['rOtArmorData', 'oar'],
    ['rOtLevel', 'olvl'],
    ['rOtMessageLot', 'otml'],
    ['rOtQuestExpBias', 'oxpb'],
    ['rOtQuestExpValue', 'oxpv'],
    ['rOtSkill', 'oskl'],
    ['rOtSpecialAction', 'osa'],
    ['rOtSupportActionBase', 'sab'],
    ['rOtSupportActionOtUnique', 'saou'],
    ['rOtTensionData', 'otd'],
    ['rOtTrainParam', 'otp'],
    ['rOtWeaponData', 'owp'],
    ['rPlBaseCmd', 'plbasecmd'],
    ['rPlCmdTblList', 'plcmdtbllist'],
    ['rPlayerGimmickType', 'plgmktype'],
    ['rPlayerManyAttacks', 'pma'],
    ['rPlayerPartsDisp', 'plpartsdisp'],
    ['rPlayerWeaponList', 'plweplist'],
    ['rPointPos', 'pntpos'],
    ['rProofEffectColorControl', 'pec'],
    ['rProofEffectList', 'pel'],
    ['rProofEffectMotSequenceList', 'psl'],
    ['rProofEffectParamScript', 'pep'],
    ['rQuestGroup', 'qsg'],
    ['rRapidshotData', 'raps'],
    ['rRelationData', 'rlt'],
    ['rRem', 'rem'],
    ['rSeFsAse', 'sfsa'],
    ['rSetEmMain', 'sem'],
    ['rSetItemData', 'sid'],
    ['rShell', 'shell'],
    ['rShellEffectParam', 'sep'],
    ['rSkillData', 'skd'],
    ['rSkillTypeData', 'skt'],
    ['rSoundBank', 'sbkr'],
    ['rSoundEQ', 'equr'],
    ['rSoundRequest', 'srqr'],
    ['rSoundReverb', 'revr_ctr'],
    ['rSoundSourceADPCM', 'mca'],
    ['rSoundStreamRequest', 'stqr'],
    ['rSquatshotData', 'squs'],
    ['rSupplyList', 'sup'],
    ['rSupportGaugeValue', 'spval'],
    ['rTameshotData', 'tams'],
    ['rWeapon00BaseData', 'w00d'],
    ['rWeapon00LevelData', 'w00d'],
    ['rWeapon00MsgData', 'w00m'],
    ['rWeapon01BaseData', 'w01d'],
    ['rWeapon01LevelData', 'w01d'],
    ['rWeapon01MsgData', 'w01m'],
    ['rWeapon02BaseData', 'w02d'],
    ['rWeapon02LevelData', 'w02d'],
    ['rWeapon02MsgData', 'w02m'],
    ['rWeapon03BaseData', 'w03d'],
    ['rWeapon03LevelData', 'w03d'],
    ['rWeapon03MsgData', 'w03m'],
    ['rWeapon04BaseData', 'w04d'],
    ['rWeapon04LevelData', 'w04d'],
    ['rWeapon04MsgData', 'w04m'],
    ['rWeapon06BaseData', 'w06d'],
    ['rWeapon06LevelData', 'w06d'],
    ['rWeapon06MsgData', 'w06m'],
    ['rWeapon07BaseData', 'w07d'],
    ['rWeapon07LevelData', 'w07d'],
    ['rWeapon07MsgData', 'w07m'],
    ['rWeapon08BaseData', 'w08d'],
    ['rWeapon08LevelData', 'w08d'],
    ['rWeapon08MsgData', 'w08m'],
    ['rWeapon09BaseData', 'w09d'],
    ['rWeapon09LevelData', 'w09d'],
    ['rWeapon09MsgData', 'w09m'],
    ['rWeapon10BaseData', 'w10d'],
    ['rWeapon10LevelData', 'w10d'],
    ['rWeapon10MsgData', 'w10m'],
    ['rWeapon11BaseData', 'w11d'],
    ['rWeapon11LevelData', 'w11d'],
    ['rWeapon11MsgData', 'w11m'],
    ['rWeapon12BaseData', 'w12d'],
    ['rWeapon12LevelData', 'w12d'],
    ['rWeapon12MsgData', 'w12m'],
    ['rWeapon13BaseData', 'w13d'],
    ['rWeapon13LevelData', 'w13d'],
    ['rWeapon13MsgData', 'w13m'],
    ['rWeapon14BaseData', 'w14d'],
    ['rWeapon14LevelData', 'w14d'],
    ['rWeapon14MsgData', 'w14m']
]

def gen_file_type_codes():
    return [(zlib.crc32(file_type[0].encode()) ^ 0xffffffff) & 0x7fffffff for file_type in file_types]

def extract_arc(arc_file, output_path):
    if not os.path.isdir(output_path):
        raise ValueError('output path: must be existing directory')
    arc = open(arc_file, 'rb')
    magic, version, file_count, unknown = struct.unpack('4sHHI', arc.read(12))
    if magic != b'ARC\x00':
        raise ValueError('header: invalid magic')
    if version not in [0x13, 0x11]: # 0x13 = MH4U, 0x11 = MHX
        raise ValueError('header: invalid version')
    file_type_codes = gen_file_type_codes()
    toc = arc.read(file_count * 0x50)
    for i in range(file_count):
        file_name, file_type_code, compressed_size, size, offset = struct.unpack('64sIIII', toc[i*0x50:(i+1)*0x50])
        file_type = 'UNKNOWN'
        file_extension = '{:08X}'.format(file_type_code)
        if file_type_code in file_type_codes:
            file_type, file_extension = file_types[file_type_codes.index(file_type_code)]
        file_name = os.path.join(*file_name.decode().strip('\x00').split('\\')) + '.' + file_extension
        if version == 0x13:
            size &= 0x0fffffff
        else:
            size &= 0x1fffffff
        print('extracting: {}, type: {}, compressed size: {}, size: {}'.format(file_name, file_type, compressed_size, size))
        arc.seek(offset)
        file_data = arc.read(compressed_size)
        if len(file_data) != compressed_size:
            raise ValueError('table of contents: wrong compressed file size')
        file_data = zlib.decompress(file_data)
        if len(file_data) != size:
            raise ValueError('table of contents: wrong file size')
        file_name = os.path.join(output_path, file_name)
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        open(file_name, 'wb').write(file_data)
    arc.close()

parser = argparse.ArgumentParser(description='Extracts files from an ARC file from MH4U and MHX')
parser.add_argument('inputfile', help='ARC input file')
parser.add_argument('outputpath', nargs='?', default='./', help='output path')
args = parser.parse_args()

extract_arc(args.inputfile, args.outputpath)

