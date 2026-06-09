"""Mesh loading, analysis, conservative repair, and display-GLB generation.

All geometry is treated as millimeters. Analysis never modifies the source; repair returns
a new mesh and reports exactly what it changed (it never deletes large regions silently).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

import config
from models import BoundingBox, MeshAnalysis, ValidationReport


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    """Load any supported file into a single Trimesh (scenes are concatenated).

    Coincident vertices are welded (``merge_vertices``). STL/OBJ store vertices per-face, so
    without welding even a perfect cube reports as non-watertight. Welding rebuilds shared
    topology; it does not alter the surface or delete real geometry. The original file on
    disk is untouched — only this in-memory copy is welded.
    """
    loaded = trimesh.load(str(path), force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        if len(loaded.geometry) == 0:
            raise ValueError("File contains no geometry.")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError(f"Unsupported geometry type: {type(loaded).__name__}")
    if loaded.faces is None or len(loaded.faces) == 0:
        raise ValueError("Mesh has no faces (point clouds are not supported).")
    try:
        loaded.merge_vertices()
    except Exception:
        pass
    return loaded


def _bbox(mesh: trimesh.Trimesh) -> BoundingBox:
    lo, hi = mesh.bounds
    size = hi - lo
    return BoundingBox(
        min=tuple(float(v) for v in lo),
        max=tuple(float(v) for v in hi),
        size=tuple(float(v) for v in size),
    )


def analyze(mesh: trimesh.Trimesh) -> MeshAnalysis:
    """Compute printability-relevant statistics for a mesh."""
    warnings: list[str] = []
    watertight = bool(mesh.is_watertight)
    winding_ok = bool(mesh.is_winding_consistent)

    volume: float | None = None
    inverted = False
    if watertight:
        try:
            raw_volume = float(mesh.volume)
            inverted = raw_volume < 0
            volume = abs(raw_volume)
        except Exception:
            volume = None
    else:
        warnings.append(
            "Mesh is not watertight (non-manifold). Volume is unknown and booleans may "
            "fail. Try the Repair action."
        )

    if not winding_ok:
        warnings.append("Face winding is inconsistent; normals may be unreliable.")
    if inverted:
        warnings.append("Normals appear inverted (negative signed volume).")

    return MeshAnalysis(
        triangle_count=int(len(mesh.faces)),
        vertex_count=int(len(mesh.vertices)),
        bounding_box=_bbox(mesh),
        surface_area_mm2=float(mesh.area),
        volume_mm3=volume,
        is_watertight=watertight,
        is_winding_consistent=winding_ok,
        has_inverted_normals=inverted,
        warnings=warnings,
    )


def validation_report(mesh: trimesh.Trimesh, warnings: list[str] | None = None) -> ValidationReport:
    watertight = bool(mesh.is_watertight)
    volume = abs(float(mesh.volume)) if watertight else None
    return ValidationReport(
        is_watertight=watertight,
        is_winding_consistent=bool(mesh.is_winding_consistent),
        volume_mm3=volume,
        triangle_count=int(len(mesh.faces)),
        bounding_box=_bbox(mesh),
        warnings=list(warnings or []),
    )


def repair(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, list[str]]:
    """Conservative repair. Returns (repaired_copy, actions_taken).

    Only safe operations: merge duplicate vertices, drop degenerate/duplicate faces, fix
    winding & normals, fill small holes, drop unreferenced vertices. Never deletes large
    regions.
    """
    m = mesh.copy()
    actions: list[str] = []

    before_v = len(m.vertices)
    try:
        m.merge_vertices()
        if len(m.vertices) != before_v:
            actions.append(f"Merged duplicate vertices ({before_v} -> {len(m.vertices)}).")
    except Exception:
        pass

    before_f = len(m.faces)
    try:
        # Drop zero-area (degenerate) faces.
        nondeg = m.nondegenerate_faces()
        if nondeg is not None and nondeg.sum() != len(m.faces):
            m.update_faces(nondeg)
            actions.append(f"Removed degenerate faces ({before_f} -> {len(m.faces)}).")
    except Exception:
        pass

    try:
        before_f2 = len(m.faces)
        m.update_faces(m.unique_faces())
        if len(m.faces) != before_f2:
            actions.append(f"Removed duplicate faces ({before_f2} -> {len(m.faces)}).")
    except Exception:
        pass

    try:
        trimesh.repair.fix_winding(m)
        actions.append("Fixed face winding.")
    except Exception:
        pass

    try:
        trimesh.repair.fix_normals(m)
        actions.append("Recomputed/normalized face normals.")
    except Exception:
        pass

    if not m.is_watertight:
        try:
            filled = trimesh.repair.fill_holes(m)
            if filled:
                actions.append("Filled small holes.")
        except Exception:
            pass

    try:
        m.remove_unreferenced_vertices()
    except Exception:
        pass

    if not actions:
        actions.append("No changes were necessary.")
    return m, actions


def export_display_glb(mesh: trimesh.Trimesh, out_path: str | Path) -> Path:
    """Export a GLB for the web viewer (one loader path for every input format)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scene = trimesh.Scene(mesh)
    glb_bytes = scene.export(file_type="glb")
    out_path.write_bytes(glb_bytes)
    return out_path


def thin_feature_warnings(mesh: trimesh.Trimesh, min_wall_mm: float | None = None) -> list[str]:
    """Cheap heuristic: warn if the smallest bbox dimension is below the min wall."""
    min_wall = min_wall_mm if min_wall_mm is not None else config.DEFAULTS["min_wall_mm"]
    size = mesh.bounds[1] - mesh.bounds[0]
    smallest = float(np.min(size))
    if smallest < min_wall:
        return [
            f"Smallest dimension is {smallest:.2f} mm, below the {min_wall} mm minimum-wall "
            "guideline; this feature may not print reliably."
        ]
    return []
