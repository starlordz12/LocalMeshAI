// Renders one helper-feature preview. When selected, a transform gizmo lets the user move /
// rotate it; the new transform is committed to the store on mouse-up (not mid-drag, to avoid
// state churn). Geometry is rebuilt from the operation's dimensions, so scaling happens via
// the Inspector, keeping mesh.scale at 1 and the exported result exact.

import { useEffect, useMemo, useRef, useState } from "react";
import { TransformControls } from "@react-three/drei";
import * as THREE from "three";
import type { Operation, Vec3 } from "../types/operations";
import type { DisplayMode, GizmoMode } from "../geometry/sceneState";
import { modeColor } from "../geometry/sceneState";
import { buildHelperGeometry, holeMarkers } from "../geometry/helperGeometry";
import { degToRadVec, roundVec, RAD2DEG } from "../geometry/transformUtils";

interface Props {
  op: Operation;
  selected: boolean;
  gizmoMode: GizmoMode;
  displayMode: DisplayMode;
  onSelect: (id: string) => void;
  onCommit: (id: string, patch: Partial<Operation>) => void;
}

export default function HelperMesh({ op, selected, gizmoMode, displayMode, onSelect, onCommit }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  // Re-render once after mount so the gizmo can attach to a populated mesh ref.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const geometry = useMemo(
    () => buildHelperGeometry(op),
    // rebuild when shape-affecting fields change
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [op.feature, op.scaleMm[0], op.scaleMm[1], op.scaleMm[2], JSON.stringify(op.parameters)]
  );
  const markers = useMemo(() => holeMarkers(op), [op.feature, op.scaleMm[0], op.scaleMm[2], JSON.stringify(op.parameters)]);

  const color = modeColor(op.mode);
  const isCut = op.mode === "subtractive";
  const opacity = displayMode === "xray" ? 0.25 : displayMode === "transparent" ? 0.5 : isCut ? 0.55 : 0.92;
  const wireframe = displayMode === "wireframe";

  const rot = degToRadVec(op.rotationDeg);

  const commit = () => {
    const m = meshRef.current;
    if (!m) return;
    const pos = roundVec([m.position.x, m.position.y, m.position.z]);
    const rotDeg = roundVec([m.rotation.x * RAD2DEG, m.rotation.y * RAD2DEG, m.rotation.z * RAD2DEG]) as Vec3;
    onCommit(op.id, { positionMm: pos, rotationDeg: rotDeg });
  };

  const mesh = (
    <mesh
      ref={meshRef}
      geometry={geometry}
      position={op.positionMm}
      rotation={rot}
      visible={!op.suppressed}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(op.id);
      }}
    >
      <meshStandardMaterial
        color={color}
        transparent
        opacity={op.suppressed ? 0.15 : opacity}
        wireframe={wireframe}
        depthWrite={displayMode !== "xray"}
        metalness={0.1}
        roughness={0.75}
        emissive={selected ? new THREE.Color(color) : new THREE.Color("#000000")}
        emissiveIntensity={selected ? 0.25 : 0}
      />
      {markers.map((mk, i) => (
        <mesh key={i} position={mk.position} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[mk.radius, mk.radius, mk.depth * 1.1, 24]} />
          <meshStandardMaterial color="#1b1f27" transparent opacity={0.85} />
        </mesh>
      ))}
    </mesh>
  );

  return (
    <>
      {mesh}
      {selected && !op.suppressed && mounted && meshRef.current && (
        // Control the mesh directly (object mode) so the committed transform reads back
        // from meshRef on mouse-up. Wrapping children would move an internal group instead.
        <TransformControls object={meshRef.current} mode={gizmoMode} onMouseUp={commit} />
      )}
    </>
  );
}
