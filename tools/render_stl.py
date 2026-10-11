#!/usr/bin/env python3
"""Headless Blender preview render of an STL (Sprint 14). Concept visualization only; no brand marks. Usage: python3 tools/render_stl.py in.stl out.png"""
import subprocess, sys, tempfile, os
SCRIPT = '''
import bpy, sys
a = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=a[0]) if hasattr(bpy.ops.wm,"stl_import") else bpy.ops.import_mesh.stl(filepath=a[0])
o = bpy.context.selected_objects[0]; o.location.z = 0
bpy.ops.mesh.primitive_plane_add(size=1, location=(0,0,-1)); bpy.context.object.scale=(1,1,1)
m = bpy.data.materials.new("glass"); m.use_nodes=True; n=m.node_tree.nodes; n.clear(); o_=n.new("ShaderNodeOutputMaterial"); g=n.new("ShaderNodeBsdfGlass"); m.node_tree.links.new(g.outputs[0], o_.inputs[0]); o.data.materials.append(m)
bpy.ops.object.light_add(type="AREA", location=(0.2,-0.3,0.4)); bpy.context.object.data.energy=400; bpy.context.object.data.size=0.3
bpy.ops.object.camera_add(location=(0.0,-0.55,0.12), rotation=(1.45,0,0)); bpy.context.scene.camera=bpy.context.object
for v in o.data.vertices: pass
o.scale=(0.001,0.001,0.001)
w=bpy.data.worlds.new('w'); w.use_nodes=True; w.node_tree.nodes['Background'].inputs[1].default_value=1.0; w.node_tree.nodes['Background'].inputs[0].default_value=(0.55,0.5,0.45,1); bpy.context.scene.world=w
s=bpy.context.scene; s.render.engine="CYCLES"; s.cycles.samples=48; s.cycles.device="CPU"; s.cycles.use_denoising=False; s.render.resolution_x=640; s.render.resolution_y=640; s.render.filepath=a[1]
bpy.ops.render.render(write_still=True)
'''
if __name__ == "__main__":
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False); f.write(SCRIPT); f.close()
    r = subprocess.run(["blender", "-b", "-P", f.name, "--", os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])], capture_output=True, text=True, timeout=300)
    print("rendered" if os.path.exists(sys.argv[2]) else "FAILED\n" + r.stdout[-800:] + r.stderr[-400:])
