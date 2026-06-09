// Right panel: Add-Helper palette + context inspector for the selected mesh or helper.

import { useStore } from "../store/projectStore";
import type { CatalogEntry, HelperMode, Operation, Vec3 } from "../types/operations";
import type { MeshInfo } from "../types/project";

function Num({
  label,
  value,
  onChange,
  step = 0.5,
  min,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
}) {
  return (
    <label className="num-field">
      <span>{label}</span>
      <input
        type="number"
        value={Number.isFinite(value) ? value : 0}
        step={step}
        min={min}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </label>
  );
}

function Vec3Field({ label, value, onChange, step = 0.5 }: { label: string; value: Vec3; onChange: (v: Vec3) => void; step?: number }) {
  const set = (i: number, v: number) => {
    const next: Vec3 = [...value];
    next[i] = Number.isFinite(v) ? v : 0;
    onChange(next);
  };
  return (
    <div className="vec3-field">
      <span className="vec3-label">{label}</span>
      <div className="vec3-inputs">
        {(["X", "Y", "Z"] as const).map((ax, i) => (
          <input key={ax} type="number" step={step} value={value[i]} onChange={(e) => set(i, parseFloat(e.target.value))} title={ax} />
        ))}
      </div>
    </div>
  );
}

// Feature-specific parameter keys worth surfacing as editable fields.
const PARAM_HINTS: Record<string, { key: string; label: string }[]> = {
  screw_boss: [
    { key: "outerDiameterMm", label: "Outer Ø (mm)" },
    { key: "holeDiameterMm", label: "Pilot Ø (mm)" },
    { key: "heightMm", label: "Height (mm)" },
  ],
  mounting_tab: [{ key: "holeDiameterMm", label: "Hole Ø (mm)" }],
  mounting_pad: [
    { key: "holeCount", label: "Hole count" },
    { key: "holeDiameterMm", label: "Hole Ø (mm)" },
    { key: "holeSpacingMm", label: "Spacing (mm)" },
  ],
  mounting_deck: [
    { key: "holeCount", label: "Hole count" },
    { key: "holeDiameterMm", label: "Hole Ø (mm)" },
    { key: "holeSpacingMm", label: "Spacing (mm)" },
  ],
  glue_plate: [
    { key: "holeCount", label: "Hole count" },
    { key: "holeDiameterMm", label: "Hole Ø (mm)" },
    { key: "holeSpacingMm", label: "Spacing (mm)" },
  ],
  cylinder: [{ key: "diameterMm", label: "Diameter (mm)" }, { key: "heightMm", label: "Height (mm)" }],
  cylinder_hole: [{ key: "diameterMm", label: "Diameter (mm)" }, { key: "heightMm", label: "Depth (mm)" }],
  screw_clearance_hole: [{ key: "holeDiameterMm", label: "Clearance Ø (mm)" }, { key: "heightMm", label: "Depth (mm)" }],
  cable_channel: [{ key: "cableDiameterMm", label: "Cable Ø (mm)" }],
  cable_guide: [{ key: "outerDiameterMm", label: "Outer Ø (mm)" }, { key: "cableDiameterMm", label: "Cable Ø (mm)" }],
};

function HelperInspector({ op }: { op: Operation }) {
  const update = useStore((s) => s.updateOperation);
  const exportHelper = useStore((s) => s.exportHelper);
  const project = useStore((s) => s.project);

  const setParam = (key: string, v: number) =>
    update(op.id, { parameters: { ...op.parameters, [key]: Number.isFinite(v) ? v : 0 } });

  const hints = PARAM_HINTS[op.feature] ?? [];

  return (
    <div className="inspector-body">
      <label className="num-field">
        <span>Name</span>
        <input type="text" value={op.name} onChange={(e) => update(op.id, { name: e.target.value })} />
      </label>

      <div className="kv"><span>Feature</span><b>{op.feature.replace(/_/g, " ")}</b></div>

      <label className="num-field">
        <span>Mode</span>
        <select value={op.mode} onChange={(e) => update(op.id, { mode: e.target.value as HelperMode, exportSeparate: e.target.value === "glue_on" ? true : op.exportSeparate })}>
          <option value="additive">Additive (union)</option>
          <option value="subtractive">Subtractive (cut)</option>
          <option value="glue_on">Glue-on (separate part)</option>
        </select>
      </label>

      <Vec3Field label="Size (mm)" value={op.scaleMm} onChange={(v) => update(op.id, { scaleMm: v })} />
      <Vec3Field label="Position (mm)" value={op.positionMm} onChange={(v) => update(op.id, { positionMm: v })} />
      <Vec3Field label="Rotation (°)" value={op.rotationDeg} step={5} onChange={(v) => update(op.id, { rotationDeg: v })} />

      {hints.length > 0 && (
        <div className="param-block">
          <div className="param-title">Parameters</div>
          {hints.map((h) => (
            <Num
              key={h.key}
              label={h.label}
              value={typeof op.parameters[h.key] === "number" ? (op.parameters[h.key] as number) : 0}
              step={h.key === "holeCount" ? 1 : 0.2}
              min={0}
              onChange={(v) => setParam(h.key, v)}
            />
          ))}
        </div>
      )}

      <label className="check-field">
        <input
          type="checkbox"
          checked={op.exportSeparate}
          onChange={(e) => update(op.id, { exportSeparate: e.target.checked })}
        />
        Export as separate piece (glue-on)
      </label>

      <div className="kv"><span>Boolean target</span><b>{project?.meshes.find((m) => m.id === op.targetMeshId)?.name ?? "—"}</b></div>

      <button className="full accent" onClick={() => exportHelper(op.id, "stl")}>Export this helper as STL</button>
    </div>
  );
}

