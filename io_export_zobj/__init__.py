# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

bl_info = {
    "name": "ZOBJ format",
    "author": "astronotter, CrookedPoe, z64me, Campbell Barton, Bastien Montagne",
    "version": (2, 2, 1),
    "blender": (2, 79, 0),
    "location": "File > Import-Export",
    "description": "Export ZOBJ for OOT and MM modding.",
    "warning": "",
    "support": 'OFFICIAL',
    "category": "Import-Export"}

if "bpy" in locals():
    import importlib
    if "export_objex" in locals():
        importlib.reload(export_objex)
'''    if "import_objex" in locals():
        importlib.reload(import_objex)'''


import bpy
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper_factory,
        path_reference_mode,
        axis_conversion,
        )
import os
import ntpath
import subprocess
import random
import string


IOOBJOrientationHelper = orientation_helper_factory("IOOBJOrientationHelper", axis_forward='-Z', axis_up='Y')


class ExportZOBJ(bpy.types.Operator, ExportHelper, IOOBJOrientationHelper):
    """Save a ZOBJ File"""

    bl_idname = "export_scene.zobj"
    bl_label = 'Export ZOBJ'
    bl_options = {'PRESET'}

    filename_ext = ".zobj"
    filter_glob = StringProperty(
            default="*.zobj",
            options={'HIDDEN'},
            )

    keep_objex          = BoolProperty(default=False, name="Keep OBJEX")
    use_playas          = BoolProperty(default=True, name="Embed PlayAs data")
    output_header       = BoolProperty(default=False, name="Output header (.h)")
    model_type          = EnumProperty(default="OTHER", name="Model type",
        items=[("CHILD", "Child", "Link Child Model"),
               ("ADULT", "Adult", "Link Boy Model"),
               ("OTHER", "Other", "Custom Model") ])
    
    # context group
    use_selection = BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=False,
            )
    use_animation = BoolProperty(
            name="Animation",
            description="Write out an OBJ for each frame",
            default=False,
            )

    # object group
    use_mesh_modifiers = BoolProperty(
            name="Apply Modifiers",
            description="Apply modifiers (preview resolution)",
            default=False,
            )

    # extra data group
    use_edges = BoolProperty(
            name="Include Edges",
            description="",
            default=False,
            )
    use_smooth_groups = BoolProperty(
            name="Smooth Groups",
            description="Write sharp edges as smooth groups",
            default=False,
            )
    use_smooth_groups_bitflags = BoolProperty(
            name="Bitflag Smooth Groups",
            description="Same as 'Smooth Groups', but generate smooth groups IDs as bitflags "
                        "(produces at most 32 different smooth groups, usually much less)",
            default=False,
            )
    use_normals = BoolProperty(
            name="Write Normals",
            description="Export one normal per vertex and per face, to represent flat faces and sharp edges",
            default=True,
            )
    use_uvs = BoolProperty(
            name="Include UVs",
            description="Write out the active UV coordinates",
            default=True,
            )
    use_materials = BoolProperty(
            name="Write Materials",
            description="Write out the MTL file",
            default=True,
            )
    use_triangles = BoolProperty(
            name="Triangulate Faces",
            description="Convert all faces to triangles",
            default=True,
            )
    use_nurbs = BoolProperty(
            name="Write Nurbs",
            description="Write nurbs curves as OBJ nurbs rather than "
                        "converting to geometry",
            default=False,
            )
    use_vertex_groups = BoolProperty(
            name="Polygroups",
            description="",
            default=False,
            )

    # grouping group
    use_blen_objects = BoolProperty(
            name="Objects as OBJ Objects",
            description="",
            default=False,
            )
    group_by_object = BoolProperty(
            name="Objects as OBJ Groups ",
            description="",
            default=True,
            )
    group_by_material = BoolProperty(
            name="Material Groups",
            description="",
            default=False,
            )
    keep_vertex_order = BoolProperty(
            name="Keep Vertex Order",
            description="",
            default=False,
            )

    global_scale = FloatProperty(
            name="Scale",
            min=0.01, max=1000.0,
            default=1.0,
            )

    path_mode = path_reference_mode

    check_extension = True



    def execute(self, context):
        from . import export_objex
        from mathutils import Matrix
        
        TEMP = os.getenv('TEMP')
        CWD = ntpath.dirname(ntpath.abspath(__file__))

        basefilepath = ntpath.splitext(self.filepath)[0]
        objexfilepath = basefilepath + ".objex"
        if not self.keep_objex:
            objexfilepath = ntpath.join(TEMP, ntpath.basename(objexfilepath))


        # Create an intermediate OBJEX file first. If the option to preserve
        # this file (kee_objex) is true we use the same directory, otherwise we
        # use the temp directory.
        global_matrix = (Matrix.Scale(self.global_scale, 4) *
                         axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4())
        keywords = self.as_keywords(ignore=(
            "axis_forward",
            "axis_up",
            "global_scale",
            "check_existing",
            "filter_glob",
            "keep_objex",
            "model_type",
            "output_header",
            "use_playas",
            "rom_path"))
        keywords["global_matrix"] = global_matrix
        keywords["filepath"] = objexfilepath
        export_objex.save(self, context, **keywords)  # FIXME check the return!

        # Convert the OBJEX file to a ZOBJ with playas info
        zzconvert = []
        zzconvert.append(os.path.join(CWD, "zzconvert.exe"))
        zzconvert.append("object")
        zzconvert.append(objexfilepath)
        zzconvert.append(self.filepath)
        if not self.output_header:
            zzconvert.append("-nh")
        if self.model_type != "NONE":
            zzconvert.append("-l")
        if self.use_playas:
            zzconvert.append('-p')
        subprocess.run(zzconvert)

        if self.use_playas and self.model_type != "NONE":
            zzplayas = []
            zzplayas.append(os.path.join(CWD, "zzobjman.exe"))
            zzplayas.append("playas")
            zzplayas.append("-r")
            zzplayas.append(self.filepath) # Provide the zobj as a rom...
            zzplayas.append("-i")
            zzplayas.append(self.filepath)
            zzplayas.append("-o")
            zzplayas.append(basefilepath)  # No extension!
            if self.model_type == "CHILD":
                zzplayas.append("-m")
                zzplayas.append(os.path.join(CWD, "child-link.txt"))
                zzplayas.append("-b")
                zzplayas.append(os.path.join(CWD, "bank_object_link_child.zobj"))
            else:
                zzplayas.append("-m")
                zzplayas.append(os.path.join(CWD, "adult-link.txt"))
                zzplayas.append("-b")
                zzplayas.append(os.path.join(CWD, "bank_object_link_boy.zobj"))
            subprocess.run(zzplayas)
        
        return {'FINISHED'}


