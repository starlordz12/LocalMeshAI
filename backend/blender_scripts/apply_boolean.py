"""Headless Blender boolean applier.

Invoked as::

    blender --background --factory-startup --python apply_boolean.py -- spec.json

``spec.json`` schema::

    {
      "base":   "/abs/base.stl",
      "output": "/abs/result.stl",
      "helpers": [
        {"file": "/abs/helper_0.stl", "mode": "additive"|"subtractive", "name": "..."}
      ]
    }

All meshes share one coordinate frame (mm). Import/export use matching axis settings so the
round-trip is identity. The boolean modifier prefers the MANIFOLD solver (Blender 4.5+) and
falls back to EXACT, which is the right choice for thin-wall / tangent-cut geometry.

Lines tagged ``[LMAI]`` are parsed by the backend and shown in the UI log.
"""
import json
import sys

import bpy


def log(msg: str) -> None:
    print(f"[LMAI] {msg}")


def get_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_stl(path: str):
    before = set(bpy.data.objects)
    try:
        # Blender 4.x native importer; explicit axes => identity round-trip.
        bpy.ops.wm.stl_import(filepath=path, forward_axis="Y", up_axis="Z", global_scale=1.0)
    except Exception:
        try:
            bpy.ops.preferences.addon_enable(module="io_mesh_stl")
        except Exception:
            pass
        bpy.ops.import_mesh.stl(filepath=path)  # legacy operator (Z-up, raw coords)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        raise RuntimeError(f"No mesh object imported from {path}")
    return new[0]


def export_stl(obj, path: str):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.wm.stl_export(
            filepath=path, export_selected_objects=True,
            forward_axis="Y", up_axis="Z", global_scale=1.0,
        )
    except Exception:
        try:
            bpy.ops.preferences.addon_enable(module="io_mesh_stl")
        except Exception:
            pass
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)


def set_solver(mod) -> str:
    for solver in ("MANIFOLD", "EXACT"):
        try:
            mod.solver = solver
            return solver
        except (TypeError, ValueError):
            continue
    return getattr(mod, "solver", "DEFAULT")


def apply_boolean(base, tool, operation: str) -> str:
    mod = base.modifiers.new(name="lmai_bool", type="BOOLEAN")
    mod.object = tool
    mod.operation = operation  # UNION | DIFFERENCE
    solver = set_solver(mod)
    bpy.ops.object.select_all(action="DESELECT")
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return solver


def main():
    args = get_args()
    if not args:
        raise SystemExit("[LMAI] ERROR: no spec.json argument provided")
    with open(args[0], "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    clear_scene()
    base = import_stl(spec["base"])
    base.name = "lmai_base"
    log(f"base imported: {len(base.data.polygons)} polys")

    for helper in spec.get("helpers", []):
        mode = helper["mode"]
        name = helper.get("name", "helper")
        tool = import_stl(helper["file"])
        op = "UNION" if mode == "additive" else "DIFFERENCE"
        try:
            solver = apply_boolean(base, tool, op)
            log(f"{op} '{name}' solver={solver} -> {len(base.data.polygons)} polys")
        except Exception as exc:  # keep going? no -> fail loudly
            log(f"ERROR applying {op} '{name}': {exc}")
            raise
        finally:
            if tool.name in bpy.data.objects:
                bpy.data.objects.remove(tool, do_unlink=True)

    export_stl(base, spec["output"])
    log("exported result")


if __name__ == "__main__":
    main()
