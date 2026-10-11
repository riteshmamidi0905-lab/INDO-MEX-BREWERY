#!/usr/bin/env python3
"""Headless Blender orthographic front render of STL studies + comparison montage (Sprint 15). Concept form studies only; no marks (D-66).
Usage: python3 tools/render_ortho.py OUT.png a.stl b.stl ...   (each rendered at the same scale, labelled by filename)"""
import subprocess, sys, os, tempfile
from PIL import Image, ImageDraw
SCRIPT = '''
import bpy, sys
a = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=a[0]); o = bpy.context.selected_objects[0]
m = bpy.data.materials.new("m"); m.use_nodes=True; b=m.node_tree.nodes["Principled BSDF"]; b.inputs[0].default_value=(0.85,0.85,0.88,1); b.inputs[2].default_value=0.35; o.data.materials.append(m)
bpy.ops.object.light_add(type="SUN", rotation=(0.9,0.2,0.6)); bpy.context.object.data.energy=3
bpy.ops.object.camera_add(location=(0,-500,125), rotation=(1.5708,0,0)); c=bpy.context.object; c.data.type="ORTHO"; c.data.ortho_scale=275; bpy.context.scene.camera=c
w=bpy.data.worlds.new("w"); w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.93,0.93,0.92,1); bpy.context.scene.world=w
s=bpy.context.scene; s.render.engine="BLENDER_EEVEE"; s.render.resolution_x=360; s.render.resolution_y=640; s.render.filepath=a[1]
bpy.ops.render.render(write_still=True)
'''
if __name__ == "__main__":
    out, stls = sys.argv[1], sys.argv[2:]; f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False); f.write(SCRIPT); f.close(); ims = []
    for s in stls:
        png = tempfile.mktemp(suffix=".png"); r = subprocess.run(["blender", "-b", "-P", f.name, "--", os.path.abspath(s), png], capture_output=True, text=True, timeout=300)
        if not os.path.exists(png): sys.exit("render failed\n" + r.stdout[-600:])
        im = Image.open(png).convert("RGB"); ImageDraw.Draw(im).text((10, 10), os.path.basename(s), fill=(20, 20, 20)); ims.append(im)
    M = Image.new("RGB", (360 * len(ims), 640), "white")
    for i, im in enumerate(ims): M.paste(im, (360 * i, 0))
    M.save(out); print("montage", out, M.size)
