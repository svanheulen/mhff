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


def parse_vertex(raw_vertex):
    return array.array('f', raw_vertex[:12])


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
        for j in range(mesh_info[1]):
            vertices.append(parse_vertex(mod.read(mesh_info[4])))
        mod.seek(mod_header[17] + mesh_info[9] * 2)
        faces = parse_faces(mesh_info[6], mod.read(mesh_info[10] * 2 + 2))
        b_mesh = bpy.data.meshes.new('imported_mesh_{}'.format(i))
        b_object = bpy.data.objects.new('imported_object_{}'.format(i), b_mesh)
        b_mesh.from_pydata(vertices, [], faces)
        b_mesh.update()
        bpy.context.scene.objects.link(b_object)
    mod.close()


class IMPORT_OT_mod(bpy.types.Operator):
    bl_idname = "import_scene.mod"
    bl_label = "Import MOD"
    bl_description = "Import a Moster Hunter 4 Ultimate model"
    bl_options = {'REGISTER', 'UNDO'}

    filepath = bpy.props.StringProperty(name="File Path", description="Filepath used for importing the MOD file", maxlen=1024, default="")

    def execute(self, context):
        load_mod(self.filepath, context)
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