function MeshInspector({ mesh }: { mesh: MeshInfo }) {
  const rotate90 = useStore((s) => s.rotateMesh90);
  const updateMesh = useStore((s) => s.updateMeshTransform);
  const layFlat = useStore((s) => s.layFlat);
  const centerOnBed = useStore((s) => s.centerOnBed);
  const moveToBuildPlate = useStore((s) => s.moveToBuildPlate);
  const a = mesh.analysis;

  return (
    <div className="inspector-body">
      <div className="kv"><span>File</span><b title={mesh.name}>{mesh.name}</b></div>
      {a && (
        <>
          <div className="kv"><span>Bounding box</span><b>{a.boundingBox.size.map((s) => s.toFixed(1)).join(" × ")} mm</b></div>
          <div className="kv"><span>Volume</span><b>{a.volumeMm3 != null ? `${(a.volumeMm3 / 1000).toFixed(2)} cm³` : "—"}</b></div>
          <div className="kv"><span>Surface area</span><b>{(a.surfaceAreaMm2 / 100).toFixed(2)} cm²</b></div>
          <div className="kv"><span>Triangles</span><b>{a.triangleCount.toLocaleString()}</b></div>
          <div className="kv">
            <span>Repair status</span>
            <b className={a.isWatertight ? "ok" : "warn"}>{a.isWatertight ? "watertight" : "NOT watertight"}</b>
          </div>
          {!a.isWatertight && <div className="hint warn">Non-manifold mesh — booleans may fail. Repair from the status console.</div>}
        </>
      )}

      <div className="param-block">
        <div className="param-title">Orientation</div>
        <div className="btn-row">
          <button onClick={() => rotate90(mesh.id, 0)}>Rot X +90°</button>
          <button onClick={() => rotate90(mesh.id, 1)}>Rot Y +90°</button>
          <button onClick={() => rotate90(mesh.id, 2)}>Rot Z +90°</button>
        </div>
        <Vec3Field label="Free rotation (°)" value={mesh.rotationDeg} step={5} onChange={(v) => updateMesh(mesh.id, { rotationDeg: v })} />
        <Vec3Field label="Position (mm)" value={mesh.positionMm} onChange={(v) => updateMesh(mesh.id, { positionMm: v })} />
        <div className="btn-row">
          <button onClick={() => layFlat(mesh.id)}>Lay flat</button>
          <button onClick={() => centerOnBed(mesh.id)}>Center on bed</button>
          <button onClick={() => moveToBuildPlate(mesh.id)}>To build plate</button>
        </div>
      </div>
    </div>
  );
}

function AddHelperPalette() {
  const catalog = useStore((s) => s.catalog);
  const addCatalogHelper = useStore((s) => s.addCatalogHelper);
  if (!catalog) return null;

  const group = (title: string, items: CatalogEntry[]) => (
    <div className="palette-group">
      <div className="palette-title">{title}</div>
      <div className="palette-grid">
        {items.map((e) => (
          <button key={e.feature} className="palette-btn" onClick={() => addCatalogHelper(e)} title={e.feature}>
            {e.label}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="add-helper">
      <div className="panel-subtitle">Add Helper</div>
      {group("Additive", catalog.additive)}
      {group("Subtractive", catalog.subtractive)}
    </div>
  );
}

export default function Inspector() {
  const project = useStore((s) => s.project);
  const selectedId = useStore((s) => s.selectedId);

  const op = project?.operations.find((o) => o.id === selectedId) ?? null;
  const mesh = project?.meshes.find((m) => m.id === selectedId) ?? null;

  return (
    <aside className="panel right">
      <div className="panel-title">Inspector</div>
      <AddHelperPalette />
      <div className="divider" />
      {op ? (
        <>
          <div className="panel-subtitle">Helper: {op.name}</div>
          <HelperInspector op={op} />
        </>
      ) : mesh ? (
        <>
          <div className="panel-subtitle">Mesh</div>
          <MeshInspector mesh={mesh} />
        </>
      ) : (
        <div className="inspector-empty">Select a mesh or helper, or add a helper above.</div>
      )}
    </aside>
  );
}
