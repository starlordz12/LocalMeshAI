"""Geometry engine dispatcher.

Picks a boolean backend (Blender if available, else trimesh+manifold3d), builds helper
meshes from the operation tree, applies additive/subtractive helpers in order, and produces
validated export files. glue-on helpers are exported as their own bodies, never merged.

The dispatcher is the seam that lets the geometry layer move to a remote microservice later
without touching the API surface or the UI.
"""
from __future__ import annotations

from pathlib import Path

import trimesh

import config
from models import Operation, Project, ValidationReport
from services import blender_engine, helpers, mesh_analyzer, project_store, trimesh_engine


class GeometryError(RuntimeError):
    pass


def selected_engine() -> str:
    if blender_engine.available():
        return "blender"
    if trimesh_engine.available():
        return "trimesh+manifold3d"
    return "none"


def boolean_supported() -> bool:
    return selected_engine() != "none"


def _load_base(project: Project, mesh_id: str) -> trimesh.Trimesh:
    import math

    import trimesh.transformations as tf

    mesh_info = project_store.get_mesh(project, mesh_id)
    abs_path = project_store.resolve_relative(project.id, mesh_info.source_file)
    if not abs_path.exists():
        raise GeometryError(f"Source mesh file is missing: {mesh_info.source_file}")
    mesh = mesh_analyzer.load_mesh(abs_path)

    # Apply the same orientation transform the viewer shows, so the export matches the
    # on-screen placement (rotation in degrees XYZ, then translation in mm).
    rx, ry, rz = (math.radians(float(a)) for a in mesh_info.rotation_deg)
    if any((rx, ry, rz)):
        mesh.apply_transform(tf.euler_matrix(rx, ry, rz, axes="sxyz"))
    if any(float(v) for v in mesh_info.position_mm):
        mesh.apply_translation([float(v) for v in mesh_info.position_mm])
    return mesh


def _collect_helpers(
    project: Project, mesh_id: str, operation_ids: list[str] | None
) -> list[tuple[str, trimesh.Trimesh, str]]:
    """Build (mode, mesh, name) tuples for additive/subtractive helpers targeting mesh_id."""
    selected = set(operation_ids) if operation_ids else None
    built: list[tuple[str, trimesh.Trimesh, str]] = []
    for op in project.operations:
        if op.type != "helper_feature" or op.suppressed:
            continue
        if op.mode == "glue_on":
            continue
        if op.target_mesh_id and op.target_mesh_id != mesh_id:
            continue
        if selected is not None and op.id not in selected:
            continue
        try:
            mesh = helpers.build_helper(op)
        except Exception as exc:  # noqa: BLE001
            raise GeometryError(f"Failed to build helper '{op.name}' ({op.feature}): {exc}") from exc
        built.append((op.mode, mesh, op.name))
    return built


def apply_tree(
    project: Project, mesh_id: str, operation_ids: list[str] | None = None
) -> tuple[trimesh.Trimesh, str, list[str], ValidationReport, ValidationReport]:
    """Apply the operation tree to a mesh. Returns
    (result, engine, log, before_report, after_report)."""
    base = _load_base(project, mesh_id)
    before = mesh_analyzer.validation_report(base)

    helper_meshes = _collect_helpers(project, mesh_id, operation_ids)
    if not helper_meshes:
        return base, "none", ["No applicable additive/subtractive helpers."], before, before

    if not boolean_supported():
        raise GeometryError(
            "No boolean engine is available. Install Blender, or the manifold3d package, to "
            "apply union/difference. You can still export helpers as separate glue-on STLs."
        )

    engine = selected_engine()
    if engine == "blender":
        result, log = blender_engine.apply_helpers(base, helper_meshes)
    else:
        result, log = trimesh_engine.apply_helpers(base, helper_meshes)

    warnings: list[str] = []
    if not result.is_watertight:
        warnings.append("Result is not watertight; the boolean may have produced open edges.")
    after = mesh_analyzer.validation_report(result, warnings)
    return result, engine, log, before, after


# --- exporting -------------------------------------------------------------------------


_EXPORT_EXT = {"stl": ".stl", "obj": ".obj", "3mf": ".3mf"}


def _export_mesh(mesh: trimesh.Trimesh, out_path: Path, fmt: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "3mf":
        # trimesh exports 3MF via the "3mf" type.
        mesh.export(out_path, file_type="3mf")
    else:
        mesh.export(out_path)


def export_final(
    project: Project, mesh_id: str, fmt: str = "stl"
) -> tuple[Path, ValidationReport, str, list[str]]:
    """Bake the operation tree into a single mesh and export it. Returns
    (rel_path, validation, engine, log)."""
    if fmt not in _EXPORT_EXT:
        raise GeometryError(f"Unsupported export format: {fmt}")
    result, engine, log, _before, after = apply_tree(project, mesh_id)

    out_name = f"export_{mesh_id}{_EXPORT_EXT[fmt]}"
    out_path = project_store.derived_dir(project.id) / out_name
    _export_mesh(result, out_path, fmt)

    rel = out_path.relative_to(project_store.project_dir(project.id))
    return rel, after, engine, log


def export_helper(
    project: Project, operation_id: str, fmt: str = "stl"
) -> tuple[Path, ValidationReport, list[str]]:
    """Export a single helper as its own STL (the glue-on piece). Returns
    (rel_path, validation, log)."""
    if fmt not in _EXPORT_EXT:
        raise GeometryError(f"Unsupported export format: {fmt}")
    op: Operation | None = project_store.get_operation(project, operation_id)
    if op is None:
        raise GeometryError(f"Operation not found: {operation_id}")
    if op.type != "helper_feature":
        raise GeometryError("Only helper features can be exported as separate pieces.")

    mesh = helpers.build_helper(op)
    log = [f"helper '{op.name}' ({op.feature}) tris={len(mesh.faces)}"]

    warnings = mesh_analyzer.thin_feature_warnings(mesh, project.settings.min_wall_mm)
    validation = mesh_analyzer.validation_report(mesh, warnings)

    out_name = f"helper_{operation_id}{_EXPORT_EXT[fmt]}"
    out_path = project_store.derived_dir(project.id) / out_name
    _export_mesh(mesh, out_path, fmt)

    rel = out_path.relative_to(project_store.project_dir(project.id))
    return rel, validation, log
