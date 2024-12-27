bl_info = {
    "name": "Garden Planning",
    "blender": (3, 4, 0),  # Blender version
    "category": "Garden Planning",
    "version": (1, 0, 0),
    "author": "Zuhaira Nasrin Zakaria",
    "description": "This add-on does planting and growing plants"
}

import bpy
import bpy.ops
import bpy.app
import random
import bmesh
import uuid
from mathutils import Quaternion, Vector

from bpy.props import FloatProperty

# Operator: Clear scene
def clear_collections(scene):
    while scene.collection.children:
        collection = scene.collection.children[0]
        clear_collection_objects(collection)
        scene.collection.children.unlink(collection)
        bpy.data.collections.remove(collection)

def clear_collection_objects(collection):
    while collection.children:
        nested_collection = collection.children[0]
        clear_collection_objects(nested_collection)
        collection.children.unlink(nested_collection)
        bpy.data.collections.remove(nested_collection)

    for obj in collection.objects:
        # Remove object from the current collection
        collection.objects.unlink(obj)
        # Delete the object data if no other users
        if obj.users == 0:
            bpy.data.objects.remove(obj)

class ClearGrowingObjectsOperator(bpy.types.Operator):
    """Clear scene completely"""
    bl_idname = "scene.clear_growing_objects"
    bl_label = "Clear Growing Objects"
    
    def execute(self, context):
        if 'growing_objects' in bpy.context.scene:
            # Clear the list
            bpy.context.scene['growing_objects'] = []
            bpy.context.scene['initial_object_properties'] = {}
            clear_collections(bpy.context.scene) 
            bpy.types.Scene.plant_type = bpy.props.EnumProperty(
            name="Plant Type",
            description="Type of plant to use in the scene",
            items=get_plant_types
            )
            print("Growing objects list cleared")
        else:
            print("Growing objects list not found")

        # Remove all mesh objects in the scene
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_by_type(type='MESH')
        bpy.ops.object.delete()
        
        # Remove all camera objects in the scene
        bpy.ops.object.select_all(action='DESELECT')  # Deselect all objects first
        bpy.ops.object.select_by_type(type='CAMERA')  # Select all camera objects
        bpy.ops.object.delete()  # Delete all selected cameras

        return {'FINISHED'}
    
# Operator: Add plane
class OBJECT_OT_AddCustomPlane(bpy.types.Operator):
    """Add a Custom Plane"""
    bl_idname = "mesh.add_custom_plane"
    bl_label = "Add Custom Plane"
    
    def execute(self, context):
        scene = context.scene
        size = scene.plane_size
        color = scene.plane_color

        # Add the plane with the specified size and color
        bpy.ops.mesh.primitive_plane_add(size=size, enter_editmode=False, align='WORLD', location=(0, 0, 0))
        plane = bpy.context.active_object
        plane.name = "soil"

        # Apply color to the plane
        self.set_color_plane(plane, color)

        return {'FINISHED'}
    
    def set_color_plane(self, obj, color):
        mat = bpy.data.materials.new(name="SoilMaterial")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = color
        obj.data.materials.append(mat)

        
# Operator: Add camera
class OBJECT_OT_AddCamera(bpy.types.Operator):
    """Add a Camera to the Scene"""
    bl_idname = "object.add_camera"
    bl_label = "Add Camera"

    def execute(self, context):
        scene = context.scene
        
        plane_obj = bpy.data.objects.get("soil")
        
        if not plane_obj:
            self.report({'ERROR'}, "Please add plane to the scene")
            return {'CANCELLED'}

        else:
            cam_data = bpy.data.cameras.new(name='New_Scene_Camera')
        
            cam_obj = bpy.data.objects.new('New_Scene_Camera', cam_data)
            
            scene.collection.objects.link(cam_obj)
                # Calculate camera position
            plane_dimensions = plane_obj.dimensions
            plane_center = plane_obj.location
            
            # Set the camera distance based on the size of the plane, and lift it up
            camera_distance = max(plane_dimensions.x, plane_dimensions.y) * 3.5
            camera_height = plane_dimensions.z + 6.0  # Adjust multiplier as needed
            
            # Set camera to look from behind the plane and above, looking at the center
            cam_obj.location = Vector((plane_center.x, plane_center.y - camera_distance, plane_center.z  + camera_height))
            
            # Make the camera look at the center of the plane
            self.look_at(cam_obj, plane_center)

        return {'FINISHED'}
    
    def look_at(self, obj, target):
        """Direct an object's -Z axis to look towards a target point.""" 
        direction = target - obj.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        obj.rotation_euler = rot_quat.to_euler()

