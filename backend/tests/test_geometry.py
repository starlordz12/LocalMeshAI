"""Geometry-layer tests: helper builders, analysis, repair, and the trimesh boolean engine."""
import numpy as np
import trimesh

import config
from models import Operation
from services import helpers, mesh_analyzer, trimesh_engine


def _cube(size=20.0):
    return trimesh.creation.box(extents=(size, size, size))


def test_analyze_cube_is_watertight():
    a = mesh_analyzer.analyze(_cube())
    assert a.is_watertight
    assert a.triangle_count == 12
    assert a.volume_mm3 is not None
    assert abs(a.volume_mm3 - 20**3) < 1.0
    np.testing.assert_allclose(a.bounding_box.size, (20, 20, 20), atol=1e-6)


def test_helper_box_dimensions():
    op = Operation(id="op1", name="b", feature="box", mode="additive", scale_mm=(10, 6, 4))
    mesh = helpers.build_helper(op)
    size = mesh.bounds[1] - mesh.bounds[0]
    np.testing.assert_allclose(size, (10, 6, 4), atol=1e-6)
    assert mesh.is_watertight


def test_helper_mounting_pad_with_holes_is_watertight():
    op = Operation(
        id="op2", name="pad", feature="mounting_pad", mode="glue_on",
        scale_mm=(28, 14, 3),
        parameters={"holeCount": 2, "holeDiameterMm": 2.2, "holeSpacingMm": 20.0},
    )
    mesh = helpers.build_helper(op)
    assert mesh.is_watertight
    size = mesh.bounds[1] - mesh.bounds[0]
    np.testing.assert_allclose(size, (28, 14, 3), atol=1e-3)


def test_screw_boss_has_hole_and_is_watertight():
    op = Operation(id="op3", name="boss", feature="screw_boss", mode="additive",
                   parameters={"outerDiameterMm": 6, "holeDiameterMm": 2.2, "heightMm": 6})
    mesh = helpers.build_helper(op)
    assert mesh.is_watertight
    # A tube has genus 1 -> Euler characteristic 0.
    assert mesh.euler_number == 0


def test_all_catalog_features_build_watertight():
    for group in helpers.FEATURE_CATALOG.values():
        for entry in group:
            op = Operation(
                id=f"op_{entry['feature']}", name=entry["label"],
                feature=entry["feature"],
                mode="subtractive" if entry in helpers.FEATURE_CATALOG["subtractive"] else "additive",
                scale_mm=tuple(entry.get("defaultScaleMm", (20, 10, 3))),
                parameters=entry.get("params", {}),
            )
            mesh = helpers.build_helper(op)
            assert len(mesh.faces) > 0, entry["feature"]
            assert mesh.is_watertight, f"{entry['feature']} not watertight"


def test_repair_reports_actions():
    repaired, actions = mesh_analyzer.repair(_cube())
    assert isinstance(actions, list) and actions
    assert repaired.is_watertight


def test_trimesh_boolean_union_and_difference():
    if not trimesh_engine.available():
        import pytest

        pytest.skip("manifold3d not installed")
    base = _cube(20)
    add = trimesh.creation.box(extents=(10, 10, 10))
    add.apply_translation((15, 0, 0))  # overlaps the +X face
    cut = trimesh.creation.cylinder(radius=3, height=40, sections=48)

    result, log = trimesh_engine.apply_helpers(
        base, [("additive", add, "block"), ("subtractive", cut, "hole")]
    )
    assert result.is_watertight
    assert len(log) >= 3
    # Union should grow the bbox in +X; difference removes volume.
    assert result.bounds[1][0] > 10.0


def test_thin_feature_warning():
    thin = trimesh.creation.box(extents=(20, 20, 0.4))
    warns = mesh_analyzer.thin_feature_warnings(thin, config.DEFAULTS["min_wall_mm"])
    assert warns and "minimum-wall" in warns[0]
