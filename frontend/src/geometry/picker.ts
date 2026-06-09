// A tiny singleton the Viewer3D registers so the (DOM-level) AnnotationLayer can raycast a
// screen point onto the base mesh and recover a world-space anchor in mm. Kept out of the
// store because it is a transient function, not serializable project state.

import type { Vec3 } from "../types/operations";

export interface Picker {
  // ndc: normalized device coords in [-1, 1]. Returns world point (mm) or null on miss.
  pick?: (ndcX: number, ndcY: number) => Vec3 | null;
}

export const picker: Picker = {};