# Function to add a new node
def create_branch(scene,parent_collection):
    branch_collection_name = f"{parent_collection.name}_Branch"
    branch_collection = bpy.data.collections.new(branch_collection_name)
    parent_collection.children.link(branch_collection)  # Link the new branch collection as a child
    print(f"{branch_collection_name} added to {parent_collection.name} ")
    return branch_collection
    
def create_branch_object(parent_obj, branch_collection):
    parent_obj.select_set(True)
    bpy.context.view_layer.objects.active = parent_obj
    parent_obj.select_set(False)
    
    new_obj = clone_cylinder(parent_obj, branch_collection)
    new_obj.select_set(True)
    bpy.context.view_layer.objects.active = new_obj
        
    new_obj.name = branch_collection.name                    # adjust name of new node
    new_obj.location = get_top_cylinder(parent_obj)  # adjust location of new node to top of older
    rotate_rand(parent_obj, new_obj, 45)             # rotate new node
    scale_factor = parent_obj.scale[0] + 0.002       # scale new node
      
      
def add_new_node(scene,collection):
    obj = bpy.data.collections.get(collection.name)
    if collection.objects:
        obj = collection.objects[-1]
        print(f"The last object in the collection '{collection.name}' is: {obj.name}")
        new_obj = clone_cylinder(obj, collection)
    
        new_obj.select_set(True)
        bpy.context.view_layer.objects.active = new_obj

        new_obj.name = collection.name                    # adjust name of new node
        new_obj.location = get_top_cylinder(obj)  # adjust location of new node to top of older
        rotate_rand(obj, new_obj, 45)             # rotate new node
        new_obj.select_set(False)
        
        if scene.frame_current % 4 == 0: 
            print(scene.frame_current)
            new_branch_collection = create_branch(scene,collection)
            create_branch_object(new_obj, new_branch_collection)
        else:
            print("Don't add branch")
            
    else:
        print(f"The collection '{collection.name}' has no objects.")    
        
# Growth Handler
def grow_mesh_handler(scene):
    if scene.grow_mesh_running: 
        collections = bpy.data.collections
        plant_type = scene.plant_type
        # Iterate over each collection
        print(f"Current frame is: {scene.frame_current} ")
        
        # grow main tree
#        if scene.frame_current % 2 == 0:
#            collection_names = [c.name for c in collections if "Branch" not in c.name]
#            for c_name in collection_names:
#                print(f"Target tree: {c_name} ")  
#                add_new_node(scene,bpy.data.collections.get(c_name))
#        
#            if scene.frame_current % 4 == 0: 
#                # grow branches
#                branches_names = [c.name for c in collections if "Branch" in c.name]
#                for c_name in branches_names:
#                    print(f"Growing branch: {c_name} ")  
#                    add_new_node(scene,bpy.data.collections.get(c_name))
        
        for c in collections:
            # grow only main
            if "TREE" in c.name and "Branch" not in c.name:
                if scene.frame_current % 2 == 0:
                    print(f"Target plant: {c.name} ")
                    add_new_node(scene,bpy.data.collections.get(c.name))
                    
            elif "SHRUB" in c.name and "Branch" not in c.name:
                if scene.frame_current % 4 == 0:
                    print(f"Target plant: {c.name} ")
                    add_new_node(scene,bpy.data.collections.get(c.name))
            
            # grow branches
            if "TREE" in c.name and "Branch" in c.name:
                if scene.frame_current % 10 == 0:
                    print(f"Target plant: {c.name} ")
                    add_new_node(scene,bpy.data.collections.get(c.name))
                    
            elif "SHRUB" in c.name and "Branch" in c.name:
                if scene.frame_current % 5 == 0:
                    print(f"Target plant: {c.name} ")
                    add_new_node(scene,bpy.data.collections.get(c.name))
            
            
