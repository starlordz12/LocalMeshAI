# Architecture

LocalMeshAI is a **local-first web app**: a Python geometry/AI backend plus a browser
frontend, both running on your machine. This document explains the moving parts and the
deliberate seams that let the backend, geometry engine, and AI planner move to a hosted
service later without rewriting the UI.

## High-level diagram

```
+----------------------------------------------------------+
|                        Browser (UI)                       |
|  React + Vite + TypeScript                                |
|  three.js / @react-three/fiber / @react-three/drei        |
|                                                           |
|  Toolbar | ObjectTree | Viewer3D | Inspector | AIPanel    |
|                       StatusConsole                        |
|                                                           |
|  - Renders imported mesh (display GLB)                     |
|  - Renders parametric helper PREVIEWS locally (three.js)   |
|  - Holds the operation tree in a zustand store            |
+----------------------------+-----------------------------+
                             | HTTP (JSON + multipart)
                             v
+----------------------------------------------------------+
|                   Backend (FastAPI)                       |
|                                                           |
|  models.py        Pydantic request/response schemas       |
|  services/                                                |
|    project_store     workspace + project.json persistence |
|    mesh_analyzer     bbox / volume / area / manifold      |
|    helpers           parametric helper -> trimesh meshes  |
|    geometry_engine   dispatcher (Blender | trimesh)       |
|    blender_engine    headless Blender boolean backend     |
|    trimesh_engine    trimesh + manifold3d boolean backend |
|    ai_planner        rule-based + LLM adapter interface    |
+----------------------------+-----------------------------+
                             |
              +--------------+--------------+
              v                             v
   +--------------------+        +-----------------------+
   |  Blender (headless)|        |  trimesh + manifold3d |
   |  robust booleans   |        |  pure-Python fallback |
   +--------------------+        +-----------------------+
```

## Why local-first (and how we keep SaaS open)

See the recommendation summary in the project README. In short: local-first wins for this
app today because of **direct STL/file access, local GPU rendering, Blender on the same
box, and private project files**. The architecture keeps SaaS reachable by enforcing three
seams:

1. **The frontend only talks to the backend over HTTP/JSON.** No geometry library is
   imported into the UI for *authoritative* operations — three.js is used only for display
   and live previews. Swap `http://localhost:8000` for a remote URL and the UI is unchanged.
2. **The geometry engine is a dispatcher behind an interface** (`GeometryEngine`). Blender,
   trimesh/manifold3d today; a containerized geometry microservice tomorrow.
3. **The AI planner is an adapter** (`Planner`). `LocalRuleBasedPlanner` ships now;
   `OllamaPlanner`, `AnthropicPlanner`, `OpenAIPlanner` are drop-in.

## Data model

A **Project** is a folder under `projects/<project_id>/` containing:

```
project.json        operation tree + metadata (source of truth)
sources/            original imported meshes (never modified)
_derived/           display GLBs and exported STLs (regenerable)
```

`project.json` holds the operation tree. Each operation is a non-destructive record:

```jsonc
{
  "id": "op_001",
  "type": "helper_feature",
  "name": "Camera Mounting Pad",
  "mode": "additive | subtractive | glue_on",
  "feature": "box | cylinder | mounting_tab | screw_boss | cable_channel | fairing | ...",
  "targetMeshId": "mesh_001",
  "positionMm": [0, 0, 0],
  "rotationDeg": [0, 0, 0],
  "scaleMm": [20, 10, 3],
  "parameters": { "holeDiameterMm": 3.2, "filletRadiusMm": 1.0 },
  "sourceAnnotationId": "ann_001",
  "suppressed": false,
  "exportSeparate": false
}
```

The original mesh import is itself recorded as a `mesh_import` operation, so the tree fully
describes how to rebuild any export from the sources.

## Request flow: importing a mesh

1. UI `POST /api/import` (multipart) → backend copies the file to `sources/`.
2. Backend loads it with trimesh, runs `mesh_analyzer`, and exports a **display GLB** to
   `_derived/`.
3. Response returns mesh id, analysis, and the GLB URL.
4. UI loads the GLB with `useGLTF` and renders it. One viewer path for every input format.

## Request flow: applying a boolean

1. UI sends the operation tree to `POST /api/export/final-stl` (or `apply-boolean`).
2. Backend rebuilds each helper mesh from its parameters (`helpers.py`).
3. `geometry_engine` picks a backend (Blender if available, else trimesh/manifold3d) and
   performs union/difference in order.
4. A final validation pass checks watertightness and reports triangle/bbox deltas.
5. Backend writes the STL to `_derived/` and returns the path + logs + validation.

## Technology choices

| Concern | Choice | Reason |
|---|---|---|
| UI framework | React + Vite + TS | Fast HMR, typed, huge ecosystem |
| 3D rendering | three.js + r3f + drei | Declarative scene, GPU via WebGL |
| Backend | FastAPI + Pydantic | Typed schemas, async, OpenAPI for free |
| Mesh analysis | trimesh | Mature, watertight/volume/area built in |
| Booleans (robust) | Blender headless | Industry-grade boolean modifier |
| Booleans (fallback) | manifold3d via trimesh | Works with no Blender; watertight |
| State | zustand | Minimal, no boilerplate, easy to test |

## Failure handling philosophy

- Booleans that fail return the engine log and a human-readable reason; the UI surfaces it
  in the status console and **does not** mutate the operation tree.
- Non-manifold imports are flagged, not silently "repaired". Repair is an explicit action.
- Exports always run a final validation pass and report it.
