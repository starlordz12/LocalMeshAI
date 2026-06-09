"""Headless Blender mesh analysis (auxiliary).

The default analysis path in LocalMeshAI uses trimesh; this script exists so analysis can
optionally run through Blender for parity testing or for formats only Blender can read.

    blender --background --factory-startup --python analyze_mesh.py -- in.stl

Prints a single ``[LMAI-JSON] {...}`` line with triangle count, bbox, and volume.
"""
import json
import sys

import bpy
import bmesh


def get_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def import_any(path: str):
    before = set(bpy.data.objects)
    lower = path.lower()
    if lower.endswith(".stl"):
        try:
            bpy.ops.wm.stl_import(filepath=path)
        except Exception:
            bpy.ops.import_mesh.stl(filepath=path)
    elif lower.endswith(".obj"):
        try:
            bpy.ops.wm.obj_import(filepath=path)
        except Exception:
            bpy.ops.import_scene.obj(filepath=path)
    elif lower.endswith(".ply"):
        try:
            bpy.ops.wm.ply_import(filepath=path)
        except Exception:
            bpy.ops.import_mesh.ply(filepath=path)
    else:
        raise SystemExit(f"[LMAI] Unsupported format: {path}")
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        raise SystemExit("[LMAI] No mesh imported")
    return new[0]


def main():
    args = get_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = import_any(args[0])

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    volume = bm.calc_volume()
    bm.free()

    bbox = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs = [c.x for c in bbox]; ys = [c.y for c in bbox]; zs = [c.z for c in bbox]
    info = {
        "triangleCount": len(obj.data.polygons),
        "vertexCount": len(obj.data.vertices),
        "boundingBox": {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        },
        "volumeMm3": abs(volume),
    }
    print("[LMAI-JSON] " + json.dumps(info))


if __name__ == "__main__":
    main()
