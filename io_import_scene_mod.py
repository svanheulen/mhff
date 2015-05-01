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

bl_info= {
    "name": "Import MH4U Models",
    "author": "Seth VanHeulen",
    "version": (1, 0),
    "blender": (2, 74, 0),
    "location": "File > Import > Monster Hunter 4 Ultimate Model (.mod)",
    "description": "Imports a Monster Hunter 4 Ultimate model.",
    "category": "Import-Export",
}

import array
import struct

import bpy


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


def decode_etc1(image, data):
    data = array.array('I', data)
    image_pixels = [0.0, 0.0, 0.0, 1.0] * image.size[0] * image.size[1]
    block_index = 0
    while len(data) != 0:
        alpha_part1 = 0
        alpha_part2 = 0
        if image.depth == 32:
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
            bc1 = [(x << 3) + (x >> 2) for x in bc1]
            bc2 = [(x << 3) + (x >> 2) for x in bc2]
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
            offset = block_index % 4
            x = (block_index - offset) % (image.size[0] // 2) * 2
            y = (block_index - offset) // (image.size[0] // 2) * 8
            if offset & 1:
                x += 4
            if offset & 2:
                y += 4
            x += i // 4
            y += i % 4
            offset = (x + (image.size[1] - y - 1) * image.size[0]) * 4
            image_pixels[offset] = c[0] / 255
            image_pixels[offset+1] = c[1] / 255
            image_pixels[offset+2] = c[2] / 255
        block_index += 1
    image.pixels = image_pixels
    image.update()


def load_tex(filename, name):
    tex = open(filename, 'rb')
    tex_header = struct.unpack('4s3I', tex.read(16))
    constant = tex_header[1] & 0xfff
    #unknown1 = (tex_header[1] >> 12) & 0xfff
    size_shift = (tex_header[1] >> 24) & 0xf
    #unknown2 = (tex_header[1] >> 28) & 0xf
    mipmap_count = tex_header[2] & 0x3f
    width = (tex_header[2] >> 6) & 0x1fff
    height = (tex_header[2] >> 19) & 0x1fff
    #unknown3 = tex_header[3] & 0xff
    pixel_type = (tex_header[3] >> 8) & 0xff
    #unknown5 = (tex_header[3] >> 16) & 0x1fff
    offsets = array.array('I', tex.read(4 * mipmap_count))
    if pixel_type == 11:
        image = bpy.data.images.new('texture', width, height)
        decode_etc1(image, tex.read(width*height//2))
    elif pixel_type == 12:
        image = bpy.data.images.new('texture', width, height, True)
        decode_etc1(image, tex.read(width*height))
    tex.close()


def load_mrl():
    pass


def parse_vertex(raw_vertex):
    vertex = array.array('f', raw_vertex[:12])
    uv = array.array('f', raw_vertex[16:24])
    bones = list(raw_vertex[24:26] + raw_vertex[32:33] + raw_vertex[34:35])
    weights = [x / 255 for x in raw_vertex[26:28] + raw_vertex[33:34] + raw_vertex[35:36]]
    return vertex, uv


def parse_faces(vertex_start_index, raw_faces):
    raw_faces = array.array('H', raw_faces)
    reverse = True
    faces = []
    f1 = raw_faces.pop(0)
    f2 = raw_faces.pop(0)
    while len(raw_faces) > 0:
        f3 = raw_faces.pop(0)
        if f3 == 0xffff:
            f1 = raw_faces.pop(0)
            f2 = raw_faces.pop(0)
            reverse = True
        else:
            reverse = not reverse
            if reverse:
                faces.append([f1-vertex_start_index, f3-vertex_start_index, f2-vertex_start_index])
            else:
                faces.append([f1-vertex_start_index, f2-vertex_start_index, f3-vertex_start_index])
            f1 = f2
            f2 = f3
    return faces


def build_uv_map(b_mesh, uvs, faces):
    b_mesh.uv_textures.new()
    for i,loop in enumerate(b_mesh.loops):
        b_mesh.uv_layers[0].data[i].uv = uvs[loop.vertex_index]


def load_mod(filename, context):
    mod = open(filename, 'rb')
    mod_header = struct.unpack('4s4H13I', mod.read(64))
    if mod_header[0] != b'MOD\x00' or mod_header[1] != 0xe6:
        mod.close()
        return
    for i in range(mod_header[3]):
        mod.seek(mod_header[15] + i * 48)
        mesh_info = struct.unpack('HHIHBB9I', mod.read(48))
        mod.seek(mod_header[16] + mesh_info[6] * mesh_info[4] + mesh_info[7])
        vertices = []
        uvs = []
        for j in range(mesh_info[1]):
            vertex, uv = parse_vertex(mod.read(mesh_info[4]))
            vertices.append(vertex)
            if len(uv) != 0:
                uvs.append(uv)
        mod.seek(mod_header[17] + mesh_info[9] * 2)
        faces = parse_faces(mesh_info[6], mod.read(mesh_info[10] * 2 + 2))
        b_mesh = bpy.data.meshes.new('imported_mesh_{}'.format(i))
        b_object = bpy.data.objects.new('imported_object_{}'.format(i), b_mesh)
        b_mesh.from_pydata(vertices, [], faces)
        b_mesh.update(calc_edges=True)
        bpy.context.scene.objects.link(b_object)
        if len(uvs) != 0:
            build_uv_map(b_mesh, uvs, faces)
    mod.close()


class IMPORT_OT_mod(bpy.types.Operator):
    bl_idname = "import_scene.mod"
    bl_label = "Import MOD"
    bl_description = "Import a Moster Hunter 4 Ultimate model"
    bl_options = {'REGISTER', 'UNDO'}

    filepath = bpy.props.StringProperty(name="File Path", description="Filepath used for importing the MOD file", maxlen=1024, default="")

    def execute(self, context):
        load_mod(self.filepath, context)
        load_tex(self.filepath.replace('.58A15856', '_BM.241F5DEB'), 'test')
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_func(self, context):
    self.layout.operator(IMPORT_OT_mod.bl_idname, text="Monster Hunter 4 Ultimate Model (.mod)")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func)


if __name__ == "__main__":
    register()
