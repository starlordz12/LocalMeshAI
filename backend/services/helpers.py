"""Parametric helper-feature mesh builders.

Each builder turns an :class:`Operation` (dimensions in mm, parameters dict) into a clean,
watertight :class:`trimesh.Trimesh` positioned and rotated in the scene. Where a feature has
holes (tabs, bosses, pads), the hole is built into the 2D cross-section and extruded, so we
get a watertight result **without** needing a 3D boolean engine.

These same builders are the authoritative source for exports; the frontend renders an
equivalent three.js preview for live editing.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon
from shapely.geometry import box as shapely_box

import config
from models import Operation

_SECTIONS = 64  # cylinder smoothness


# --- small parameter helpers -----------------------------------------------------------


def _f(params: dict[str, Any], key: str, default: float) -> float:
    try:
        v = params.get(key, default)
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(params: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(params.get(key, default))
    except (TypeError, ValueError):
        return default


def _center(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Translate so the mesh bounding-box center is at the origin."""
    lo, hi = mesh.bounds
    mesh.apply_translation(-(lo + hi) / 2.0)
    return mesh


# --- primitive builders ----------------------------------------------------------------


def _box(sx: float, sy: float, sz: float) -> trimesh.Trimesh:
    return trimesh.creation.box(extents=(max(sx, 1e-3), max(sy, 1e-3), max(sz, 1e-3)))


def _cylinder(radius: float, height: float) -> trimesh.Trimesh:
    return trimesh.creation.cylinder(radius=max(radius, 1e-3), height=max(height, 1e-3),
                                     sections=_SECTIONS)


