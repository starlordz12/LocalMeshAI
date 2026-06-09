// Bottom panel: operation log / geometry warnings / errors, plus quick geometry actions
// (repair non-manifold mesh, toggle baked-result preview).

import { useEffect, useRef } from "react";
import { useStore } from "../store/projectStore";

export default function StatusConsole() {
  const log = useStore((s) => s.log);
  const project = useStore((s) => s.project);
  const showResult = useStore((s) => s.showResult);
  const resultPreviewUrl = useStore((s) => s.resultPreviewUrl);
  const setShowResult = useStore((s) => s.setShowResult);
  const repairMesh = useStore((s) => s.repairMesh);
  const busy = useStore((s) => s.busy);

  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [log.length]);

  const mesh = project?.meshes[0] ?? null;
  const needsRepair = mesh?.analysis && !mesh.analysis.isWatertight;

  return (
    <div className="status-console">
      <div className="console-bar">
        <span className="panel-subtitle">Status Console</span>
        <div className="console-actions">
          {needsRepair && (
            <button className="warn-btn" disabled={busy} onClick={() => repairMesh(mesh!.id)} title="Attempt conservative repair">
              Repair mesh
            </button>
          )}
          {resultPreviewUrl && (
            <label className="check-inline">
              <input type="checkbox" checked={showResult} onChange={(e) => setShowResult(e.target.checked)} />
              Show baked result
            </label>
          )}
        </div>
      </div>
      <div className="console-log">
        {log.length === 0 && <div className="log-line info">Ready. Import a model to begin.</div>}
        {log.map((l, i) => (
          <div key={i} className={`log-line ${l.level}`}>
            <span className="log-time">{new Date(l.time).toLocaleTimeString()}</span>
            <span className="log-text">{l.text}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
