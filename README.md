# LocalMeshAI

**A local-first, AI-assisted editor for 3D-printable parts.**

Import a model, view and orient it, mark up what you want changed, and generate
**editable parametric helper features** — mounting pads, screw bosses, cable channels,
cutouts, glue-on parts — then export clean STLs. Your original file is never modified.

> LocalMeshAI does **not** pretend freehand sketch → perfect CAD is a solved problem.
> Instead it is built around a reliable **operation-tree** workflow: annotations capture
> *intent*, and real geometry comes from parametric helpers and boolean operations.

---

## Screenshot

> _Screenshot placeholder — drop a viewport capture here once the UI is running._
>
> `docs/images/screenshot.png`

---

## Core features

- **3D viewer** — orbit / pan / zoom, grid build plate, axes gizmo, bounding box, live
  dimensions in **millimeters**, model origin and build-plate plane.
- **Orientation tools** — rotate X/Y/Z by 90°, free rotation, lay-flat attempt,
  center-on-bed, move-to-build-plate.
- **Object / operation tree** — original mesh, helper features, cutouts, glue-on parts,
  each with visibility, select, and suppress/delete.
- **Inspector** — mesh stats (bbox, volume, area, triangle count, watertight status) and
  per-helper parameters, all editable after creation.
- **Parametric helpers** — additive (box, cylinder, screw boss, mounting tab/pad, rib,
  cable guide, fairing, mounting deck, glue plate) and subtractive (box cutout, hole, slot,
  cable channel, vent, screw clearance, pocket).
- **Glue-on workflow** — make any helper a boolean union **or** a separate exportable
  glue-on STL (or preview both).
- **Pencil / annotation mode** — draw intent on the model, tag it (add / cut / drill /
  channel / tab / boss / vent / fairing / note…), then convert to an editable helper.
- **AI planner** — describe a change in plain English; a **rule-based** planner turns it
  into a structured, reviewable plan, then into helper operations. Works with **no API key**.
- **Boolean engine** — robust **Blender** headless backend when available, with a
  **trimesh + manifold3d** fallback so booleans still work with no Blender installed.
- **Non-destructive** — everything is a JSON operation tree; exports bake geometry, the
  source file stays untouched.

## What works now (MVP)

- Import **STL / OBJ / PLY / 3MF**, normalized to a display GLB for one clean viewer path.
- Mesh analysis + conservative repair (with before/after stats).
- Add, transform, and edit helper primitives; full helper library above.
- Boolean union & difference (Blender **or** trimesh/manifold3d).
- Export **final STL** (booleans baked) and **per-helper STL** (glue-on pieces).
- Save / load **project JSON** (operation tree).
- Pencil annotations → helper conversion.
- Rule-based AI edit planner with reviewable plans.

## What is planned

- Conformal (mesh-conforming) glue surfaces — flat contact face for now.
- STEP/IGES import via Blender/FreeCAD.
- Real local-LLM planner (Ollama) wired end-to-end.
- Desktop packaging (Tauri) and optional SaaS/hybrid backend.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full milestone plan.

---

## Install

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** and npm
- **Blender 3.x/4.x** — *optional but recommended* for robust booleans. Without it,
  LocalMeshAI uses the built-in trimesh/manifold3d engine.

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API serves at <http://localhost:8000> (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL it prints (default <http://localhost:5173>).

### One-command dev (Windows)

From the repo root:

```powershell
./start-dev.ps1
```

This launches the backend (uvicorn) and the frontend (Vite) together.

---

## Development setup

- Backend tests: `cd backend && python -m pytest`
- Frontend type-check + build: `cd frontend && npm run build`
- API base URL is read from `frontend/.env` (`VITE_API_BASE`, default
  `http://localhost:8000`). No absolute paths are hardcoded.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Blender dependency notes

- LocalMeshAI auto-detects Blender by checking, in order: the `LOCALMESHAI_BLENDER`
  environment variable, a `blender` on your `PATH`, and common install locations
  (`C:\Program Files\Blender Foundation\...` on Windows).
- If found, booleans run through a **headless Blender** script using the boolean modifier
  with the MANIFOLD solver (best for thin-wall and tangent-cut geometry).
- If not found, the **trimesh + manifold3d** engine handles booleans. It is watertight and
  needs no external app; it is just slower on very large meshes.
- Set a custom path: `setx LOCALMESHAI_BLENDER "C:\Path\to\blender.exe"` (Windows) or
  export it in your shell.
- An optional Blender **MCP** server on port `9876` can be used for interactive Blender
  work; the headless path above is the default and needs no MCP.

## Supported file formats

| Format | Import | Export | Notes |
|---|---|---|---|
| STL | ✅ | ✅ | Primary format |
| OBJ | ✅ | ✅ (optional) | |
| 3MF | ✅ | ✅ (optional) | |
| PLY | ✅ | — | Import for viewing/analysis |
| STEP/IGES | ⬜ | — | Deferred (Blender/FreeCAD), does not block MVP |
| Project `.json` | ✅ | ✅ | Operation tree (required) |

## Safety / geometry limitations

- No freehand sculpting — annotations capture intent; geometry comes from parametric
  helpers (deliberate; see above).
- Glue-on contact is a **flat face** in the MVP; conformal surfaces are planned.
- Non-manifold imports are **flagged, not silently repaired**. Repair is explicit and
  conservative (it never deletes large regions).
- Booleans can fail on degenerate/open inputs; failures return a readable reason and the
  operation tree is left unchanged.
- Exports run a final validation pass (watertight / winding / volume / bbox delta).
- Printability defaults: mm units, 0.8 mm min-wall warning, 2.2 mm pilot / 3.2 mm M3
  clearance, 0.5–1.0 mm default fillet, 2–3 mm default helper thickness.

## Example workflows

Full step-by-step in [docs/USER_WORKFLOW.md](docs/USER_WORKFLOW.md):

1. **Glue-on mounting pad** with screw holes → export as a separate STL or union + export.
2. **Annotated cooling vent** → pencil-circle an area → rectangular cutout → boolean
   difference → export.
3. **AI-planned camera mounting deck** → prompt → reviewable plan → helper features →
   export as glue-on or merged.

## Roadmap

Milestones 1–5 (viewer, helpers, boolean backend, annotations, rule-based AI) are
implemented in the MVP. Milestones 6–7 (desktop packaging, optional SaaS/hybrid) are
planned. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Architecture & local-first rationale

LocalMeshAI is **local-first** because this app benefits most from direct local STL access,
local GPU rendering, Blender on the same machine, and private project files. The
architecture keeps a hosted SaaS/hybrid future open by isolating three seams: the UI only
talks HTTP/JSON to the backend, the geometry engine sits behind a dispatcher interface, and
the AI planner is a swappable adapter. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## License

Code in this repository is licensed under the **MIT License**. See the [LICENSE](LICENSE)
file for details.

3D models, CAD files, images, documentation, screenshots, diagrams, and other design assets
are licensed under **CC BY 4.0** unless otherwise noted.

This means people can use and build from LocalMeshAI, but **attribution is still required
for the design assets**. See [LICENSE-ASSETS.md](LICENSE-ASSETS.md) and
[docs/LICENSING.md](docs/LICENSING.md) for the full explanation of why code and assets are
licensed differently.