def get_plant_types(self, context):
    # This could be dynamic based on some other data or a fixed list
    types = [
        ("TREE", "Tree", "Large and perennial plant"),
        ("SHRUB", "Shrub", "Small to medium-sized perennial plant"),
    ]
    return types
        
# Operator to start/stop the animation----------------------

def stop_animation_at_end_frame(scene):
    if scene.frame_current >= scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=False)
        scene.grow_mesh_running = False
        # Remove only the stop_animation_at_end_frame handler
        bpy.app.handlers.frame_change_post.remove(stop_animation_at_end_frame)
        print("Animation stopped at end frame: {}".format(scene.frame_end))

class OBJECT_OT_GrowScene(bpy.types.Operator):
    """Grow the plant without recording"""
    bl_idname = "mesh.grow_scene"
    bl_label = "Grow Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.grow_mesh_running = not context.scene.grow_mesh_running

        context.scene.render.fps = context.scene.custom_frame_per_second
        context.scene.render.fps_base = 1.0
        context.scene.frame_start = context.scene.custom_frame_start
        context.scene.frame_end = context.scene.custom_frame_end
        
        if context.scene.grow_mesh_running:
            # Check if the handler is already added to avoid duplicates
            if stop_animation_at_end_frame not in bpy.app.handlers.frame_change_post:
                bpy.app.handlers.frame_change_post.append(stop_animation_at_end_frame)
            bpy.ops.screen.animation_play()
        else:
            context.scene.grow_mesh_running = False
            bpy.ops.screen.animation_cancel(restore_frame=False)
            # Remove the handler when stopping the animation manually
            if stop_animation_at_end_frame in bpy.app.handlers.frame_change_post:
                bpy.app.handlers.frame_change_post.remove(stop_animation_at_end_frame)

        return {'FINISHED'}

    
class OBJECT_OT_GrowRenderScene(bpy.types.Operator):
    """Grow the plant with recording and save to C:/Animation/"""
    bl_idname = "mesh.grow_render_scene"
    bl_label = "Grow and Render Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.grow_mesh_running = not context.scene.grow_mesh_running
        
        context.scene.render.fps = context.scene.custom_frame_per_second
        context.scene.render.fps_base = 1.0
        context.scene.frame_start = context.scene.custom_frame_start
        context.scene.frame_end = context.scene.custom_frame_end
        camera = bpy.data.objects.get("New_Scene_Camera")
        
        if context.scene.grow_mesh_running:
            if not camera:
                self.report({'ERROR'}, "Please add plane to the scene")
                return {'CANCELLED'}
            else: 
                context.scene.render.filepath = "C:/Animation/"  # Change to your preferred path
                context.scene.render.image_settings.file_format = 'FFMPEG'  # Set the output format (FFMPEG for video)
                context.scene.render.ffmpeg.format = 'MPEG4'
                context.scene.render.ffmpeg.codec = 'H264'
                context.scene.render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
                context.scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
                print("Animation setup complete: {} weeks at {} fps".format((context.scene.frame_end - context.scene.frame_start + 1) / 2, context.scene.render.fps))
            
                bpy.ops.screen.animation_play()
                # Start rendering the animation
                bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
        else:
            context.scene.grow_mesh_running = False
            bpy.ops.screen.animation_cancel(restore_frame=False)
            
        return {'FINISHED'}
    
