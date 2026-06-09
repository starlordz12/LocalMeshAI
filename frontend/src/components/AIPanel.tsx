// AI panel: describe a change, generate a structured (editable) plan, review it, then create
// helper operations from it. The plan never changes geometry directly — the user creates the
// features explicitly. Works with no API key via the rule-based planner.

import { useState } from "react";
import { useStore } from "../store/projectStore";

const EXAMPLES = [
  "add a 28x14x3 mm camera mounting pad with two 2.2 mm pilot holes spaced 20 mm apart",
  "cut a 6 mm hole",
  "make a cable channel",
  "add a mounting tab as a glue-on piece",
  "add an aerodynamic fairing on the underside",
];

export default function AIPanel() {
  const [prompt, setPrompt] = useState("");
  const [planner, setPlanner] = useState("rule_based");
  const plan = useStore((s) => s.plan);
  const busy = useStore((s) => s.busy);
  const runPlan = useStore((s) => s.runPlan);
  const addPlannedFeature = useStore((s) => s.addPlannedFeature);
  const clearPlan = useStore((s) => s.clearPlan);

  const createAll = () => {
    plan?.features.forEach((f) => addPlannedFeature(f));
    clearPlan();
  };

  return (
    <div className="ai-panel">
      <div className="panel-subtitle">AI Edit Planner</div>

      <textarea
        className="ai-prompt"
        placeholder="Describe what you want changed…"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
      />

      <div className="ai-controls">
        <select value={planner} onChange={(e) => setPlanner(e.target.value)} title="Planner backend">
          <option value="rule_based">Rule-based (offline)</option>
          <option value="ollama">Ollama (placeholder)</option>
          <option value="anthropic">Anthropic (placeholder)</option>
          <option value="openai">OpenAI (placeholder)</option>
        </select>
        <button className="accent" disabled={busy || !prompt.trim()} onClick={() => runPlan(prompt, planner)}>
          Generate Edit Plan
        </button>
      </div>

      <div className="ai-examples">
        {EXAMPLES.map((ex) => (
          <button key={ex} className="chip" onClick={() => setPrompt(ex)} title="Use example">
            {ex.length > 28 ? ex.slice(0, 28) + "…" : ex}
          </button>
        ))}
      </div>

      {plan && (
        <div className="ai-plan">
          <div className="ai-plan-head">
            <b>Plan ({plan.planner})</b>
            <button className="icon-btn" onClick={clearPlan} title="Dismiss">✕</button>
          </div>
          <div className="ai-plan-summary">{plan.summary}</div>
          {plan.features.map((f, i) => (
            <div key={i} className="ai-feature">
              <div className="ai-feature-name">{f.name} <span className="pill">{f.mode}</span></div>
              <div className="ai-feature-detail">
                {f.feature.replace(/_/g, " ")} · size {f.scaleMm.join("×")} mm
                {Object.keys(f.parameters).length > 0 && (
                  <> · {Object.entries(f.parameters).map(([k, v]) => `${k}=${v}`).join(", ")}</>
                )}
              </div>
              {f.rationale && <div className="ai-feature-why">{f.rationale}</div>}
            </div>
          ))}
          {plan.warnings.map((w, i) => (
            <div key={i} className="ai-warn">⚠ {w}</div>
          ))}
          {plan.features.length > 0 && (
            <button className="full accent" onClick={createAll}>
              Create Helper Features From Plan
            </button>
          )}
        </div>
      )}
    </div>
  );
}
