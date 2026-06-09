"""Boolean engine backed by trimesh + manifold3d.

This is the fallback path that works with **no Blender installed**. manifold3d produces
watertight CSG results. Helpers are applied in operation order: additive -> union,
subtractive -> difference. glue-on helpers are never merged here.
"""
from __future__ import annotations

import trimesh

import config


class BooleanUnavailableError(RuntimeError):
    pass


def available() -> bool:
    return config.manifold_available()


def _as_mesh(result) -> trimesh.Trimesh:
    if isinstance(result, trimesh.Trimesh):
        return result
    if isinstance(result, (list, tuple)) and result:
        return trimesh.util.concatenate(result)
    if isinstance(result, trimesh.Scene):
        return trimesh.util.concatenate(tuple(result.geometry.values()))
    raise ValueError("Boolean returned no usable geometry.")


def apply_helpers(
    base: trimesh.Trimesh, helpers: list[tuple[str, trimesh.Trimesh, str]]
) -> tuple[trimesh.Trimesh, list[str]]:
    """Apply ``helpers`` to ``base``.

    helpers: list of (mode, mesh, name) where mode is "additive" or "subtractive".
    Returns (result_mesh, log_lines). Raises on hard failure.
    """
    if not available():
        raise BooleanUnavailableError(
            "No boolean engine available. Install Blender or the manifold3d package."
        )

    log: list[str] = [f"engine=trimesh+manifold3d, base_tris={len(base.faces)}"]
    result = base.copy()

    for mode, mesh, name in helpers:
        tris = len(mesh.faces)
        try:
            if mode == "additive":
                result = _as_mesh(trimesh.boolean.union([result, mesh], engine="manifold"))
                log.append(f"union  '{name}' (+{tris} tris) -> {len(result.faces)} tris")
            elif mode == "subtractive":
                result = _as_mesh(trimesh.boolean.difference([result, mesh], engine="manifold"))
                log.append(f"diff   '{name}' (-{tris} tris) -> {len(result.faces)} tris")
            else:
                log.append(f"skip   '{name}' (mode={mode} not merged)")
        except Exception as exc:  # noqa: BLE001 - surface the engine's reason to the user
            raise RuntimeError(
                f"Boolean {mode} failed on helper '{name}': {exc}. "
                "Check that both meshes are watertight and actually overlap."
            ) from exc

    try:
        result.fix_normals()
    except Exception:
        pass
    return result, log