# Operator for reset animation
class OBJECT_OT_ResetAnimation(bpy.types.Operator):
    """Reset animation"""
    bl_idname = "mesh.reset_animation"
    bl_label = "Reset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.context.scene.frame_current = 0
        self.reset_objects_to_initial_state(context)
        return {'FINISHED'}
    
    def clear_nested_collections(self,collection):
        # Recursive function to clear out nested collections
        while collection.children:
            child_collection = collection.children[0]
            clear_collection_objects(child_collection)
            self.clear_nested_collections(child_collection)
            collection.children.unlink(child_collection)
            bpy.data.collections.remove(child_collection)
        
    def reset_objects_to_initial_state(self, context):
        initial_properties = context.scene.get('initial_object_properties', {})
     
        for obj_name, props in initial_properties.items():
            location=props['location']
            radius=props['radius'] 
            height=props['height']
            collection_name=props['collection_name']
            
            collection = bpy.data.collections.get(collection_name)
            
            self.clear_nested_collections(collection)
            
            for obj in collection.objects:
                # Remove object from the current collection
                collection.objects.unlink(obj)
                # Delete the object data if no other users
                if obj.users == 0:
                    bpy.data.objects.remove(obj)
                    
            x,y,z = location
            
            add_cylinder((x, y, z - z), radius, height, collection)
            cursor_location_update((x, y, z - z))
            origin_to_cursor()
            all_objects = bpy.context.scene.objects

            # Deselect all objects
            for obj in all_objects:
                obj.select_set(False)
    
# Utilities for plants --------------------------------------------------
def set_color(color_val, obj):
    name = obj.name
    mesh_object = bpy.data.objects.get(name)

    if mesh_object:
        material = bpy.data.materials.new(name=name)
        material.use_nodes = False  
        material.diffuse_color = color_val
        mesh_object.data.materials.append(material)

def cursor_location_update(location):
    x, y, z = location
    bpy.context.scene.cursor.location[0] = x
    bpy.context.scene.cursor.location[1] = y
    bpy.context.scene.cursor.location[2] = z

def origin_to_cursor():
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

def add_cylinder(location, radius, height, collection):
    """ Add cylinder to the collection tree """
    location = (location[0], location[1], location[2] + height / 2)
    
    bpy.ops.mesh.primitive_cylinder_add(enter_editmode=False, radius=radius, depth=height, location=location)
    bpy.ops.object.shade_smooth()
    obj = bpy.context.active_object
    obj.name = collection.name
    set_color((0.5, 0.2, 0.1, 1.0), obj)
    
    collection.objects.link(obj)
    
    bpy.context.scene.collection.objects.unlink(obj)
    
    initial_properties = bpy.context.scene.get('initial_object_properties', {})
    if obj.name not in bpy.context.scene['initial_object_properties']:
        initial_properties[obj.name] = {'location': location[:], 'radius': radius, 'height': height, 'collection_name': collection.name}
        bpy.context.scene['initial_object_properties'] = initial_properties
    
    return obj

def set_scene_units():
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 0.01  
    bpy.context.scene.unit_settings.length_unit = 'CENTIMETERS'
    
def plant_new(x, y, location_z, scale_factor):
    """Create a new collection for the tree"""
    unique_suffix = str(uuid.uuid4())[:3]  # Take only the first 8 characters for brevity
    plant_type = bpy.context.scene.plant_type
    unique_name = f"{plant_type}_{unique_suffix}"
    new_collection = bpy.data.collections.new(unique_name)
    bpy.context.scene.collection.children.link(new_collection)
    
    # Example: a young tree might be 0.05 meters (5 cm) in radius and 0.5 meters (50 cm) tall
    add_cylinder((x, y, location_z), 0.05 * scale_factor, 0.5 * scale_factor, new_collection)
    
    cursor_location_update((x, y, location_z - location_z))
    origin_to_cursor()
    all_objects = bpy.context.scene.objects

    # Deselect all objects
    for obj in all_objects:
        obj.select_set(False)
    
    print(f"Planted {new_collection.name} at ({x:.2f},{y:.2f})")

