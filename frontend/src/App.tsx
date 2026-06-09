import { useEffect } from "react";
import Toolbar from "./components/Toolbar";
import ObjectTree from "./components/ObjectTree";
import Viewer3D from "./components/Viewer3D";
import Inspector from "./components/Inspector";
import AIPanel from "./components/AIPanel";
import StatusConsole from "./components/StatusConsole";
import AnnotationLayer from "./components/AnnotationLayer";
import { useStore } from "./store/projectStore";

export default function App() {
  const bootstrap = useStore((s) => s.bootstrap);
  const displayMode = useStore((s) => s.displayMode);
  const setDisplayMode = useStore((s) => s.setDisplayMode);
  const gizmoMode = useStore((s) => s.gizmoMode);
  const setGizmoMode = useStore((s) => s.setGizmoMode);
  const showBounds = useStore((s) => s.showBounds);
  const toggleBounds = useStore((s) => s.toggleBounds);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  return (
    <div className="app">
      <Toolbar />
      <div className="main">
        <ObjectTree />
        <div className="viewport-wrap">
          <Viewer3D />
          <AnnotationLayer />
          <div className="view-overlay">
            <div className="seg">
              {(["solid", "wireframe", "transparent", "xray"] as const).map((m) => (
                <button key={m} className={displayMode === m ? "on" : ""} onClick={() => setDisplayMode(m)}>
                  {m}
                </button>
              ))}
            </div>
            <div className="seg">
              {(["translate", "rotate"] as const).map((m) => (
                <button key={m} className={gizmoMode === m ? "on" : ""} onClick={() => setGizmoMode(m)} title={`Gizmo: ${m}`}>
                  {m === "translate" ? "move" : "rotate"}
                </button>
              ))}
              <button className={showBounds ? "on" : ""} onClick={toggleBounds} title="Toggle bounding box + dimensions">
                bbox
              </button>
            </div>
          </div>
        </div>
        <div className="right-stack">
          <Inspector />
          <AIPanel />
        </div>
      </div>
      <StatusConsole />
    </div>
  );
}
