"""Pydantic request/response and domain schemas for LocalMeshAI.

JSON is camelCase (matching the TypeScript frontend and the operation-tree spec);
Python attributes stay snake_case via an alias generator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# --- Shared base -----------------------------------------------------------------------


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase on the wire."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        protected_namespaces=(),
    )


Vec3 = tuple[float, float, float]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Enums (as Literals for clean OpenAPI) ---------------------------------------------

HelperMode = Literal["additive", "subtractive", "glue_on"]

FeatureType = Literal[
    # additive
    "box",
    "cylinder",
    "screw_boss",
    "mounting_tab",
    "mounting_pad",
    "rib_gusset",
    "cable_guide",
    "fairing",
    "mounting_deck",
    "glue_plate",
    # subtractive
    "box_cutout",
    "cylinder_hole",
    "rectangular_slot",
    "cable_channel",
    "vent_slot",
    "screw_clearance_hole",
    "pocket",
    # escape hatch
    "custom",
]

AnnotationIntent = Literal[
    "add_material",
    "cut_material",
    "glue_on",
    "drill_hole",
    "cable_channel",
    "mounting_tab",
    "screw_boss",
    "vent_cutout",
    "fairing",
    "flat_pad",
    "note",
]

OperationType = Literal["mesh_import", "helper_feature", "annotation"]


# --- Mesh analysis ---------------------------------------------------------------------


class BoundingBox(CamelModel):
    min: Vec3
    max: Vec3
    size: Vec3  # per-axis extent in mm


class MeshAnalysis(CamelModel):
    triangle_count: int
    vertex_count: int
    bounding_box: BoundingBox
    surface_area_mm2: float
    volume_mm3: Optional[float] = None  # None when not watertight (meaningless otherwise)
    is_watertight: bool
    is_winding_consistent: bool
    has_inverted_normals: bool
    warnings: list[str] = Field(default_factory=list)


class MeshInfo(CamelModel):
    """A single imported source mesh inside a project."""

    id: str
    name: str  # original file name
    source_file: str  # relative path under the project workspace
    display_glb: Optional[str] = None  # relative path to the viewer GLB
    format: str  # stl/obj/ply/3mf
    analysis: Optional[MeshAnalysis] = None
    # Orientation transform applied identically by the viewer and by export, so rotating /
    # laying-flat the model stays consistent with helper placement and the baked result.
    position_mm: Vec3 = (0.0, 0.0, 0.0)
    rotation_deg: Vec3 = (0.0, 0.0, 0.0)


# --- Operation tree --------------------------------------------------------------------


class Operation(CamelModel):
    """A non-destructive edit record. Helper features and imports both live here."""

    id: str
    type: OperationType = "helper_feature"
    name: str
    mode: HelperMode = "additive"
    feature: FeatureType = "box"
    target_mesh_id: Optional[str] = None
    position_mm: Vec3 = (0.0, 0.0, 0.0)
    rotation_deg: Vec3 = (0.0, 0.0, 0.0)
    scale_mm: Vec3 = (20.0, 10.0, 3.0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    source_annotation_id: Optional[str] = None
    suppressed: bool = False
    export_separate: bool = False


class Annotation(CamelModel):
    """A pencil stroke capturing user intent over the model."""

    id: str
    intent: AnnotationIntent = "note"
    note: str = ""
    # 2D normalized screen points (0..1) of the stroke, for redraw.
    screen_points: list[tuple[float, float]] = Field(default_factory=list)
    # Optional 3D anchor (raycast hit on the mesh) in mm, if available.
    world_anchor_mm: Optional[Vec3] = None
    world_normal: Optional[Vec3] = None
    target_mesh_id: Optional[str] = None
    converted_operation_id: Optional[str] = None


# --- Project ---------------------------------------------------------------------------


class ProjectSettings(CamelModel):
    units: str = "mm"
    min_wall_mm: float = 0.8
    pilot_hole_mm: float = 2.2
    m3_clearance_mm: float = 3.2
    default_fillet_mm: float = 0.8
    default_helper_thickness_mm: float = 2.5


class Project(CamelModel):
    id: str
    name: str
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    schema_version: int = 1
    meshes: list[MeshInfo] = Field(default_factory=list)
    operations: list[Operation] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


# --- API request / response models -----------------------------------------------------


class NewProjectRequest(CamelModel):
    name: str = "Untitled Project"


class ProjectResponse(CamelModel):
    project: Project


class ImportResponse(CamelModel):
    project: Project
    mesh: MeshInfo


class AnalyzeRequest(CamelModel):
    project_id: str
    mesh_id: str


class AnalyzeResponse(CamelModel):
    mesh_id: str
    analysis: MeshAnalysis


class RepairRequest(CamelModel):
    project_id: str
    mesh_id: str


class RepairResponse(CamelModel):
    mesh_id: str
    before: MeshAnalysis
    after: MeshAnalysis
    actions: list[str]
    success: bool
    message: str


# Operation/geometry endpoints carry the full Project so the frontend stays the single
# source of truth (client-only state like annotations/orientation is never lost to a stale
# disk read). analyze/repair operate on already-persisted source files, so they take ids.


class AddHelperRequest(CamelModel):
    project: Project
    operation: Operation


class UpdateHelperRequest(CamelModel):
    project: Project
    operation: Operation


class DeleteOperationRequest(CamelModel):
    project: Project
    operation_id: str
    # If true, soft-suppress instead of deleting.
    suppress: bool = False


class OperationResponse(CamelModel):
    project: Project
    operation: Optional[Operation] = None


class ApplyBooleanRequest(CamelModel):
    project: Project
    mesh_id: str
    # If empty, apply all non-suppressed additive/subtractive helpers targeting this mesh.
    operation_ids: Optional[list[str]] = None


class ValidationReport(CamelModel):
    is_watertight: bool
    is_winding_consistent: bool
    volume_mm3: Optional[float] = None
    triangle_count: int
    bounding_box: BoundingBox
    warnings: list[str] = Field(default_factory=list)


class BooleanResponse(CamelModel):
    success: bool
    engine: str
    message: str
    log: list[str] = Field(default_factory=list)
    before: Optional[ValidationReport] = None
    after: Optional[ValidationReport] = None
    output_file: Optional[str] = None  # relative path under the project workspace


class ExportRequest(CamelModel):
    project: Project
    mesh_id: Optional[str] = None
    operation_id: Optional[str] = None  # for helper-stl export
    format: Literal["stl", "obj", "3mf"] = "stl"


class ExportResponse(CamelModel):
    success: bool
    file: Optional[str] = None  # relative path under project workspace
    message: str
    validation: Optional[ValidationReport] = None
    log: list[str] = Field(default_factory=list)


# --- AI planner ------------------------------------------------------------------------


class PlanRequest(CamelModel):
    project_id: Optional[str] = None
    prompt: str
    mesh_id: Optional[str] = None
    annotation_id: Optional[str] = None
    planner: Literal["rule_based", "ollama", "anthropic", "openai"] = "rule_based"


class PlannedFeature(CamelModel):
    """A single proposed, editable operation (not yet applied)."""

    name: str
    mode: HelperMode
    feature: FeatureType
    position_mm: Vec3 = (0.0, 0.0, 0.0)
    rotation_deg: Vec3 = (0.0, 0.0, 0.0)
    scale_mm: Vec3 = (20.0, 10.0, 3.0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class PlanResponse(CamelModel):
    planner: str
    summary: str
    features: list[PlannedFeature] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    needs_review: bool = True


class EngineStatus(CamelModel):
    boolean_engine: str
    blender_available: bool
    manifold_available: bool
    blender_path: Optional[str] = None


class HealthResponse(CamelModel):
    status: str
    version: str
    engine: EngineStatus