# End of plant utilities ---------------------------------------------------------------------
# Node adjustment -----------------------------------------
def rotate_quar(obj, new_obj, angle, axis):
    quar_obj = obj.rotation_quaternion
    direction = Quaternion(axis, angle)
    rotation_matrix = direction.to_matrix()
    new_obj.rotation_euler = rotation_matrix.to_euler()

def rotate_rand(obj, new_obj, angle):
    min_value = -1.0
    max_value = 1.0
    
    x = random.uniform(min_value, max_value)
    y = random.uniform(min_value, max_value)
    z = random.uniform(min_value, max_value)
    
    rotate_quar(obj, new_obj, angle, (x, y, z))
    bpy.context.view_layer.update()

def cursor_location_update(location):
    x, y, z = location
    bpy.context.scene.cursor.location[0] = x
    bpy.context.scene.cursor.location[1] = y
    bpy.context.scene.cursor.location[2] = z

def origin_to_cursor():
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

def set_up_init_cylinder(location, rotation):
    x, y, z = location
    bpy.ops.mesh.primitive_cylinder_add(radius=0.01, depth=0.1, location=location, rotation=rotation)
    cursor_location_update((x, y, z - z))
    origin_to_cursor()
    a = bpy.context.active_object
    return a

def get_top_cylinder(obj):
    local_top_coordinate = Vector((0, 0, obj.dimensions.z))
    world_top_coordinate = obj.matrix_world @ local_top_coordinate
    return world_top_coordinate

def clone_cylinder(obj, collection):
    a = obj.copy()
    collection.objects.link(a)
#    new_cyl = bpy.context.collection.objects[index]
    return a

class OBJECT_OT_PlantMesh(bpy.types.Operator):
    """Add plant to scene"""
    bl_idname = "mesh.plant_mesh"
    bl_label = "Plant Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Get user input properties
        scale_factor = context.scene.plant_mesh_scale
        z = context.scene.plant_mesh_location_z 
        x = context.scene.plant_mesh_location_x
        y = context.scene.plant_mesh_location_y
        
        if 'growing_objects' not in bpy.context.scene:
            bpy.context.scene['growing_objects'] = []
        # Initialize the dictionary if it doesn't exist
        if 'initial_object_properties' not in context.scene:
            context.scene['initial_object_properties'] = {}
        if 'age_object' not in context.scene:
            context.scene['age_object'] = {}

        plant_new(x,y,z,scale_factor)
            
        return {'FINISHED'}

class OBJECT_OT_AddRandomPlants(bpy.types.Operator):
    """Add Random Plants in Specified Area"""
    bl_idname = "object.add_random_plants"
    bl_label = "Add Random Plants"

    def execute(self, context):
        plane_obj = bpy.data.objects.get("soil")
        plane_size = context.scene.plane_size
            
        if not plane_obj:
            self.report({'ERROR'}, "Please add plane to the scene")
            return {'CANCELLED'}

        else:
            if plane_obj:
                plane_dimensions = plane_obj.dimensions
                plane_center = plane_obj.location
            scale_factor = context.scene.plant_mesh_scale
            plant_count = context.scene.plant_count
            base_x = plane_dimensions.x  - plane_size*1.5
            base_y = plane_dimensions.y - plane_size*1.5
            base_z = context.scene.plant_mesh_location_z

            for _ in range(plant_count):
                x = random.uniform(base_x, base_x + plane_size)
                y = random.uniform(base_y, base_y + plane_size)
                z = base_z  # Assuming plants are placed at a constant height

                # Assuming you have a function to add a plant at a location
                plant_new(x,y,z,scale_factor)

        return {'FINISHED'}
    
