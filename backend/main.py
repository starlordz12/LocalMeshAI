"""LocalMeshAI backend — FastAPI application.

Local-first geometry + AI-planner service. The frontend is the source of truth for the
in-memory project; geometry/operation endpoints accept the full project, persist it, and run
the requested geometry. The original imported mesh is always preserved; only exports bake
geometry.

Run:  uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import mimetypes

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import config
from models import (
    AddHelperRequest,
    AnalyzeRequest,
    AnalyzeResponse,
    ApplyBooleanRequest,
    BooleanResponse,
    DeleteOperationRequest,
    EngineStatus,
    ExportRequest,
    ExportResponse,
    HealthResponse,
    ImportResponse,
    MeshInfo,
    NewProjectRequest,
    OperationResponse,
    PlanRequest,
    PlanResponse,
    Project,
    ProjectResponse,
    RepairRequest,
    RepairResponse,
    UpdateHelperRequest,
)
from services import ai_planner, geometry_engine, helpers, mesh_analyzer, project_store

VERSION = "0.1.0"

app = FastAPI(title="LocalMeshAI", version=VERSION, description="Local-first 3D-print editor backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- helpers ---------------------------------------------------------------------------


def _engine_status() -> EngineStatus:
    return EngineStatus(
        boolean_engine=geometry_engine.selected_engine(),
        blender_available=config.blender_available(),
        manifold_available=config.manifold_available(),
        blender_path=config.find_blender(),
    )


def _persist(project: Project) -> Project:
    """Write the client's project to disk (single write path) and return it."""
    if not project_store.project_exists(project.id):
        # Recreate the workspace dirs if the client has a project the server hasn't seen.
        project_store.project_dir(project.id).mkdir(parents=True, exist_ok=True)
    project_store.save_project(project)
    return project


def _load_source_mesh(project_id: str, mesh_id: str):
    project = project_store.load_project(project_id)
    info = project_store.get_mesh(project, mesh_id)
    path = project_store.resolve_relative(project_id, info.source_file)
    return project, info, mesh_analyzer.load_mesh(path)


# --- health / catalog ------------------------------------------------------------------


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=VERSION, engine=_engine_status())


@app.get("/api/features")
def features() -> dict:
    """Helper-feature catalog + printability defaults, so the UI stays in sync with the
    backend's actual capabilities."""
    return {"catalog": helpers.FEATURE_CATALOG, "defaults": config.DEFAULTS}


@app.get("/api/projects")
def list_projects() -> dict:
    return {"projects": project_store.list_projects()}


# --- project lifecycle -----------------------------------------------------------------


@app.post("/api/project/new", response_model=ProjectResponse)
def new_project(req: NewProjectRequest) -> ProjectResponse:
    project = project_store.create_project(req.name)
    return ProjectResponse(project=project)


