// Shared scene constants and small enums for the viewport.

export type DisplayMode = "solid" | "wireframe" | "transparent" | "xray";

export type GizmoMode = "translate" | "rotate";

// Build plate / grid (mm). A common desktop printer bed footprint.
export const BUILD_PLATE_MM = 256;
export const GRID_DIVISIONS = 32; // ~8 mm cells

export const COLORS = {
  baseMesh: "#9aa7b4",
  baseMeshSelected: "#c9d6e3",
  additive: "#4caf50",
  subtractive: "#e0533d",
  glueOn: "#3d8be0",
  annotation: "#ffb300",
  buildPlate: "#3a4150",
  buildPlateAxis: "#5a6577",
  resultPreview: "#7e57c2",
};

export function modeColor(mode: string): string {
  if (mode === "subtractive") return COLORS.subtractive;
  if (mode === "glue_on") return COLORS.glueOn;
  return COLORS.additive;
}
