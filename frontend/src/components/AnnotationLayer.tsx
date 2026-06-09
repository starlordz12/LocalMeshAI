// Edit-pencil overlay. When pencil mode is on, this captures a freehand stroke over the
// viewport, raycasts the stroke centroid onto the base mesh for a world anchor (mm), and
// lets the user tag the stroke's intent + note. The stroke becomes an annotation in the
// tree; annotations convert to editable helper features.

import { useRef, useState } from "react";
import { useStore } from "../store/projectStore";
import { picker } from "../geometry/picker";
import { genId } from "../geometry/transformUtils";
import type { AnnotationIntent, Vec3 } from "../types/operations";

const INTENTS: { value: AnnotationIntent; label: string }[] = [
  { value: "add_material", label: "Add material" },
  { value: "cut_material", label: "Cut / remove material" },
  { value: "glue_on", label: "Glue-on part" },
  { value: "drill_hole", label: "Drill hole" },
  { value: "cable_channel", label: "Cable channel" },
  { value: "mounting_tab", label: "Mounting tab" },
  { value: "screw_boss", label: "Screw boss" },
  { value: "vent_cutout", label: "Vent / cutout" },
  { value: "fairing", label: "Aerodynamic fairing" },
  { value: "flat_pad", label: "Flat mounting pad" },
  { value: "note", label: "Custom note" },
];

interface Pending {
  points: [number, number][]; // pixel coords within the layer
  centroidPx: [number, number];
  anchor: Vec3 | null;
}

export default function AnnotationLayer() {
  const pencilMode = useStore((s) => s.pencilMode);
  const addAnnotation = useStore((s) => s.addAnnotation);
  const project = useStore((s) => s.project);

  const layerRef = useRef<HTMLDivElement>(null);
  const drawing = useRef(false);
  const [stroke, setStroke] = useState<[number, number][]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const [intent, setIntent] = useState<AnnotationIntent>("cut_material");
  const [note, setNote] = useState("");

  if (!pencilMode) return null;

  const rect = () => layerRef.current!.getBoundingClientRect();

  const toLocal = (e: React.PointerEvent): [number, number] => {
    const r = rect();
    return [e.clientX - r.left, e.clientY - r.top];
  };

  const onDown = (e: React.PointerEvent) => {
    if (pending) return;
    drawing.current = true;
    setStroke([toLocal(e)]);
  };
  const onMove = (e: React.PointerEvent) => {
    if (!drawing.current) return;
    setStroke((s) => [...s, toLocal(e)]);
  };
  const onUp = () => {
    if (!drawing.current) return;
    drawing.current = false;
    if (stroke.length < 2) {
      setStroke([]);
      return;
    }
    const r = rect();
    const cx = stroke.reduce((a, p) => a + p[0], 0) / stroke.length;
    const cy = stroke.reduce((a, p) => a + p[1], 0) / stroke.length;
    const ndcX = (cx / r.width) * 2 - 1;
    const ndcY = -(cy / r.height) * 2 + 1;
    const anchor = picker.pick ? picker.pick(ndcX, ndcY) : null;
    setPending({ points: stroke, centroidPx: [cx, cy], anchor });
  };

  const confirm = () => {
    if (!pending) return;
    addAnnotation({
      id: genId("ann"),
      intent,
      note: note.trim(),
      screenPoints: pending.points,
      worldAnchorMm: pending.anchor,
      worldNormal: null,
      targetMeshId: project?.meshes[0]?.id ?? null,
      convertedOperationId: null,
    });
    cancel();
  };

  const cancel = () => {
    setPending(null);
    setStroke([]);
    setNote("");
  };

  return (
    <div
      ref={layerRef}
      className="annotation-layer"
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerLeave={onUp}
    >
      <svg className="annotation-svg">
        {stroke.length > 1 && (
          <polyline
            points={stroke.map((p) => p.join(",")).join(" ")}
            fill="none"
            stroke="#ffb300"
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}
        {pending && (
          <circle cx={pending.centroidPx[0]} cy={pending.centroidPx[1]} r={5} fill="#ffb300" />
        )}
      </svg>

      <div className="pencil-hint">✎ Pencil mode — draw over the model, then tag the intent. (Toggle off in the toolbar.)</div>

      {pending && (
        <div
          className="annotation-popover"
          style={{ left: Math.min(pending.centroidPx[0], (layerRef.current?.clientWidth ?? 400) - 260), top: pending.centroidPx[1] + 10 }}
          onPointerDown={(e) => e.stopPropagation()}
        >
          <div className="pop-title">New annotation</div>
          <div className="pop-anchor">
            {pending.anchor ? `anchored at ${pending.anchor.map((v) => v.toFixed(1)).join(", ")} mm` : "not on mesh (free annotation)"}
          </div>
          <select value={intent} onChange={(e) => setIntent(e.target.value as AnnotationIntent)}>
            {INTENTS.map((i) => (
              <option key={i.value} value={i.value}>{i.label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Note (e.g. make a rectangular cooling vent here)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <div className="pop-actions">
            <button onClick={cancel}>Cancel</button>
            <button className="accent" onClick={confirm}>Add annotation</button>
          </div>
        </div>
      )}
    </div>
  );
}