@app.get("/api/project/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    try:
        return ProjectResponse(project=project_store.load_project(project_id))
    except project_store.ProjectNotFoundError:
        raise HTTPException(404, f"Project not found: {project_id}")


@app.post("/api/project/{project_id}/save", response_model=ProjectResponse)
def save_project(project_id: str, project: Project) -> ProjectResponse:
    if project.id != project_id:
        raise HTTPException(400, "Project id in path and body do not match.")
    return ProjectResponse(project=_persist(project))


# --- file serving (display GLBs, exported STLs, sources) -------------------------------


@app.get("/api/project/{project_id}/file/{path:path}")
def get_file(project_id: str, path: str):
    try:
        abs_path = project_store.resolve_relative(project_id, path)
    except ValueError:
        raise HTTPException(400, "Invalid path.")
    if not abs_path.exists() or not abs_path.is_file():
        raise HTTPException(404, "File not found.")
    media = mimetypes.guess_type(str(abs_path))[0]
    if abs_path.suffix.lower() == ".glb":
        media = "model/gltf-binary"
    elif abs_path.suffix.lower() == ".stl":
        media = "model/stl"
    return FileResponse(abs_path, media_type=media or "application/octet-stream",
                        filename=abs_path.name)


# --- import ----------------------------------------------------------------------------


@app.post("/api/import", response_model=ImportResponse)
async def import_mesh(
    project_id: str = Form(..., alias="projectId"),
    file: UploadFile = File(...),
) -> ImportResponse:
    if not project_store.project_exists(project_id):
        raise HTTPException(404, f"Project not found: {project_id}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Uploaded file is empty.")
    try:
        mesh_id, abs_path, ext = project_store.save_source_mesh(project_id, data, file.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    try:
        mesh = mesh_analyzer.load_mesh(abs_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"Could not read mesh: {exc}")

    analysis = mesh_analyzer.analyze(mesh)
    analysis.warnings += mesh_analyzer.thin_feature_warnings(mesh)

    glb_rel = f"_derived/{mesh_id}.glb"
    try:
        mesh_analyzer.export_display_glb(mesh, project_store.resolve_relative(project_id, glb_rel))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Could not build display mesh: {exc}")

    source_rel = str(abs_path.relative_to(project_store.project_dir(project_id))).replace("\\", "/")
    mesh_info = MeshInfo(
        id=mesh_id,
        name=file.filename,
        source_file=source_rel,
        display_glb=glb_rel,
        format=ext,
        analysis=analysis,
    )

    project = project_store.load_project(project_id)
    project_store.add_mesh(project, mesh_info)
    project_store.save_project(project)
    return ImportResponse(project=project, mesh=mesh_info)


# --- analysis / repair -----------------------------------------------------------------


@app.post("/api/mesh/analyze", response_model=AnalyzeResponse)
def analyze_mesh(req: AnalyzeRequest) -> AnalyzeResponse:
    try:
        _project, _info, mesh = _load_source_mesh(req.project_id, req.mesh_id)
    except project_store.ProjectNotFoundError:
        raise HTTPException(404, f"Project not found: {req.project_id}")
    except project_store.MeshNotFoundError:
        raise HTTPException(404, f"Mesh not found: {req.mesh_id}")
    analysis = mesh_analyzer.analyze(mesh)
    analysis.warnings += mesh_analyzer.thin_feature_warnings(mesh)
    return AnalyzeResponse(mesh_id=req.mesh_id, analysis=analysis)


@app.post("/api/mesh/repair", response_model=RepairResponse)
def repair_mesh(req: RepairRequest) -> RepairResponse:
    try:
        project, info, mesh = _load_source_mesh(req.project_id, req.mesh_id)
    except project_store.ProjectNotFoundError:
        raise HTTPException(404, f"Project not found: {req.project_id}")
    except project_store.MeshNotFoundError:
        raise HTTPException(404, f"Mesh not found: {req.mesh_id}")

    before = mesh_analyzer.analyze(mesh)
    repaired, actions = mesh_analyzer.repair(mesh)
    after = mesh_analyzer.analyze(repaired)

    # Write the repaired mesh back as a NEW source file (never overwrite the original).
    repaired_rel = f"sources/{req.mesh_id}__repaired.stl"
    repaired.export(project_store.resolve_relative(req.project_id, repaired_rel))
    info.source_file = repaired_rel
    info.analysis = after
    # Rebuild the display GLB.
    mesh_analyzer.export_display_glb(
        repaired, project_store.resolve_relative(req.project_id, info.display_glb or f"_derived/{req.mesh_id}.glb")
    )
    project_store.save_project(project)

    success = after.is_watertight or not before.is_watertight and after.triangle_count > 0
    message = (
        "Repair complete; mesh is watertight." if after.is_watertight
        else "Repair ran, but the mesh is still not watertight. Manual cleanup may be needed."
    )
    return RepairResponse(
        mesh_id=req.mesh_id, before=before, after=after, actions=actions,
        success=after.is_watertight, message=message,
    )


# --- operations ------------------------------------------------------------------------


@app.post("/api/operation/add-helper", response_model=OperationResponse)
def add_helper(req: AddHelperRequest) -> OperationResponse:
    project = req.project
    project_store.upsert_operation(project, req.operation)
    _persist(project)
    return OperationResponse(project=project, operation=req.operation)


@app.post("/api/operation/update-helper", response_model=OperationResponse)
def update_helper(req: UpdateHelperRequest) -> OperationResponse:
    project = req.project
    if project_store.get_operation(project, req.operation.id) is None:
        raise HTTPException(404, f"Operation not found: {req.operation.id}")
    project_store.upsert_operation(project, req.operation)
    _persist(project)
    return OperationResponse(project=project, operation=req.operation)


@app.post("/api/operation/delete", response_model=OperationResponse)
def delete_operation(req: DeleteOperationRequest) -> OperationResponse:
    project = req.project
    op = project_store.get_operation(project, req.operation_id)
    if op is None:
        raise HTTPException(404, f"Operation not found: {req.operation_id}")
    if req.suppress:
        op.suppressed = True
        project_store.upsert_operation(project, op)
        result_op = op
    else:
        project_store.remove_operation(project, req.operation_id)
        result_op = None
    _persist(project)
    return OperationResponse(project=project, operation=result_op)


# --- boolean apply ---------------------------------------------------------------------


@app.post("/api/operation/apply-boolean", response_model=BooleanResponse)
def apply_boolean(req: ApplyBooleanRequest) -> BooleanResponse:
    project = _persist(req.project)
    try:
        result, engine, log, before, after = geometry_engine.apply_tree(
            project, req.mesh_id, req.operation_ids
        )
    except geometry_engine.GeometryError as exc:
        return BooleanResponse(success=False, engine=geometry_engine.selected_engine(),
                               message=str(exc), log=[])
    except project_store.MeshNotFoundError:
        raise HTTPException(404, f"Mesh not found: {req.mesh_id}")
    except Exception as exc:  # noqa: BLE001 - surface engine failure to the UI
        return BooleanResponse(success=False, engine=geometry_engine.selected_engine(),
                               message=f"Boolean failed: {exc}", log=[])

    # Persist the baked result so the viewer can preview it.
    preview_rel = f"_derived/preview_{req.mesh_id}.stl"
    try:
        result.export(project_store.resolve_relative(project.id, preview_rel))
    except Exception:
        preview_rel = None

    return BooleanResponse(
        success=True, engine=engine,
        message=f"Applied helpers via {engine}.",
        log=log, before=before, after=after, output_file=preview_rel,
    )


# --- export ----------------------------------------------------------------------------


@app.post("/api/export/final-stl", response_model=ExportResponse)
def export_final(req: ExportRequest) -> ExportResponse:
    project = _persist(req.project)
    mesh_id = req.mesh_id or (project.meshes[0].id if project.meshes else None)
    if not mesh_id:
        raise HTTPException(400, "No mesh to export. Import a model first.")
    try:
        rel, validation, engine, log = geometry_engine.export_final(project, mesh_id, req.format)
    except geometry_engine.GeometryError as exc:
        return ExportResponse(success=False, message=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ExportResponse(success=False, message=f"Export failed: {exc}")
    return ExportResponse(
        success=True, file=str(rel).replace("\\", "/"),
        message=f"Exported final {req.format.upper()} via {engine}.",
        validation=validation, log=log,
    )


@app.post("/api/export/helper-stl", response_model=ExportResponse)
def export_helper(req: ExportRequest) -> ExportResponse:
    project = _persist(req.project)
    if not req.operation_id:
        raise HTTPException(400, "operationId is required for helper export.")
    try:
        rel, validation, log = geometry_engine.export_helper(project, req.operation_id, req.format)
    except geometry_engine.GeometryError as exc:
        return ExportResponse(success=False, message=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ExportResponse(success=False, message=f"Export failed: {exc}")
    return ExportResponse(
        success=True, file=str(rel).replace("\\", "/"),
        message=f"Exported helper {req.format.upper()}.",
        validation=validation, log=log,
    )


# --- AI planner ------------------------------------------------------------------------


@app.post("/api/ai/plan", response_model=PlanResponse)
def ai_plan(req: PlanRequest) -> PlanResponse:
    project = None
    if req.project_id and project_store.project_exists(req.project_id):
        try:
            project = project_store.load_project(req.project_id)
        except Exception:
            project = None
    return ai_planner.plan(req, project)


@app.get("/")
def root() -> dict:
    return {"name": "LocalMeshAI", "version": VERSION, "docs": "/docs", "health": "/api/health"}
