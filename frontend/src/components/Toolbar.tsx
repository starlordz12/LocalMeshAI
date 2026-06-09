// Top toolbar: project actions, exports, undo/redo, view, and run-geometry.

import { useRef } from "react";
import { useStore } from "../store/projectStore";

export default function Toolbar() {
  const fileRef = useRef<HTMLInputElement>(null);

  const project = useStore((s) => s.project);
  const engine = useStore((s) => s.engine);
  const busy = useStore((s) => s.busy);
  const dirty = useStore((s) => s.dirty);
  const selectedId = useStore((s) => s.selectedId);
  const pencilMode = useStore((s) => s.pencilMode);
  const canUndo = useStore((s) => s.past.length > 0);
  const canRedo = useStore((s) => s.future.length > 0);

  const createProject = useStore((s) => s.createProject);
  const importFile = useStore((s) => s.importFile);
  const save = useStore((s) => s.save);
  const exportFinal = useStore((s) => s.exportFinal);
  const exportHelper = useStore((s) => s.exportHelper);
  const undo = useStore((s) => s.undo);
  const redo = useStore((s) => s.redo);
  const resetView = useStore((s) => s.resetView);
  const applyBoolean = useStore((s) => s.applyBoolean);
  const togglePencil = useStore((s) => s.togglePencil);

  const hasMesh = !!project?.meshes.length;
  const selectedOp = project?.operations.find((o) => o.id === selectedId) ?? null;

  const onPickFile = () => fileRef.current?.click();
  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) importFile(f);
    e.target.value = "";
  };

  return (
    <div className="toolbar">
      <input
        ref={fileRef}
        type="file"
        accept=".stl,.obj,.ply,.3mf"
        style={{ display: "none" }}
        onChange={onFileChange}
      />

      <span className="brand">LocalMeshAI</span>

      <div className="tb-group">
        <button onClick={() => createProject("Untitled Project")} disabled={busy}>New</button>
        <button onClick={onPickFile} disabled={busy || !project} title="Import STL / OBJ / PLY / 3MF">
          Import Model
        </button>
        <button onClick={save} disabled={busy || !project} className={dirty ? "accent" : ""}>
          Save{dirty ? " *" : ""}
        </button>
      </div>

      <div className="tb-group">
        <button onClick={() => exportFinal("stl")} disabled={busy || !hasMesh} title="Bake helpers and export final STL">
          Export Final STL
        </button>
        <button
          onClick={() => selectedOp && exportHelper(selectedOp.id, "stl")}
          disabled={busy || !selectedOp}
          title="Export the selected helper as its own glue-on STL"
        >
          Export Helper STL
        </button>
      </div>

      <div className="tb-group">
        <button onClick={undo} disabled={!canUndo} title="Undo">↶</button>
        <button onClick={redo} disabled={!canRedo} title="Redo">↷</button>
        <button onClick={resetView} title="Reset camera">Reset View</button>
        <button onClick={togglePencil} className={pencilMode ? "active" : ""} title="Edit pencil / annotation mode">
          ✎ Pencil
        </button>
      </div>

      <div className="tb-group">
        <button
          onClick={applyBoolean}
          disabled={busy || !hasMesh || engine?.booleanEngine === "none"}
          className="accent"
          title={engine?.booleanEngine === "none" ? "No boolean engine available" : "Apply additive/subtractive helpers"}
        >
          ▶ Run Geometry Operation
        </button>
      </div>

      <div className="tb-spacer" />
      <div className="tb-status">
        {busy && <span className="spinner" />}
        <span className="engine-pill" title={engine?.blenderPath || ""}>
          engine: {engine?.booleanEngine ?? "…"}
        </span>
      </div>
    </div>
  );
}
