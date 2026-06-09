"""Runtime configuration and environment detection for the LocalMeshAI backend.

No absolute paths are hardcoded: everything is derived relative to this file, or read from
environment variables so the app is portable across machines.
"""
from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path

# --- Paths -----------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

# Workspace where user projects live. Overridable for tests / packaging.
PROJECTS_DIR = Path(os.environ.get("LOCALMESHAI_PROJECTS", REPO_ROOT / "projects")).resolve()
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Printability defaults (mm) --------------------------------------------------------

DEFAULTS = {
    "units": "mm",
    "min_wall_mm": 0.8,
    "pilot_hole_mm": 2.2,
    "m3_clearance_mm": 3.2,
    "default_fillet_mm": 0.8,
    "default_helper_thickness_mm": 2.5,
}

# --- CORS ------------------------------------------------------------------------------

# Default to the Vite dev origins. Override with a comma-separated LOCALMESHAI_CORS list.
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",  # vite preview
]


def cors_origins() -> list[str]:
    env = os.environ.get("LOCALMESHAI_CORS")
    if env:
        return [o.strip() for o in env.split(",") if o.strip()]
    return DEFAULT_CORS_ORIGINS


# --- Blender detection -----------------------------------------------------------------

_WINDOWS_BLENDER_GLOBS = [
    r"C:\Program Files\Blender Foundation\*\blender.exe",
    r"C:\Program Files (x86)\Blender Foundation\*\blender.exe",
]
_POSIX_BLENDER_CANDIDATES = [
    "/usr/bin/blender",
    "/usr/local/bin/blender",
    "/snap/bin/blender",
    "/Applications/Blender.app/Contents/MacOS/Blender",
]


@lru_cache(maxsize=1)
def find_blender() -> str | None:
    """Return a path to a Blender executable, or None if not found.

    Search order:
      1. LOCALMESHAI_BLENDER env var (explicit override)
      2. `blender` on PATH
      3. Common install locations per-OS
    """
    explicit = os.environ.get("LOCALMESHAI_BLENDER")
    if explicit and Path(explicit).exists():
        return explicit

    on_path = shutil.which("blender")
    if on_path:
        return on_path

    if os.name == "nt":
        import glob

        for pattern in _WINDOWS_BLENDER_GLOBS:
            matches = sorted(glob.glob(pattern), reverse=True)  # newest version first
            if matches:
                return matches[0]
    else:
        for candidate in _POSIX_BLENDER_CANDIDATES:
            if Path(candidate).exists():
                return candidate
    return None


def blender_available() -> bool:
    return find_blender() is not None


@lru_cache(maxsize=1)
def manifold_available() -> bool:
    try:
        import manifold3d  # noqa: F401

        return True
    except Exception:
        return False


def active_boolean_engine() -> str:
    """Name of the engine that will be used for booleans, for UI display."""
    if blender_available():
        return "blender"
    if manifold_available():
        return "trimesh+manifold3d"
    return "none"