def _annulus(outer_r: float, inner_r: float, height: float) -> trimesh.Trimesh:
    """A tube (outer circle with a concentric hole), extruded `height` along Z, centered."""
    outer_r = max(outer_r, 1e-3)
    inner_r = max(min(inner_r, outer_r - 1e-3), 0.0)
    outer = Point(0, 0).buffer(outer_r, quad_segs=_SECTIONS // 4)
    if inner_r > 0:
        inner = Point(0, 0).buffer(inner_r, quad_segs=_SECTIONS // 4)
        ring = outer.difference(inner)
    else:
        ring = outer
    mesh = trimesh.creation.extrude_polygon(ring, height=max(height, 1e-3))
    return _center(mesh)


def _plate_with_holes(
    length: float, width: float, thickness: float, holes: list[tuple[float, float, float]]
) -> trimesh.Trimesh:
    """Flat plate (length=X, width=Y, thickness=Z) with optional through holes.

    `holes` is a list of (cx, cy, radius) in plate-local coordinates centered on the plate.
    """
    plate = shapely_box(-length / 2, -width / 2, length / 2, width / 2)
    for cx, cy, r in holes:
        if r > 0:
            plate = plate.difference(Point(cx, cy).buffer(r, quad_segs=_SECTIONS // 4))
    mesh = trimesh.creation.extrude_polygon(plate, height=max(thickness, 1e-3))
    return _center(mesh)


def _triangle_prism(length: float, height: float, width: float, ramp: bool = True) -> trimesh.Trimesh:
    """A wedge/gusset. Triangle in X(length)-Y(height), extruded `width` along Z.

    ramp=True -> right triangle rising front->back (fairing).
    ramp=False -> symmetric gusset triangle.
    """
    if ramp:
        tri = Polygon([(0, 0), (length, 0), (length, height)])
    else:
        tri = Polygon([(0, 0), (length, 0), (0, height)])
    mesh = trimesh.creation.extrude_polygon(tri, height=max(width, 1e-3))
    return _center(mesh)


# --- feature dispatch ------------------------------------------------------------------


def _hole_pattern(op: Operation) -> list[tuple[float, float, float]]:
    """Build a hole pattern for pads/tabs from parameters.

    Recognized params: holeCount, holeDiameterMm, holeSpacingMm.
    Holes are laid out along X, centered, on the plate midline.
    """
    p = op.parameters
    count = _i(p, "holeCount", 0)
    if count <= 0:
        return []
    dia = _f(p, "holeDiameterMm", config.DEFAULTS["pilot_hole_mm"])
    spacing = _f(p, "holeSpacingMm", 20.0)
    r = dia / 2.0
    if count == 1:
        return [(0.0, 0.0, r)]
    start = -spacing * (count - 1) / 2.0
    return [(start + i * spacing, 0.0, r) for i in range(count)]


def build_base_mesh(op: Operation) -> trimesh.Trimesh:
    """Build the un-transformed helper mesh (centered at origin) for an operation."""
    sx, sy, sz = (float(v) for v in op.scale_mm)
    p = op.parameters
    feat = op.feature

    # --- additive boxes / flat parts ---
    if feat in ("box", "box_cutout", "rectangular_slot", "vent_slot", "pocket"):
        return _box(sx, sy, sz)

    if feat in ("mounting_pad", "flat_pad", "glue_plate", "mounting_deck"):
        thickness = sz if sz > 0 else config.DEFAULTS["default_helper_thickness_mm"]
        return _plate_with_holes(sx, sy, thickness, _hole_pattern(op))

    # --- cylinders / holes / channels ---
    if feat in ("cylinder", "cylinder_hole"):
        radius = _f(p, "radiusMm", _f(p, "diameterMm", sx) / 2.0 if "diameterMm" in p else sx / 2.0)
        height = _f(p, "heightMm", sz)
        return _cylinder(radius, height)

    if feat == "screw_clearance_hole":
        dia = _f(p, "holeDiameterMm", config.DEFAULTS["m3_clearance_mm"])
        height = _f(p, "heightMm", sz if sz > 0 else 10.0)
        return _cylinder(dia / 2.0, height)

    if feat == "cable_channel":
        # A round channel lying along X (length = sx), radius from cable diameter.
        dia = _f(p, "cableDiameterMm", _f(p, "diameterMm", min(sy, sz) if min(sy, sz) > 0 else 4.0))
        length = sx if sx > 0 else 30.0
        mesh = _cylinder(dia / 2.0, length)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        return _center(mesh)

    # --- screw boss: solid tube with a pilot hole (no boolean needed) ---
    if feat == "screw_boss":
        outer_d = _f(p, "outerDiameterMm", sx if sx > 0 else 6.0)
        hole_d = _f(p, "holeDiameterMm", config.DEFAULTS["pilot_hole_mm"])
        height = _f(p, "heightMm", sz if sz > 0 else 6.0)
        return _annulus(outer_d / 2.0, hole_d / 2.0, height)

    # --- mounting tab: flat tab with a single hole near one end ---
    if feat == "mounting_tab":
        length = sx if sx > 0 else 18.0
        width = sy if sy > 0 else 10.0
        thickness = sz if sz > 0 else config.DEFAULTS["default_helper_thickness_mm"]
        hole_d = _f(p, "holeDiameterMm", config.DEFAULTS["m3_clearance_mm"])
        # Hole sits at 70% toward the +X end by default.
        hx = _f(p, "holeOffsetMm", length * 0.5 - max(width, hole_d * 2) * 0.5)
        return _plate_with_holes(length, width, thickness, [(hx, 0.0, hole_d / 2.0)])

    # --- cable guide: horizontal tube the cable threads through (along X) ---
    if feat == "cable_guide":
        outer_d = _f(p, "outerDiameterMm", max(sy, sz) if max(sy, sz) > 0 else 8.0)
        cable_d = _f(p, "cableDiameterMm", _f(p, "innerDiameterMm", 4.0))
        length = sx if sx > 0 else 12.0
        mesh = _annulus(outer_d / 2.0, cable_d / 2.0, length)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        return _center(mesh)

    # --- rib / gusset ---
    if feat == "rib_gusset":
        return _triangle_prism(sx if sx > 0 else 15.0, sy if sy > 0 else 15.0,
                               sz if sz > 0 else 3.0, ramp=False)

    # --- aerodynamic fairing / ramp ---
    if feat == "fairing":
        return _triangle_prism(sx if sx > 0 else 30.0, sz if sz > 0 else 8.0,
                               sy if sy > 0 else 16.0, ramp=True)

    # --- custom / fallback ---
    return _box(sx, sy, sz)


def build_helper(op: Operation) -> trimesh.Trimesh:
    """Build a fully placed helper mesh: base shape + rotation + translation.

    Subtractive cutters are inflated very slightly to avoid exactly-coplanar faces, which are
    a classic cause of boolean failures.
    """
    mesh = build_base_mesh(op)

    if op.mode == "subtractive":
        # Inflate ~0.2% about the centroid so cut faces don't land exactly coplanar.
        mesh.apply_scale(1.002)

    rx, ry, rz = (math.radians(float(a)) for a in op.rotation_deg)
    rot = trimesh.transformations.euler_matrix(rx, ry, rz, axes="sxyz")
    mesh.apply_transform(rot)
    mesh.apply_translation([float(v) for v in op.position_mm])

    # Make sure normals are outward / consistent for clean booleans & export.
    try:
        mesh.fix_normals()
    except Exception:
        pass
    return mesh


# --- feature catalog (served to the UI so the toolbar/inspector stay in sync) -----------

FEATURE_CATALOG = {
    "additive": [
        {"feature": "box", "label": "Box / Block", "defaultScaleMm": [20, 20, 10]},
        {"feature": "cylinder", "label": "Cylinder", "defaultScaleMm": [10, 10, 10]},
        {"feature": "screw_boss", "label": "Screw Boss", "defaultScaleMm": [6, 6, 6],
         "params": {"outerDiameterMm": 6.0, "holeDiameterMm": 2.2, "heightMm": 6.0}},
        {"feature": "mounting_tab", "label": "Mounting Tab", "defaultScaleMm": [18, 10, 3],
         "params": {"holeDiameterMm": 3.2}},
        {"feature": "mounting_pad", "label": "Flat Mounting Pad", "defaultScaleMm": [28, 14, 3],
         "params": {"holeCount": 2, "holeDiameterMm": 2.2, "holeSpacingMm": 20.0}},
        {"feature": "mounting_deck", "label": "Camera Mounting Deck", "defaultScaleMm": [28, 14, 3],
         "params": {"holeCount": 2, "holeDiameterMm": 2.2, "holeSpacingMm": 20.0}},
        {"feature": "glue_plate", "label": "Glue-on Plate", "defaultScaleMm": [25, 25, 2.5]},
        {"feature": "rib_gusset", "label": "Rib / Gusset", "defaultScaleMm": [15, 15, 3]},
        {"feature": "cable_guide", "label": "Cable Guide", "defaultScaleMm": [12, 8, 8],
         "params": {"cableDiameterMm": 4.0, "outerDiameterMm": 8.0}},
        {"feature": "fairing", "label": "Aero Fairing / Wedge", "defaultScaleMm": [30, 16, 8]},
    ],
    "subtractive": [
        {"feature": "box_cutout", "label": "Box Cutout", "defaultScaleMm": [12, 12, 12]},
        {"feature": "cylinder_hole", "label": "Cylinder Hole", "defaultScaleMm": [6, 6, 20],
         "params": {"diameterMm": 6.0}},
        {"feature": "rectangular_slot", "label": "Rectangular Slot", "defaultScaleMm": [20, 4, 10]},
        {"feature": "cable_channel", "label": "Cable Channel", "defaultScaleMm": [40, 4, 4],
         "params": {"cableDiameterMm": 4.0}},
        {"feature": "vent_slot", "label": "Vent Slot", "defaultScaleMm": [25, 2.5, 12]},
        {"feature": "screw_clearance_hole", "label": "Screw Clearance Hole",
         "defaultScaleMm": [3.2, 3.2, 20], "params": {"holeDiameterMm": 3.2}},
        {"feature": "pocket", "label": "Pocket Cutout", "defaultScaleMm": [20, 15, 4]},
    ],
}
