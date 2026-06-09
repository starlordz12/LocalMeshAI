// Central app state (zustand). The frontend is the source of truth for the in-memory
// project; geometry/export calls send the whole project to the backend. Local edits mutate
// here; "Save" persists, and apply/export always send the latest project.

import { create } from "zustand";
import { api, fileUrl } from "../api/client";
import type { Annotation, CatalogEntry, FeatureCatalog, Operation, PlannedFeature, PlanResponse, Vec3 } from "../types/operations";
import type { EngineStatus, MeshInfo, Project } from "../types/project";
import { genId, operationFromCatalog, roundVec } from "../geometry/transformUtils";
import type { DisplayMode, GizmoMode } from "../geometry/sceneState";

export interface LogEntry {
  level: "info" | "warn" | "error";
  text: string;
  time: number;
}

interface State {
  project: Project | null;
  engine: EngineStatus | null;
  catalog: FeatureCatalog | null;
  defaults: Record<string, number | string> | null;

  selectedId: string | null;
  hiddenIds: string[];
  displayMode: DisplayMode;
  gizmoMode: GizmoMode;
  pencilMode: boolean;
  showBounds: boolean;
  showResult: boolean;

  busy: boolean;
  dirty: boolean;
  resultPreviewUrl: string | null;
  log: LogEntry[];
  plan: PlanResponse | null;

  // undo/redo history (snapshots of the project) + a view-reset signal for the viewport
  past: Project[];
  future: Project[];
  viewResetNonce: number;
  undo: () => void;
  redo: () => void;
  resetView: () => void;

  // bootstrap / project lifecycle
  bootstrap: () => Promise<void>;
  createProject: (name: string) => Promise<void>;
  importFile: (file: File) => Promise<void>;
  save: () => Promise<void>;
  reload: () => Promise<void>;

  // selection / view
  select: (id: string | null) => void;
  toggleHidden: (id: string) => void;
  setDisplayMode: (m: DisplayMode) => void;
  setGizmoMode: (m: GizmoMode) => void;
  togglePencil: () => void;
  toggleBounds: () => void;
  setShowResult: (b: boolean) => void;

  // operations
  addCatalogHelper: (entry: CatalogEntry, position?: Vec3) => void;
  addPlannedFeature: (pf: PlannedFeature) => void;
  updateOperation: (id: string, patch: Partial<Operation>) => void;
  deleteOperation: (id: string) => Promise<void>;
  suppressOperation: (id: string, suppressed: boolean) => void;
  duplicateOperation: (id: string) => void;

  // mesh orientation
  updateMeshTransform: (meshId: string, patch: Partial<Pick<MeshInfo, "positionMm" | "rotationDeg">>) => void;
  rotateMesh90: (meshId: string, axis: 0 | 1 | 2) => void;
  centerOnBed: (meshId: string) => void;
  moveToBuildPlate: (meshId: string) => void;
  layFlat: (meshId: string) => void;

  repairMesh: (meshId: string) => Promise<void>;

  // annotations
  addAnnotation: (ann: Annotation) => void;
  updateAnnotation: (id: string, patch: Partial<Annotation>) => void;
  deleteAnnotation: (id: string) => void;
  convertAnnotation: (id: string) => void;

  // geometry / export
  applyBoolean: () => Promise<void>;
  exportFinal: (format?: string) => Promise<void>;
  exportHelper: (id: string, format?: string) => Promise<void>;

  // AI
  runPlan: (prompt: string, planner: string) => Promise<void>;
  clearPlan: () => void;

  pushLog: (level: LogEntry["level"], text: string) => void;
}

const HISTORY_LIMIT = 50;

function snapshot(p: Project): Project {
  // Structured deep clone so undo restores nested operation/mesh/annotation values.
  return JSON.parse(JSON.stringify(p)) as Project;
}

function mutateProject(get: () => State, set: (p: Partial<State>) => void, fn: (p: Project) => void) {
  const project = get().project;
  if (!project) return;
  const prev = snapshot(project);
  const next: Project = { ...project, operations: [...project.operations], meshes: [...project.meshes], annotations: [...project.annotations] };
  fn(next);
  const past = [...get().past, prev].slice(-HISTORY_LIMIT);
  set({ project: next, dirty: true, past, future: [] });
}

