import array
import struct

import bpy
import bmesh
import mathutils
from bpy.props import StringProperty


def convert_rgb565(i):
    r = round((i & 31) * (255 / 31))
    g = round((i >> 5 & 63) * (255 / 63))
    b = round((i >> 11 & 31) * (255 / 31))
    return mathutils.Color((r, g, b))


def convert_rgba5(i):
    r = round((i & 31) * (255 / 31))
    g = round((i >> 5 & 31) * (255 / 31))
    b = round((i >> 10 & 31) * (255 / 31))
    return mathutils.Color((r, g, b))


def convert_rgba4(i):
    r = (i & 15) * 17
    g = (i >> 4 & 15) * 17
    b = (i >> 8 & 15) * 17
    return mathutils.Color((r, g, b))


def convert_rgba8(i):
    r = i & 255
    g = i >> 8 & 255
    b = i >> 16 & 255
    return mathutils.Color((r, g, b))


def run_ge(pmo):
    bm = bmesh.new()
    file_address = pmo.tell()
    index_offset = 0
    vertex_address = None
    index_address = None
    vertex_format = None
    position_trans = None
    normal_trans = None
    color_trans = None
    texture_trans = None
    weight_trans = None
    index_format = None
    face_order = None
    while True:
        command = array.array('I', pmo.read(4))[0]
        command_type = command >> 24
        # NOP - No Operation
        if command_type == 0x00:
            pass
        # VADDR - Vertex Address (BASE)
        elif command_type == 0x01:
            if vertex_address is not None:
                index_offset = len(bm.verts)
            vertex_address = file_address + (command & 0xffffff)
        # IADDR - Index Address (BASE)
        elif command_type == 0x02:
            index_address = file_address + (command & 0xffffff)
        # PRIM - Primitive Kick
        elif command_type == 0x04:
            primative_type = (command >> 16) & 7
            index_count = command & 0xffff
            command_address = pmo.tell()
            index = range(len(bm.verts) - index_offset, len(bm.verts) + index_count - index_offset)
            if index_format is not None:
                index = array.array(index_format)
                pmo.seek(index_address)
                index.fromfile(pmo, index_count)
                index_address = pmo.tell()
            vertex_size = struct.calcsize(vertex_format)
            for i in index:
                pmo.seek(vertex_address + vertex_size * i)
                vertex = list(struct.unpack(vertex_format, pmo.read(vertex_size)))
                position = mathutils.Vector()
                position.z = vertex.pop() / position_trans
                position.y = vertex.pop() / position_trans
                position.x = vertex.pop() / position_trans
                if len(bm.verts) > (i + index_offset):
                    bm.verts[i + index_offset].co = position
                else:
                    for v in range(i + index_offset - len(bm.verts)):
                        bm.verts.new()
                    bm.verts.new(position)
                if normal_trans is not None:
                    normal = mathutils.Vector()
                    normal.z = vertex.pop() / normal_trans
                    normal.y = vertex.pop() / normal_trans
                    normal.x = vertex.pop() / normal_trans
                    bm.verts[i + index_offset].normal = normal
                if color_trans is not None:
                    color = color_trans(vertex.pop()) # TODO: add vertex colors
                if texture_trans is not None:
                    texture = mathutils.Vector() # TODO: add texture coordinates
                    texture.y = vertex.pop() / texture_trans
                    texture.x = vertex.pop() / texture_trans
                if weight_trans is not None:
                    weights = vertex[:] # TODO: add bone weights
            pmo.seek(command_address)
            r = range(index_count - 2)
            if primative_type == 3:
                r = range(0, index_count, 3)
            elif primative_type != 4:
                ValueError('Unsupported primative type: 0x%02X' % primative_type)
            for i in r:
                v1 = bm.verts[index[i] + index_offset]
                v2 = bm.verts[index[i+1] + index_offset]
                v3 = bm.verts[index[i+2] + index_offset]
                bm.faces.new((v1, v2, v3))
        # RET - Return from Call
        elif command_type == 0x0b:
            break
        # BASE - Base Address Register
        elif command_type == 0x10:
            pass
        # VTYPE - Vertex Type
        elif command_type == 0x12:
            vertex_format = ''
            weight = (command >> 9) & 3
            if weight != 0:
                count = ((command >> 14) & 7) + 1
                vertex_format += str(count) + (None, 'B', 'H', 'f')[weight]
                weight_trans = (None, 0x80, 0x8000, 1)[weight]
            bypass_transform = (command >> 23) & 1
            texture = command & 3
            if texture != 0:
                vertex_format += (None, '2B', '2H', '2f')[texture]
                texture_trans = 1
                if not bypass_transform:
                    texture_trans = (None, 0x80, 0x8000, 1)[texture]
            color = (command >> 2) & 7
            if color != 0:
                vertex_format += (None, None, None, None, 'H', 'H', 'H', 'I')[color]
                color_trans = (None, None, None, None, convert_rgb565, convert_rgba5, convert_rgba4, convert_rgba8)[color]
            normal = (command >> 5) & 3
            if normal != 0:
                vertex_format += (None, '3b', '3h', '3f')[normal]
                normal_trans = 1
                if not bypass_transform:
                    normal_trans = (None, 0x7f, 0x7fff, 1)[normal]
            position = (command >> 7) & 3
            if position != 0:
                if bypass_transform:
                    vertex_format += (None, '2bB', '2hH', '3f')[position] # TODO: handle Z clamping
                    position_trans = 1
                else:
                    vertex_format += (None, '3b', '3h', '3f')[position]
                    position_trans = (None, 0x7f, 0x7fff, 1)[position]
            index_format = (None, 'B', 'H', 'I')[(command >> 11) & 3]
            if (command >> 18) & 7 > 0:
                raise ValueError('Can not handle morphing')
        # ??? - Offset Address (BASE)
        elif command_type == 0x13:
            pass
        # ??? - Origin Address (BASE)
        elif command_type == 0x14:
            pass
        # FFACE - Front Face Culling Order
        elif command_type == 0x9b:
            face_order = command & 1 # TODO: handle face culling
        else:
            raise ValueError('Unknown GE command: 0x%02X' % command_type)
    return bm


