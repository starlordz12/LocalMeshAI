"""Boolean engine backed by headless Blender.

This is the robust path used when a Blender executable is found. It exports the base mesh
and helper meshes to a temp directory, runs ``blender_scripts/apply_boolean.py`` in
``--background`` mode, and loads the resulting STL back. The boolean modifier uses the
MANIFOLD solver, which handles thin-wall and tangent-cut geometry well.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import trimesh

import config

SCRIPT = config.BACKEND_DIR / "blender_scripts" / "apply_boolean.py"


def available() -> bool:
    return config.blender_available()


def apply_helpers(
    base: trimesh.Trimesh, helpers: list[tuple[str, trimesh.Trimesh, str]]
) -> tuple[trimesh.Trimesh, list[str]]:
    """Apply ``helpers`` to ``base`` via headless Blender. Returns (result_mesh, log)."""
    blender = config.find_blender()
    if not blender:
        raise RuntimeError("Blender executable not found.")

    log: list[str] = [f"engine=blender ({blender})"]

    with tempfile.TemporaryDirectory(prefix="localmeshai_") as td:
        tmp = Path(td)
        base_path = tmp / "base.stl"
        base.export(base_path)

        spec_helpers = []
        for idx, (mode, mesh, name) in enumerate(helpers):
            hp = tmp / f"helper_{idx}.stl"
            mesh.export(hp)
            spec_helpers.append({"file": str(hp), "mode": mode, "name": name})

        output_path = tmp / "result.stl"
        spec = {"base": str(base_path), "output": str(output_path), "helpers": spec_helpers}
        spec_path = tmp / "spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")

        cmd = [
            blender,
            "--background",
            "--factory-startup",
            "--python",
            str(SCRIPT),
            "--",
            str(spec_path),
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Blender boolean timed out after 300s.") from exc

        # Surface only the lines our script tagged, to keep the UI log readable.
        for line in (proc.stdout or "").splitlines():
            if line.startswith("[LMAI]"):
                log.append(line.replace("[LMAI]", "blender:").strip())

        if not output_path.exists():
            tail = "\n".join((proc.stdout or "").splitlines()[-15:])
            err = (proc.stderr or "").strip()
            raise RuntimeError(
                "Blender did not produce an output mesh. "
                f"stderr: {err[:500]}\n--- stdout tail ---\n{tail}"
            )

        result = trimesh.load(output_path, force="mesh", process=False)
        if isinstance(result, trimesh.Scene):
            result = trimesh.util.concatenate(tuple(result.geometry.values()))

    log.append(f"result_tris={len(result.faces)}")
    return result, log
