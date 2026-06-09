# Changelog

All notable changes to LocalMeshAI are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — 0.1.0 MVP scaffold

- **Repository structure** for a real open-source project: docs, issue templates,
  dual licensing (MIT for code, CC BY 4.0 for assets).
- **Backend (FastAPI):**
  - Project workspace store (create / load / save JSON projects).
  - Mesh import for STL, OBJ, PLY, 3MF with normalization to a display GLB.
  - Mesh analysis: bounding box, volume, surface area, triangle count, watertight check.
  - Operation tree (additive / subtractive / glue-on helper features) persisted as JSON.
  - Parametric helper feature generators (box, cylinder, screw boss, mounting tab,
    mounting pad, rib/gusset, cable guide, fairing wedge, cutouts, channels, vents...).
  - Geometry engine dispatcher with two backends:
    - **Blender** headless (robust booleans) when available.
    - **trimesh + manifold3d** fallback (works with no Blender installed).
  - Export: final STL (booleans baked) and per-helper STL (glue-on pieces).
  - AI planner adapter interface with a working **rule-based** planner plus
    Ollama / Anthropic / OpenAI placeholders (no API key required for MVP).
- **Frontend (React + Vite + TypeScript + three.js / r3f / drei):**
  - 3D viewport: orbit / pan / zoom, grid build plate, axes gizmo, bounding box,
    mm dimensions, transform gizmo for helpers.
  - Toolbar, Object/Operation tree, Inspector, AI panel, status console.
  - Parametric helper preview rendered live in the scene.
  - Pencil/annotation mode that captures intent and converts to helper features.
  - Display modes: solid / wireframe / transparent / x-ray.

### Notes

- Conformal (mesh-conforming) glue surfaces are **not** in the MVP — glue-on parts use a
  flat contact face. Tracked as a TODO in `docs/GEOMETRY_PIPELINE.md`.
- STEP import is deferred (requires Blender/FreeCAD); it does not block the MVP.

[Unreleased]: https://github.com/starlordz12/LocalMeshAI/commits/main