export const useStore = create<State>((set, get) => ({
  project: null,
  engine: null,
  catalog: null,
  defaults: null,
  selectedId: null,
  hiddenIds: [],
  displayMode: "solid",
  gizmoMode: "translate",
  pencilMode: false,
  showBounds: true,
  showResult: false,
  busy: false,
  dirty: false,
  resultPreviewUrl: null,
  log: [],
  plan: null,
  past: [],
  future: [],
  viewResetNonce: 0,

  undo: () => {
    const { past, project } = get();
    if (!past.length || !project) return;
    const prev = past[past.length - 1];
    set({
      project: prev,
      past: past.slice(0, -1),
      future: [snapshot(project), ...get().future].slice(0, HISTORY_LIMIT),
      dirty: true,
    });
    get().pushLog("info", "Undo.");
  },

  redo: () => {
    const { future, project } = get();
    if (!future.length || !project) return;
    const nextP = future[0];
    set({
      project: nextP,
      future: future.slice(1),
      past: [...get().past, snapshot(project)].slice(-HISTORY_LIMIT),
      dirty: true,
    });
    get().pushLog("info", "Redo.");
  },

  resetView: () => set((s) => ({ viewResetNonce: s.viewResetNonce + 1 })),

  pushLog: (level, text) =>
    set((s) => ({ log: [...s.log.slice(-200), { level, text, time: Date.now() }] })),

  bootstrap: async () => {
    try {
      const [health, features] = await Promise.all([api.health(), api.features()]);
      set({ engine: health.engine, catalog: features.catalog, defaults: features.defaults });
      get().pushLog("info", `Backend ${health.version} ready. Boolean engine: ${health.engine.booleanEngine}.`);
      if (health.engine.booleanEngine === "none") {
        get().pushLog("warn", "No boolean engine available — install Blender or manifold3d to apply unions/cuts.");
      }
    } catch (e) {
      get().pushLog("error", `Cannot reach backend at ${api ? "" : ""}: ${(e as Error).message}. Start the backend (uvicorn) first.`);
    }
    if (!get().project) {
      try {
        await get().createProject("Untitled Project");
      } catch {
        /* logged in createProject */
      }
    }
  },

  createProject: async (name) => {
    try {
      const project = await api.newProject(name);
      set({ project, selectedId: null, hiddenIds: [], resultPreviewUrl: null, dirty: false, plan: null });
      get().pushLog("info", `Created project "${project.name}" (${project.id}).`);
    } catch (e) {
      get().pushLog("error", `Failed to create project: ${(e as Error).message}`);
    }
  },

  importFile: async (file) => {
    const project = get().project;
    if (!project) return;
    set({ busy: true });
    try {
      const res = await api.importMesh(project.id, file);
      set({ project: res.project, selectedId: res.mesh.id, dirty: false, resultPreviewUrl: null });
      const a = res.mesh.analysis;
      get().pushLog("info", `Imported ${res.mesh.name}: ${a?.triangleCount ?? "?"} tris, ${a?.isWatertight ? "watertight" : "NOT watertight"}.`);
      a?.warnings.forEach((w) => get().pushLog("warn", w));
    } catch (e) {
      get().pushLog("error", `Import failed: ${(e as Error).message}`);
    } finally {
      set({ busy: false });
    }
  },

  save: async () => {
    const project = get().project;
    if (!project) return;
    set({ busy: true });
    try {
      const saved = await api.saveProject(project);
      set({ project: saved, dirty: false });
      get().pushLog("info", "Project saved.");
    } catch (e) {
      get().pushLog("error", `Save failed: ${(e as Error).message}`);
    } finally {
      set({ busy: false });
    }
  },

  reload: async () => {
    const project = get().project;
    if (!project) return;
    try {
      const fresh = await api.getProject(project.id);
      set({ project: fresh, dirty: false });
      get().pushLog("info", "Project reloaded from disk.");
    } catch (e) {
      get().pushLog("error", `Reload failed: ${(e as Error).message}`);
    }
  },

  select: (id) => set({ selectedId: id }),
  toggleHidden: (id) =>
    set((s) => ({
      hiddenIds: s.hiddenIds.includes(id) ? s.hiddenIds.filter((x) => x !== id) : [...s.hiddenIds, id],
    })),
  setDisplayMode: (m) => set({ displayMode: m }),
  setGizmoMode: (m) => set({ gizmoMode: m }),
  togglePencil: () => set((s) => ({ pencilMode: !s.pencilMode })),
  toggleBounds: () => set((s) => ({ showBounds: !s.showBounds })),
  setShowResult: (b) => set({ showResult: b }),

  addCatalogHelper: (entry, position) => {
    const project = get().project;
    const mesh = project?.meshes[0] ?? null;
    const op = operationFromCatalog(entry, mesh?.id ?? null, position ?? defaultHelperPosition(mesh, entry.defaultScaleMm ?? [20, 10, 3]));
    mutateProject(get, set, (p) => p.operations.push(op));
    set({ selectedId: op.id });
    get().pushLog("info", `Added helper "${op.name}" (${op.mode}).`);
  },

  addPlannedFeature: (pf) => {
    const project = get().project;
    const meshId = project?.meshes[0]?.id ?? null;
    const op: Operation = {
      id: genId("op"),
      type: "helper_feature",
      name: pf.name,
      mode: pf.mode,
      feature: pf.feature,
      targetMeshId: meshId,
      positionMm: pf.positionMm,
      rotationDeg: pf.rotationDeg,
      scaleMm: pf.scaleMm,
      parameters: { ...pf.parameters },
      sourceAnnotationId: null,
      suppressed: false,
      exportSeparate: pf.mode === "glue_on",
    };
    mutateProject(get, set, (p) => p.operations.push(op));
    set({ selectedId: op.id });
    get().pushLog("info", `Created "${op.name}" from AI plan.`);
  },

  updateOperation: (id, patch) =>
    mutateProject(get, set, (p) => {
      const i = p.operations.findIndex((o) => o.id === id);
      if (i >= 0) p.operations[i] = { ...p.operations[i], ...patch };
    }),

  deleteOperation: async (id) => {
    mutateProject(get, set, (p) => {
      p.operations = p.operations.filter((o) => o.id !== id);
    });
    if (get().selectedId === id) set({ selectedId: null });
    get().pushLog("info", "Deleted operation.");
  },

  suppressOperation: (id, suppressed) => {
    get().updateOperation(id, { suppressed });
    get().pushLog("info", `${suppressed ? "Suppressed" : "Enabled"} operation.`);
  },

  duplicateOperation: (id) => {
    const op = get().project?.operations.find((o) => o.id === id);
    if (!op) return;
    const copy: Operation = { ...op, id: genId("op"), name: `${op.name} copy`, positionMm: roundVec([op.positionMm[0] + 5, op.positionMm[1] + 5, op.positionMm[2]]) };
    mutateProject(get, set, (p) => p.operations.push(copy));
    set({ selectedId: copy.id });
  },

  updateMeshTransform: (meshId, patch) =>
    mutateProject(get, set, (p) => {
      const i = p.meshes.findIndex((m) => m.id === meshId);
      if (i >= 0) p.meshes[i] = { ...p.meshes[i], ...patch };
    }),

  rotateMesh90: (meshId, axis) => {
    const mesh = get().project?.meshes.find((m) => m.id === meshId);
    if (!mesh) return;
    const rot: Vec3 = [...mesh.rotationDeg];
    rot[axis] = (rot[axis] + 90) % 360;
    get().updateMeshTransform(meshId, { rotationDeg: rot });
  },

  centerOnBed: (meshId) => {
    get().updateMeshTransform(meshId, { positionMm: [0, 0, get().project?.meshes.find((m) => m.id === meshId)?.positionMm[2] ?? 0] });
    get().pushLog("info", "Centered model over the build plate origin (X/Y).");
  },

  moveToBuildPlate: (meshId) => {
    const mesh = get().project?.meshes.find((m) => m.id === meshId);
    if (!mesh?.analysis) return;
    // Lift so the lowest point sits at Z=0. (Approximate: ignores rotation for MVP.)
    const minZ = mesh.analysis.boundingBox.min[2];
    const pos: Vec3 = [mesh.positionMm[0], mesh.positionMm[1], mesh.positionMm[2] - minZ];
    get().updateMeshTransform(meshId, { positionMm: pos });
    get().pushLog("info", "Moved model onto the build plate (Z=0).");
  },

  layFlat: (meshId) => {
    // MVP heuristic: lay-flat attempts a 90° tip onto the largest face is non-trivial; we
    // reset rotation and drop to the plate, which is the common "make it sit flat" intent.
    get().updateMeshTransform(meshId, { rotationDeg: [0, 0, 0] });
    get().moveToBuildPlate(meshId);
    get().pushLog("info", "Lay-flat: reset orientation and dropped to the build plate.");
  },

  repairMesh: async (meshId) => {
    const project = get().project;
    if (!project) return;
    set({ busy: true });
    try {
      // Persist current state first (repair reads the saved source on disk), repair, then
      // reload to pick up the repaired source file + fresh analysis.
      await api.saveProject(project);
      const res = await api.repair(project.id, meshId);
      res.actions.forEach((a) => get().pushLog("info", `repair: ${a}`));
      get().pushLog(res.success ? "info" : "warn", res.message);
      get().pushLog("info", `watertight ${res.before.isWatertight} → ${res.after.isWatertight}, tris ${res.before.triangleCount} → ${res.after.triangleCount}`);
      await get().reload();
    } catch (e) {
      get().pushLog("error", `Repair failed: ${(e as Error).message}`);
    } finally {
      set({ busy: false });
    }
  },

  addAnnotation: (ann) => {
    mutateProject(get, set, (p) => p.annotations.push(ann));
    set({ selectedId: ann.id });
  },
  updateAnnotation: (id, patch) =>
    mutateProject(get, set, (p) => {
      const i = p.annotations.findIndex((a) => a.id === id);
      if (i >= 0) p.annotations[i] = { ...p.annotations[i], ...patch };
    }),
  deleteAnnotation: (id) => {
    mutateProject(get, set, (p) => {
      p.annotations = p.annotations.filter((a) => a.id !== id);
    });
    if (get().selectedId === id) set({ selectedId: null });
  },

  convertAnnotation: (id) => {
    const project = get().project;
    const ann = project?.annotations.find((a) => a.id === id);
    if (!project || !ann) return;
    const { feature, mode } = intentToFeature(ann.intent);
    const meshId = project.meshes[0]?.id ?? null;
    const op: Operation = {
      id: genId("op"),
      type: "helper_feature",
      name: ann.note?.trim() || labelForFeature(feature),
      mode,
      feature,
      targetMeshId: meshId,
      positionMm: ann.worldAnchorMm ? roundVec(ann.worldAnchorMm) : [0, 0, 0],
      rotationDeg: [0, 0, 0],
      scaleMm: defaultScaleForFeature(feature),
      parameters: {},
      sourceAnnotationId: ann.id,
      suppressed: false,
      exportSeparate: mode === "glue_on",
    };
    mutateProject(get, set, (p) => {
      p.operations.push(op);
      const i = p.annotations.findIndex((a) => a.id === id);
      if (i >= 0) p.annotations[i] = { ...p.annotations[i], convertedOperationId: op.id };
    });
    set({ selectedId: op.id });
    get().pushLog("info", `Converted annotation to helper "${op.name}".`);
  },

  applyBoolean: async () => {
    const project = get().project;
    const meshId = project?.meshes[0]?.id;
    if (!project || !meshId) {
      get().pushLog("warn", "Import a model before applying geometry operations.");
      return;
    }
    set({ busy: true });
    try {
      const res = await api.applyBoolean(project, meshId);
      res.log.forEach((l) => get().pushLog("info", l));
      if (res.success) {
        get().pushLog("info", res.message);
        if (res.after) {
          get().pushLog(
            res.after.isWatertight ? "info" : "warn",
            `Result: ${res.after.triangleCount} tris, watertight=${res.after.isWatertight}.`
          );
          res.after.warnings.forEach((w) => get().pushLog("warn", w));
        }
        if (res.outputFile) {
          set({ resultPreviewUrl: `${fileUrl(project.id, res.outputFile)}?t=${Date.now()}`, showResult: true });
        }
      } else {
        get().pushLog("error", res.message);
      }
    } catch (e) {
      get().pushLog("error", `Apply failed: ${(e as Error).message}`);
    } finally {
      set({ busy: false });
    }
  },

  exportFinal: async (format = "stl") => {
    const project = get().project;
    const meshId = project?.meshes[0]?.id;
    if (!project || !meshId) {
      get().pushLog("warn", "Import a model first.");
      return;
    }
    set({ busy: true });
    try {
      const res = await api.exportFinal(project, meshId, format);
      if (res.success && res.file) {
        get().pushLog("info", res.message);
        triggerDownload(project.id, res.file);
      } else {
        get().pushLog("error", res.message);
      }
    } catch (e) {
      get().pushLog("error", `Export failed: ${(e as Error).message}`);
    } finally {
      set({ busy: false });
    }
  },

  exportHelper: async (id, format = "stl") => {
    const project = get().project;
    if (!project) return;
    set({ busy: true });
    try {
      const res = await api.exportHelper(project, id, format);
      if (res.success && res.file) {
        get().pushLog("info", res.message);
        res.validation?.warnings.forEach((w) => get().pushLog("warn", w));
        triggerDownload(project.id, res.file);
      } else {
        get().pushLog("error", res.message);
      }
    } catch (e) {
      get().pushLog("error", `Helper export failed: ${(e as Error).message}`);
    } finally {
      set({ busy: false });
    }
  },

  runPlan: async (prompt, planner) => {
    const project = get().project;
    set({ busy: true });
    try {
      const res = await api.plan(prompt, {
        projectId: project?.id,
        meshId: project?.meshes[0]?.id,
        planner,
      });
      set({ plan: res });
      get().pushLog("info", `AI plan (${res.planner}): ${res.summary}`);
      res.warnings.forEach((w) => get().pushLog("warn", w));
    } catch (e) {
      get().pushLog("error", `Planner failed: ${(e as Error).message}`);
    } finally {
      set({ busy: false });
    }
  },

  clearPlan: () => set({ plan: null }),
}));

