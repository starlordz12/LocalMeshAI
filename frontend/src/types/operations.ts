// Operation-tree and helper-feature types. These mirror the backend Pydantic models
// (camelCase wire format).

export type Vec3 = [number, number, number];

export type HelperMode = "additive" | "subtractive" | "glue_on";

export type FeatureType =
  // additive
  | "box"
  | "cylinder"
  | "screw_boss"
  | "mounting_tab"
  | "mounting_pad"
  | "rib_gusset"
  | "cable_guide"
  | "fairing"
  | "mounting_deck"
  | "glue_plate"
  // subtractive
  | "box_cutout"
  | "cylinder_hole"
  | "rectangular_slot"
  | "cable_channel"
  | "vent_slot"
  | "screw_clearance_hole"
  | "pocket"
  // escape hatch
  | "custom";

export type OperationType = "mesh_import" | "helper_feature" | "annotation";

export type AnnotationIntent =
  | "add_material"
  | "cut_material"
  | "glue_on"
  | "drill_hole"
  | "cable_channel"
  | "mounting_tab"
  | "screw_boss"
  | "vent_cutout"
  | "fairing"
  | "flat_pad"
  | "note";

export interface Operation {
  id: string;
  type: OperationType;
  name: string;
  mode: HelperMode;
  feature: FeatureType;
  targetMeshId?: string | null;
  positionMm: Vec3;
  rotationDeg: Vec3;
  scaleMm: Vec3;
  parameters: Record<string, number | string | boolean>;
  sourceAnnotationId?: string | null;
  suppressed: boolean;
  exportSeparate: boolean;
}

export interface Annotation {
  id: string;
  intent: AnnotationIntent;
  note: string;
  screenPoints: [number, number][];
  worldAnchorMm?: Vec3 | null;
  worldNormal?: Vec3 | null;
  targetMeshId?: string | null;
  convertedOperationId?: string | null;
}

export interface PlannedFeature {
  name: string;
  mode: HelperMode;
  feature: FeatureType;
  positionMm: Vec3;
  rotationDeg: Vec3;
  scaleMm: Vec3;
  parameters: Record<string, number | string | boolean>;
  rationale: string;
}

export interface PlanResponse {
  planner: string;
  summary: string;
  features: PlannedFeature[];
  warnings: string[];
  needsReview: boolean;
}

// Catalog entry served by GET /api/features
export interface CatalogEntry {
  feature: FeatureType;
  label: string;
  defaultScaleMm?: Vec3;
  params?: Record<string, number>;
}

export interface FeatureCatalog {
  additive: CatalogEntry[];
  subtractive: CatalogEntry[];
}
