// Small geometry/transform helpers shared across the UI.

import type { CatalogEntry, FeatureType, HelperMode, Operation, Vec3 } from "../types/operations";

export const DEG2RAD = Math.PI / 180;
export const RAD2DEG = 180 / Math.PI;

export function degToRadVec(v: Vec3): Vec3 {
  return [v[0] * DEG2RAD, v[1] * DEG2RAD, v[2] * DEG2RAD];
}

export function radToDegVec(v: Vec3): Vec3 {
  return [v[0] * RAD2DEG, v[1] * RAD2DEG, v[2] * RAD2DEG];
}

export function round(v: number, dp = 2): number {
  const f = 10 ** dp;
  return Math.round(v * f) / f;
}

export function roundVec(v: Vec3, dp = 2): Vec3 {
  return [round(v[0], dp), round(v[1], dp), round(v[2], dp)];
}

let counter = 0;
export function genId(prefix: string): string {
  counter += 1;
  return `${prefix}_${Date.now().toString(36)}_${counter.toString(36)}`;
}

const SUBTRACTIVE_FEATURES = new Set<FeatureType>([
  "box_cutout",
  "cylinder_hole",
  "rectangular_slot",
  "cable_channel",
  "vent_slot",
  "screw_clearance_hole",
  "pocket",
]);

export function defaultModeForFeature(feature: FeatureType): HelperMode {
  return SUBTRACTIVE_FEATURES.has(feature) ? "subtractive" : "additive";
}

/** Build a fresh helper Operation from a catalog entry, placed at `position`. */
export function operationFromCatalog(
  entry: CatalogEntry,
  targetMeshId: string | null,
  position: Vec3 = [0, 0, 0]
): Operation {
  return {
    id: genId("op"),
    type: "helper_feature",
    name: entry.label,
    mode: defaultModeForFeature(entry.feature),
    feature: entry.feature,
    targetMeshId,
    positionMm: position,
    rotationDeg: [0, 0, 0],
    scaleMm: entry.defaultScaleMm ?? [20, 10, 3],
    parameters: { ...(entry.params ?? {}) },
    sourceAnnotationId: null,
    suppressed: false,
    exportSeparate: false,
  };
}
