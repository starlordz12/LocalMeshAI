// Left panel: project / objects tree — imported mesh, helper features (additive /
// subtractive / glue-on), and annotations. Each item has visibility, select, and
// suppress/delete controls.

import { useStore } from "../store/projectStore";
import { modeColor } from "../geometry/sceneState";
import type { Operation } from "../types/operations";

export default function ObjectTree() {
  const project = useStore((s) => s.project);
  const selectedId = useStore((s) => s.selectedId);
  const hiddenIds = useStore((s) => s.hiddenIds);
  const select = useStore((s) => s.select);
  const toggleHidden = useStore((s) => s.toggleHidden);
  const suppressOperation = useStore((s) => s.suppressOperation);
  const deleteOperation = useStore((s) => s.deleteOperation);
  const duplicateOperation = useStore((s) => s.duplicateOperation);
  const convertAnnotation = useStore((s) => s.convertAnnotation);
  const deleteAnnotation = useStore((s) => s.deleteAnnotation);

  if (!project) return <aside className="panel left">No project</aside>;

  const helpers = project.operations.filter((o) => o.type === "helper_feature");
  const groups: { label: string; items: Operation[] }[] = [
    { label: "Additive", items: helpers.filter((o) => o.mode === "additive") },
    { label: "Subtractive", items: helpers.filter((o) => o.mode === "subtractive") },
    { label: "Glue-on", items: helpers.filter((o) => o.mode === "glue_on") },
  ];

  return (
    <aside className="panel left">
      <div className="panel-title">Project</div>
      <div className="tree-section">
        <div className="tree-heading">Imported Mesh</div>
        {project.meshes.length === 0 && <div className="tree-empty">Import a model to begin.</div>}
        {project.meshes.map((m) => (
          <div
            key={m.id}
            className={`tree-row ${selectedId === m.id ? "sel" : ""}`}
            onClick={() => select(m.id)}
          >
            <button
              className="icon-btn"
              title={hiddenIds.includes(m.id) ? "Show" : "Hide"}
              onClick={(e) => {
                e.stopPropagation();
                toggleHidden(m.id);
              }}
            >
              {hiddenIds.includes(m.id) ? "🚫" : "👁"}
            </button>
            <span className="dot" style={{ background: "#9aa7b4" }} />
            <span className="tree-name" title={m.name}>{m.name}</span>
            <span className="tree-meta">{m.analysis?.triangleCount ?? "?"}△</span>
          </div>
        ))}
      </div>

      {groups.map((g) => (
        <div className="tree-section" key={g.label}>
          <div className="tree-heading">
            {g.label} <span className="count">{g.items.length}</span>
          </div>
          {g.items.length === 0 && <div className="tree-empty">—</div>}
          {g.items.map((op) => (
            <div
              key={op.id}
              className={`tree-row ${selectedId === op.id ? "sel" : ""} ${op.suppressed ? "suppressed" : ""}`}
              onClick={() => select(op.id)}
            >
              <button
                className="icon-btn"
                title={hiddenIds.includes(op.id) ? "Show" : "Hide"}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleHidden(op.id);
                }}
              >
                {hiddenIds.includes(op.id) ? "🚫" : "👁"}
              </button>
              <span className="dot" style={{ background: modeColor(op.mode) }} />
              <span className="tree-name" title={`${op.feature} (${op.mode})`}>{op.name}</span>
              <span className="row-actions">
                <button
                  className="icon-btn"
                  title={op.suppressed ? "Enable" : "Suppress (exclude from result)"}
                  onClick={(e) => {
                    e.stopPropagation();
                    suppressOperation(op.id, !op.suppressed);
                  }}
                >
                  {op.suppressed ? "▷" : "⏸"}
                </button>
                <button
                  className="icon-btn"
                  title="Duplicate"
                  onClick={(e) => {
                    e.stopPropagation();
                    duplicateOperation(op.id);
                  }}
                >
                  ⧉
                </button>
                <button
                  className="icon-btn danger"
                  title="Delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteOperation(op.id);
                  }}
                >
                  ✕
                </button>
              </span>
            </div>
          ))}
        </div>
      ))}

      <div className="tree-section">
        <div className="tree-heading">
          Annotations <span className="count">{project.annotations.length}</span>
        </div>
        {project.annotations.length === 0 && <div className="tree-empty">Use ✎ Pencil to mark intent.</div>}
        {project.annotations.map((a) => (
          <div
            key={a.id}
            className={`tree-row ${selectedId === a.id ? "sel" : ""}`}
            onClick={() => select(a.id)}
          >
            <span className="dot" style={{ background: "#ffb300" }} />
            <span className="tree-name" title={a.note}>{a.note || a.intent.replace(/_/g, " ")}</span>
            <span className="row-actions">
              {!a.convertedOperationId && (
                <button
                  className="icon-btn"
                  title="Convert to helper feature"
                  onClick={(e) => {
                    e.stopPropagation();
                    convertAnnotation(a.id);
                  }}
                >
                  →◆
                </button>
              )}
              <button
                className="icon-btn danger"
                title="Delete annotation"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteAnnotation(a.id);
                }}
              >
                ✕
              </button>
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
}