def load_pmo_mh3(pmo):
    pmo_header = struct.unpack('I4f2H8I', pmo.read(0x38))
    for i in range(pmo_header[5]):
        pmo.seek(pmo_header[7] + i * 0x30)
        group_header = struct.unpack('8f2I4H', pmo.read(0x30))
        for j in range(group_header[12]):
            pmo.seek(pmo_header[8] + ((group_header[13] + j) * 0x10))
            vertex_group_header = struct.unpack('2BH3I', pmo.read(0x10))
            pmo.seek(pmo_header[12] + vertex_group_header[3])
            bm = run_ge(pmo)
            me = bpy.data.meshes.new('Mesh%04d%04d' % (i, j))
            bm.to_mesh(me)
            ob = bpy.data.objects.new('Object%04d%04d' % (i, j), me)
            bpy.context.scene.objects.link(ob)


def load_pmo_mh2(pmo):
        pmo_header = struct.unpack('I4f2H8I', pmo.read(0x38))
        for i in range(pmo_header[5]):
            pmo.seek(pmo_header[7] + i * 0x20)
            group_header = struct.unpack('2f2I4H2I', pmo.read(0x20))
            for j in range(group_header[6]):
                pmo.seek(pmo_header[8] + ((group_header[7] + j) * 0x10))
                vertex_group_header = struct.unpack('2BH3I', pmo.read(0x10))
                pmo.seek(pmo_header[12] + vertex_group_header[3])
                bm = run_ge(pmo)
                me = bpy.data.meshes.new('Mesh%04d%04d' % (i, j))
                bm.to_mesh(me)
                ob = bpy.data.objects.new('Object%04d%04d' % (i, j), me)
                bpy.context.scene.objects.link(ob)


def load_pmo(pmo_file):
    with open(pmo_file, 'rb') as pmo:
        type, version = struct.unpack('4s4s', pmo.read(8))
        if type == b'pmo\x00' and version == b'102\x00':
            load_pmo_mh3(pmo)
        elif type == b'pmo\x00' and version == b'1.0\x00':
            load_pmo_mh2(pmo)
        else:
            raise ValueError('Invalid PMO file')


bl_info = {
        'name': 'Import Monster Hunter Objects',
        'author': 'Seth VanHeulen',
        'version': (0, 1),
        'blender': (2, 69, 0),
        'location': 'File > Import > Monster Hunter Object (.pmo)',
        'description': 'Imports a PMO object from Monster Hunter',
        'category': 'Import-Export'
}


class IMPORT_OT_pmo(bpy.types.Operator):
    bl_idname = 'import_scene.pmo'
    bl_label = 'Import PMO'
    bl_description = 'Import a Monster Hunter PMO file'
    bl_options = {'REGISTER', 'UNDO'}
    filepath = StringProperty(name='File Path', description='File path used for importing the PMO file', maxlen=1024, default='')

    def execute(self, context):
        load_pmo(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_func(self, context):
    self.layout.operator(IMPORT_OT_pmo.bl_idname, text='Monster Hunter Object (.pmo)')


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func)


if __name__ == '__main__':
    register()

