# Contributing to LocalMeshAI

Thanks for your interest in improving LocalMeshAI! This project is a **local-first,
AI-assisted editor for 3D-printable parts**. It is designed to grow incrementally, so
contributions of all sizes are welcome.

## Ground rules

- **Non-destructive by default.** Operations are stored in a JSON operation tree. The
  user's original imported mesh is never modified in place — only exports bake geometry.
- **Millimeters everywhere.** All geometry, parameters, and UI values are in mm.
- **Keep the original file untouched.** Importers copy the source into the project
  workspace; exporters write new files.
- **Fail loudly, not silently.** Geometry operations must return readable, actionable
  errors rather than producing corrupt meshes.

## Project layout

```
backend/    FastAPI server, geometry engines, AI planner
frontend/   React + Vite + TypeScript + three.js viewer
docs/       Architecture, geometry pipeline, workflow, roadmap
test_assets/ Small meshes used by tests and manual QA
examples/   Worked example projects
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Development setup

### Backend (Python 3.10+)

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

### Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev
```

Then open the Vite URL (default <http://localhost:5173>).

### One-command dev (Windows)

From the repo root:

```powershell
./start-dev.ps1
```

## Before opening a pull request

1. **Backend:** `cd backend && python -m pytest` (geometry + API smoke tests).
2. **Frontend:** `cd frontend && npm run build` (type-checks via `tsc` and bundles).
3. Keep commits focused; describe *why*, not just *what*.
4. Update the relevant docs and `CHANGELOG.md`.
5. Do not commit anything under `projects/` — that is user working data.

## Commit style

Conventional, readable subject lines are appreciated:

```
feat(geometry): add cable-channel subtractive helper
fix(viewer): correct mm dimension readout for rotated meshes
docs(roadmap): mark Milestone 2 complete
```

## Licensing of contributions

- **Code** you contribute is licensed under the **MIT License**.
- **Assets** (models, images, diagrams, docs graphics) are licensed under **CC BY 4.0**
  unless you note otherwise in the file.

By submitting a contribution you agree to license it under these terms. See
[LICENSE](LICENSE) and [LICENSE-ASSETS.md](LICENSE-ASSETS.md).

## Reporting issues

Use the GitHub issue templates:

- Bug report
- Feature request
- Geometry operation failure
- Supported file format request
- UI/UX improvement