def menu_func_export(self, context):
    self.layout.operator(ExportZOBJ.bl_idname, text="ZOBJ (.zobj)")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)

class FixArm(bpy.types.Operator):
    bl_idname="zobj.fix_armature"
    bl_label="Fix Armature"

    def execute(self,context):
        arm = bpy.context.active_object
        if len(bpy.data.armatures) != 0:
            if arm.type == 'ARMATURE':
                if bpy.context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode = 'OBJECT')
                root = arm.pose.bones[0]

            else:
                self.report({'ERROR'}, "Please select an armature!")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "Please create an armature!")
            return {'CANCELLED'}

        arm.data.draw_type = 'STICK'
        arm.show_x_ray = True
        bpy.ops.object.mode_set(mode = 'EDIT')
        # Fix Bone Tail Position
        for bone in arm.data.edit_bones[:]:
            bone.use_connect = False
            bone.roll = 0
        for bone in arm.data.edit_bones[:]:
            bone.use_inherit_scale = False
        for bone in arm.data.edit_bones[:]:
            bone.tail[2] = bone.head[2] + 0.001
        for bone in arm.data.edit_bones[:]:
            bone.tail[1] = bone.head[1]
        for bone in arm.data.edit_bones[:]:
            bone.tail[0] = bone.head[0]

        for bone in arm.pose.bones[:]:
            bone.rotation_quaternion=(1,0,0,0) # Reset Rotations
            bone.location=(0,0,0) # Reset Location
            bone.scale=(1,1,1) # Reset Scale
            bone.lock_scale=(True,True,True) # Lock Pose Scale
            if bone != root:
                bone.lock_location=(True,True,True) # Lock Pose Location

        bpy.ops.object.mode_set(mode = 'POSE')

        return{'FINISHED'}

class ShowUnassignedVerts(bpy.types.Operator):
    bl_idname="zobj.show_unassigned_verts"
    bl_label="Show Unassigned Vertices"

    def execute(self,context):
        obj = bpy.context.active_object

        if obj.type == 'MESH':
            if bpy.context.mode != 'EDIT':
                bpy.ops.object.mode_set(mode = 'EDIT')
        else:
            self.report({'ERROR'}, "Please select a mesh object!")
            return {'CANCELLED'}

        bpy.ops.mesh.select_all(action='SELECT')

        for vg in obj.vertex_groups[:]:
            bpy.ops.object.vertex_group_set_active(group=(vg.name))
            bpy.context.tool_settings.mesh_select_mode = (True, False, False)
            bpy.ops.object.vertex_group_deselect()
            obj.update_from_editmode()
        vsel = len([v for v in obj.data.vertices if v.select])
        if vsel == 0:
            bpy.ops.object.mode_set(mode = 'OBJECT')
            self.report({'INFO'}, "There are no unassigned vertices!")
            return {'FINISHED'}

        return{'FINISHED'}

class ShowMultiVerts(bpy.types.Operator):
    bl_idname="zobj.show_multi_assigned_verts"
    bl_label="Show Multi-Assigned Vertices"

    def execute(self,context):
        obj = bpy.context.active_object

        if obj.type == 'MESH':
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode = 'OBJECT')
        else:
            self.report({'ERROR'}, "Please select a mesh object!")
            return {'CANCELLED'}

        # Begin "Show Multi-Assigned Vertices"
        vsel=0
        for v in obj.data.vertices[:]:
            tgroups = len(v.groups)
            if tgroups>1:
                v.select = True
                vsel=vsel+1
            else:
                v.select = False
        if vsel == 0:
            bpy.ops.object.mode_set(mode = 'OBJECT')
            self.report({'INFO'}, "There are no multi-assigned vertices!")
            return {'FINISHED'}
        else:
            bpy.ops.object.mode_set(mode = 'EDIT')
            return {'FINISHED'}
        # End "Show Multi-Assigned Vertices"

        return{'FINISHED'}

class View3dPanel():
    bl_space_type="VIEW_3D"
    bl_region_type="TOOLS"
    bl_category="ZOBJ"


class Armature(View3dPanel,bpy.types.Panel):
    bl_label="Armature"


    def draw(self,context):
        layout=self.layout
        layout.operator(operator = "zobj.fix_armature",text = "Fix Armature",icon = "OUTLINER_DATA_ARMATURE")
        layout.operator(operator = "zobj.show_unassigned_verts",text = "Show Unassigned Vertices",icon = "GROUP_VERTEX")
        layout.operator(operator = "zobj.show_multi_assigned_verts",text = "Show Multi-Assigned Vertices",icon = "GROUP_VERTEX")
        self.layout.split()

if __name__ == "__main__":
    register()