class OBJECT_PT_PlantMeshPanel(bpy.types.Panel):
    bl_label = "Garden Planning"
    bl_idname = "OBJECT_PT_PlantMeshPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Garden Planning'

    def draw(self, context):
        layout = self.layout

        layout.label(text="Plant properties:")
        layout.prop(context.scene, "plant_type", text="Plant Type")
        layout.prop(context.scene, "plant_mesh_scale", text="Plant Scale")
        
        layout.label(text="Exact plant placement:")
        layout.prop(context.scene, "plant_mesh_location_x", text="Plant X")
        layout.prop(context.scene, "plant_mesh_location_y", text="Plant Y")
        layout.prop(context.scene, "plant_mesh_location_z", text="Plant Z")
        layout.operator("mesh.plant_mesh", text="Plant Mesh")
        
        
        layout.label(text="Random plant placement:")
        layout.prop(context.scene, "plant_count", text="Number of Plants")
        
        layout.operator("object.add_random_plants", text="Add Plants Randomly")
        # Add button to trigger the growth
        
         # Add button to clear the scene and empty growing_objects
        layout.label(text="Clear scene:")
        layout.operator("scene.clear_growing_objects", text="Clear Scene")
        
        layout.label(text="Setting up scene:")
        # Add UI elements for size and color
        layout.prop(context.scene, "plane_size", text="Plane Size")
        layout.prop(context.scene, "plane_color", text="Plane Color")

        # Button to add plane using the current size and color settings
        layout.operator("mesh.add_custom_plane", text="Add Plane")
        # Add camera and plane
        layout.operator("object.add_camera", text="Add Camera")
        
        
        
        layout.label(text="Start/Stop Animation:")
        
        # Add button to start/stop animation
        layout.prop(context.scene, "custom_frame_start", text="Start Week")
        layout.prop(context.scene, "custom_frame_end", text="End Week")
        layout.prop(context.scene, "custom_frame_per_second", text="Frame per Second")
        
        layout.operator("mesh.grow_scene", text="Grow scene")
        layout.operator("mesh.grow_render_scene", text="Grow and render scene")
        
        layout.operator("mesh.reset_animation", text="Reset")
        
        
classes_registered = False

def unregister():
    global classes_registered

    if classes_registered:
        try:
            bpy.utils.unregister_class(OBJECT_OT_PlantMesh)
            bpy.utils.unregister_class(OBJECT_PT_PlantMeshPanel)
            bpy.utils.unregister_class(ClearGrowingObjectsOperator)
            bpy.utils.unregister_class(OBJECT_OT_AddCamera)
            bpy.utils.unregister_class(OBJECT_OT_AddCustomPlane)
            bpy.utils.unregister_class(OBJECT_PT_PlantMeshPanel)
            bpy.utils.unregister_class(OBJECT_OT_GrowScene)
            bpy.utils.unregister_class(OBJECT_OT_GrowRenderScene)
            bpy.utils.unregister_class(OBJECT_OT_ResetAnimation)
            bpy.utils.unregister_class(OBJECT_OT_AddRandomPlants)
            bpy.utils.unregister_class(PLANT_PT_ControlPanel)

        except ValueError:
            pass  # Class was not registered, ignore the error

        # Remove custom properties from the Scene type
        if hasattr(bpy.types.Scene, 'plant_mesh_scale'):
            del bpy.types.Scene.plant_mesh_scale
        if hasattr(bpy.types.Scene, 'plant_mesh_location_x'):
            del bpy.types.Scene.plant_mesh_location_x
        if hasattr(bpy.types.Scene, 'plant_mesh_location_y'):
            del bpy.types.Scene.plant_mesh_location_y
        if hasattr(bpy.types.Scene, 'plant_mesh_location_z'):
            del bpy.types.Scene.plant_mesh_location_z
        if hasattr(bpy.types.Scene, 'grow_mesh_running'):
            del bpy.types.Scene.grow_mesh_running
        if hasattr(bpy.types.Scene, 'growing_objects'):
            del bpy.types.Scene.growing_objects
            
        bpy.app.handlers.frame_change_post.remove(grow_mesh_handler)
        for handler in bpy.app.handlers.frame_change_pre[:]:
            bpy.app.handlers.frame_change_pre.remove(handler)
        
        del bpy.types.Scene.camera_location_x
        del bpy.types.Scene.camera_location_y
        del bpy.types.Scene.camera_location_z
        del bpy.types.Scene.custom_plane_size
        del bpy.types.Scene.custom_plane_color
        del bpy.types.Scene.custom_frame_per_second
        del bpy.types.Scene.plane_size
        del bpy.types.Scene.plane_color
        del bpy.types.Scene.plant_type
        del bpy.types.Scene.plant_count

        classes_registered = False
        
