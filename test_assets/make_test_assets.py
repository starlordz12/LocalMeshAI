"""Generate the small test meshes used by tests and manual QA.

Run from the repo root or this folder:

    python test_assets/make_test_assets.py

Requires `trimesh` (installed with the backend requirements). Output STLs are CC BY 4.0,
not MIT — see LICENSE-ASSETS.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent


def make_cube_20mm() -> trimesh.Trimesh:
    """A 20 mm watertight cube centered on the origin."""
    return trimesh.creation.box(extents=(20.0, 20.0, 20.0))


def make_plate_with_hole() -> trimesh.Trimesh:
    """A 40x30x4 mm plate with a 6 mm through-hole (boolean difference)."""
    plate = trimesh.creation.box(extents=(40.0, 30.0, 4.0))
    hole = trimesh.creation.cylinder(radius=3.0, height=20.0, sections=64)
    # cylinder axis is +Z by default; plate thickness is along Z, so it already lines up.
    result = trimesh.boolean.difference([plate, hole])
    if result is None or result.is_empty:
        # Fallback if no boolean engine is available: return the plain plate.
        return plate
    return result


def main() -> None:
    assets = {
        "cube_20mm.stl": make_cube_20mm(),
        "plate_with_hole.stl": make_plate_with_hole(),
    }
    for name, mesh in assets.items():
        out = HERE / name
        mesh.export(out)
        size = mesh.bounds[1] - mesh.bounds[0]
        print(f"wrote {out.name:24s} size(mm)={np.round(size, 2)} watertight={mesh.is_watertight}")


if __name__ == "__main__":
    main()