// --- helpers ---------------------------------------------------------------------------

/** Place a new helper on top of the imported mesh (world frame) so it's immediately visible
 *  and useful, instead of at the world origin. Ignores mesh rotation (fine for the common
 *  identity orientation); the user can fine-tune in the inspector. */
function defaultHelperPosition(mesh: MeshInfo | null, scale: Vec3): Vec3 {
  if (!mesh?.analysis) return [0, 0, 0];
  const bb = mesh.analysis.boundingBox;
  const cx = (bb.min[0] + bb.max[0]) / 2 + mesh.positionMm[0];
  const cy = (bb.min[1] + bb.max[1]) / 2 + mesh.positionMm[1];
  const topZ = bb.max[2] + mesh.positionMm[2] + scale[2] / 2;
  return roundVec([cx, cy, topZ]);
}

function triggerDownload(projectId: string, relPath: string) {
  const a = document.createElement("a");
  a.href = fileUrl(projectId, relPath);
  a.download = relPath.split("/").pop() || "export";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function intentToFeature(intent: Annotation["intent"]): { feature: Operation["feature"]; mode: Operation["mode"] } {
  switch (intent) {
    case "cut_material":
    case "vent_cutout":
      return { feature: "box_cutout", mode: "subtractive" };
    case "drill_hole":
      return { feature: "cylinder_hole", mode: "subtractive" };
    case "cable_channel":
      return { feature: "cable_channel", mode: "subtractive" };
    case "mounting_tab":
      return { feature: "mounting_tab", mode: "additive" };
    case "screw_boss":
      return { feature: "screw_boss", mode: "additive" };
    case "fairing":
      return { feature: "fairing", mode: "additive" };
    case "flat_pad":
      return { feature: "mounting_pad", mode: "additive" };
    case "glue_on":
      return { feature: "glue_plate", mode: "glue_on" };
    case "add_material":
      return { feature: "box", mode: "additive" };
    default:
      return { feature: "box", mode: "additive" };
  }
}

function labelForFeature(feature: Operation["feature"]): string {
  return feature.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function defaultScaleForFeature(feature: Operation["feature"]): Vec3 {
  const table: Partial<Record<Operation["feature"], Vec3>> = {
    box: [20, 20, 10],
    box_cutout: [12, 12, 12],
    cylinder_hole: [6, 6, 20],
    cable_channel: [40, 4, 4],
    mounting_tab: [18, 10, 3],
    screw_boss: [6, 6, 6],
    fairing: [30, 16, 8],
    mounting_pad: [28, 14, 3],
    glue_plate: [25, 25, 2.5],
  };
  return table[feature] ?? [20, 10, 3];
}
