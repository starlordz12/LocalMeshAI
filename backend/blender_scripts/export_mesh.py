"""Headless Blender format conversion (auxiliary).

Converts one mesh file to another format via Blender, for formats the trimesh path does not
cover (or for parity testing).

    blender --background --factory-startup --python export_mesh.py -- in.stl out.obj
"""
import sys

import bpy


def get_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def import_any(path: str):
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
        raise SystemExit(f"[LMAI] Unsupported input format: {path}")


def export_any(path: str):
    lower = path.lower()
    if lower.endswith(".stl"):
        try:
            bpy.ops.wm.stl_export(filepath=path)
        except Exception:
            bpy.ops.export_mesh.stl(filepath=path)
    elif lower.endswith(".obj"):
        try:
            bpy.ops.wm.obj_export(filepath=path)
        except Exception:
            bpy.ops.export_scene.obj(filepath=path)
    elif lower.endswith((".glb", ".gltf")):
        bpy.ops.export_scene.gltf(filepath=path)
    else:
        raise SystemExit(f"[LMAI] Unsupported output format: {path}")


def main():
    args = get_args()
    if len(args) < 2:
        raise SystemExit("[LMAI] usage: export_mesh.py -- in.ext out.ext")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_any(args[0])
    export_any(args[1])
    print(f"[LMAI] converted {args[0]} -> {args[1]}")


if __name__ == "__main__":
    main()
