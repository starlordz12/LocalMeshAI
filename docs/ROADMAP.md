# Roadmap

LocalMeshAI is built in milestones. Each milestone is independently useful; nothing later
blocks the core viewer/editor loop.

Legend: ✅ done · 🟡 partial · ⬜ planned

## Milestone 1 — Local STL viewer ✅

- [x] React + Vite + TypeScript app
- [x] three.js viewport (orbit / pan / zoom)
- [x] Import STL/OBJ/PLY/3MF → render
- [x] Grid build plate, axes gizmo, bounding box
- [x] mm dimensions readout
- [x] Rotate / orient model (90° steps + free rotation, lay-flat, center-on-bed)
- [x] Object/operation tree
- [x] Inspector panel
- [x] Save / load project JSON

## Milestone 2 — Helper primitives ✅

- [x] Box & cylinder helpers
- [x] Transform helpers in the viewport (gizmo)
- [x] Additive / subtractive / glue-on mode toggle
- [x] Export helper as its own STL
- [x] Helpers stored in the operation tree
- [x] Extended helper library (screw boss, mounting tab/pad, rib, cable guide, fairing,
      cutouts, channels, vents, pockets)

## Milestone 3 — Blender boolean backend ✅

- [x] Backend receives the operation tree
- [x] Blender headless script performs union/difference
- [x] trimesh + manifold3d fallback so booleans work with no Blender
- [x] Export final STL
- [x] Return logs + validation info
- [x] Surface errors in the GUI
- [ ] Conformal (mesh-conforming) glue surfaces ⬜ *(flat contact face for now)*

## Milestone 4 — Pencil annotations ✅

- [x] Drawing overlay over the model
- [x] Strokes attached to the scene/camera; raycast onto the mesh when possible
- [x] Store annotations in the tree
- [x] Assign stroke intent (add / cut / glue-on / drill / channel / tab / boss / vent / ...)
- [x] Text notes per stroke
- [x] Convert annotation → editable helper operation
- [ ] Multi-stroke region fitting (fit a plane/box to a closed loop) 🟡

## Milestone 5 — Rule-based AI planner ✅

- [x] `LocalRuleBasedPlanner` parses common phrases into structured plans
- [x] User reviews the plan before anything is created
- [x] "Create Helper Features From Plan" turns a plan into operations
- [x] Adapter interface: Ollama / Anthropic / OpenAI placeholders (no key required)
- [ ] Wire a real local LLM (Ollama) end-to-end ⬜

## Milestone 6 — Desktop packaging ⬜

- [ ] One-command dev startup (✅ via `start-dev.ps1`)
- [ ] Package as a desktop app (Tauri preferred; Electron fallback)
- [ ] Bundle/locate Blender automatically
- [ ] Auto-update channel

## Milestone 7 — Optional SaaS / hybrid architecture ⬜

- [ ] Containerize the backend geometry service
- [ ] Move booleans to a job queue (large meshes)
- [ ] Optional cloud project storage with local-file fallback
- [ ] Multi-user sharing / collaboration
- [ ] Keep a fully local mode for private workflows

## Cross-cutting backlog

- [ ] STEP/IGES import via Blender or FreeCAD
- [ ] Automatic orientation optimizer (minimize supports)
- [ ] Per-helper fillet/chamfer in the fallback engine (Blender bevel today)
- [ ] Slicer hand-off (export + open in PrusaSlicer/Orca)
