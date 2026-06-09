"""Project workspace persistence.

A project is a folder under ``projects/<id>/`` containing:

    project.json      operation tree + metadata (source of truth)
    sources/          original imported meshes (never modified)
    _derived/         display GLBs and exported STLs (regenerable)

The original imported file is always copied into ``sources/`` and never mutated.
"""
from __future__ import annotations

import re
import secrets
import shutil
from pathlib import Path

import config
from models import MeshInfo, Operation, Project

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class ProjectNotFoundError(Exception):
    pass


class MeshNotFoundError(Exception):
    pass


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def _safe_filename(name: str) -> str:
    name = Path(name).name  # strip any directory components
    name = _SAFE_NAME.sub("_", name).strip("_")
    return name or "mesh"


# --- Directory helpers -----------------------------------------------------------------


def project_dir(project_id: str) -> Path:
    return config.PROJECTS_DIR / project_id


def sources_dir(project_id: str) -> Path:
    return project_dir(project_id) / "sources"


def derived_dir(project_id: str) -> Path:
    return project_dir(project_id) / "_derived"


def project_json_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def resolve_relative(project_id: str, relative: str) -> Path:
    """Resolve a project-relative path and guard against traversal."""
    base = project_dir(project_id).resolve()
    target = (base / relative).resolve()
    if base not in target.parents and target != base:
        raise ValueError(f"Path escapes project workspace: {relative}")
    return target


# --- CRUD ------------------------------------------------------------------------------


def create_project(name: str = "Untitled Project") -> Project:
    pid = _gen_id("proj")
    pdir = project_dir(pid)
    sources_dir(pid).mkdir(parents=True, exist_ok=True)
    derived_dir(pid).mkdir(parents=True, exist_ok=True)
    project = Project(id=pid, name=name)
    save_project(project)
    return project


def project_exists(project_id: str) -> bool:
    return project_json_path(project_id).exists()


def load_project(project_id: str) -> Project:
    path = project_json_path(project_id)
    if not path.exists():
        raise ProjectNotFoundError(project_id)
    data = path.read_text(encoding="utf-8")
    return Project.model_validate_json(data)


def save_project(project: Project) -> None:
    import models  # local import to avoid cycle at module import time

    project.updated_at = models._now()
    pdir = project_dir(project.id)
    pdir.mkdir(parents=True, exist_ok=True)
    sources_dir(project.id).mkdir(parents=True, exist_ok=True)
    derived_dir(project.id).mkdir(parents=True, exist_ok=True)
    # Write atomically: temp file then replace.
    tmp = project_json_path(project.id).with_suffix(".json.tmp")
    tmp.write_text(project.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
    tmp.replace(project_json_path(project.id))


def list_projects() -> list[dict]:
    out: list[dict] = []
    for child in config.PROJECTS_DIR.iterdir():
        if child.is_dir() and (child / "project.json").exists():
            try:
                p = load_project(child.name)
                out.append({"id": p.id, "name": p.name, "updatedAt": p.updated_at})
            except Exception:
                continue
    return sorted(out, key=lambda d: d["updatedAt"], reverse=True)


# --- Mesh import -----------------------------------------------------------------------


SUPPORTED_IMPORT_EXT = {".stl", ".obj", ".ply", ".3mf"}


def save_source_mesh(project_id: str, data: bytes, original_name: str) -> tuple[str, Path, str]:
    """Persist an uploaded mesh into ``sources/``. Returns (mesh_id, abs_path, ext)."""
    if not project_exists(project_id):
        raise ProjectNotFoundError(project_id)
    ext = Path(original_name).suffix.lower()
    if ext not in SUPPORTED_IMPORT_EXT:
        raise ValueError(
            f"Unsupported import format '{ext}'. Supported: "
            + ", ".join(sorted(SUPPORTED_IMPORT_EXT))
        )
    mesh_id = _gen_id("mesh")
    safe = _safe_filename(original_name)
    dest = sources_dir(project_id) / f"{mesh_id}__{safe}"
    dest.write_bytes(data)
    return mesh_id, dest, ext.lstrip(".")


def add_mesh(project: Project, mesh: MeshInfo) -> None:
    project.meshes.append(mesh)


def get_mesh(project: Project, mesh_id: str) -> MeshInfo:
    for m in project.meshes:
        if m.id == mesh_id:
            return m
    raise MeshNotFoundError(mesh_id)


# --- Operations ------------------------------------------------------------------------


def upsert_operation(project: Project, operation: Operation) -> None:
    for i, existing in enumerate(project.operations):
        if existing.id == operation.id:
            project.operations[i] = operation
            return
    project.operations.append(operation)


def get_operation(project: Project, operation_id: str) -> Operation | None:
    for op in project.operations:
        if op.id == operation_id:
            return op
    return None


def remove_operation(project: Project, operation_id: str) -> bool:
    before = len(project.operations)
    project.operations = [op for op in project.operations if op.id != operation_id]
    return len(project.operations) != before


def delete_project(project_id: str) -> None:
    pdir = project_dir(project_id)
    if pdir.exists():
        shutil.rmtree(pdir, ignore_errors=True)