def register():
    global classes_registered

    if not classes_registered:
        bpy.utils.register_class(OBJECT_OT_AddCamera)
        bpy.types.Scene.custom_plane_size = bpy.props.FloatProperty(name="Plane Size", default=2.0)
        bpy.types.Scene.custom_plane_color = bpy.props.FloatVectorProperty(name="Plane Color", subtype='COLOR', default=(0.6, 0.4, 0.1, 1.0), size=4, min=0.0, max=1.0)
        bpy.utils.register_class(OBJECT_OT_AddCustomPlane)
        
        # growth
        bpy.utils.register_class(OBJECT_OT_GrowScene)
        bpy.utils.register_class(OBJECT_OT_GrowRenderScene)
        bpy.utils.register_class(OBJECT_OT_ResetAnimation)
        bpy.app.handlers.frame_change_post.append(grow_mesh_handler)
        
        
        bpy.utils.register_class(OBJECT_OT_PlantMesh)
        bpy.utils.register_class(OBJECT_OT_AddRandomPlants)
        bpy.utils.register_class(OBJECT_PT_PlantMeshPanel)
        bpy.utils.register_class(ClearGrowingObjectsOperator)
        

        # Create and add scene properties only if they don't exist
        if not hasattr(bpy.types.Scene, 'plant_mesh_location_x'):
            bpy.types.Scene.plant_mesh_location_x = bpy.props.FloatProperty(default=0.0)
        if not hasattr(bpy.types.Scene, 'plant_mesh_location_y'):
            bpy.types.Scene.plant_mesh_location_y = bpy.props.FloatProperty(default=0.0)
        if not hasattr(bpy.types.Scene, 'plant_mesh_location_z'):
            bpy.types.Scene.plant_mesh_location_z = bpy.props.FloatProperty(default=0.0)
        if not hasattr(bpy.types.Scene, 'grow_mesh_running'):
            bpy.types.Scene.grow_mesh_running = bpy.props.BoolProperty(default=False)
        if not hasattr(bpy.types.Scene, 'growing_objects'):
            bpy.types.Scene.growing_objects = []
        if not hasattr(bpy.types.Scene, 'plant_mesh_scale'):
           bpy.types.Scene.plant_mesh_scale = bpy.props.FloatProperty(default=1.0, min=1.0)
        
        bpy.types.Scene.plane_size = bpy.props.FloatProperty(
        name="Plane Size",
        description="Size of the plane",
        default=2.0,
        min=0.1,
        max=10.0
        )
        
        bpy.types.Scene.plane_color = bpy.props.FloatVectorProperty(
            name="Plane Color",
            description="Color of the plane",
            subtype='COLOR',
            default=(0.03, 0.10, 0.013, 1.0),
            min=0.0,
            max=1.0,
            size=4
        )
        
        bpy.types.Scene.custom_frame_start = bpy.props.IntProperty(
        name="Start Week",
        default=1,
        min=1,
        )
        
        bpy.types.Scene.custom_frame_end = bpy.props.IntProperty(
            name="End Week",
            default=12,
            min=1,
        )
        
        bpy.types.Scene.custom_frame_per_second = bpy.props.IntProperty(
            name="Frame per Second",
            default=1,
            min=1,
            max=5
        )
        
        bpy.types.Scene.plant_type = bpy.props.EnumProperty(
            name="Plant Type",
            description="Type of plant to use in the scene",
            items=get_plant_types
        )
        
        bpy.types.Scene.plant_count = bpy.props.IntProperty(
            name="Plant Count",
            description="Number of plants to add",
            default=5,
            min=1
        )
        
        classes_registered = True
        

    
if __name__ == "__main__":
    register()
