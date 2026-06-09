"""AI edit planner.

Turns a natural-language request into a **structured, editable plan** (a list of proposed
helper features). It never changes geometry directly — the user reviews the plan, then
chooses to create the helper operations.

Design:
- ``LocalRuleBasedPlanner`` ships and works with **no API key**. It parses common phrases
  and dimensions into operations.
- ``OllamaPlanner`` / ``AnthropicPlanner`` / ``OpenAIPlanner`` are adapter placeholders with
  the same interface. Until configured, they transparently fall back to the rule-based
  planner and add a warning, so the MVP always returns something useful.
"""
from __future__ import annotations

import re
from typing import Optional

import config
from models import PlannedFeature, PlanRequest, PlanResponse, Project
from services import mesh_analyzer, project_store

# --- text parsing helpers --------------------------------------------------------------

_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "single": 1, "pair": 2, "couple": 2,
}

_DIM_TRIPLE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", re.IGNORECASE
)


def _num(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_dimensions(text: str) -> Optional[tuple[float, float, float]]:
    """Return (length_x, width_y, thickness_z) in mm if found, else None."""
    triple = _DIM_TRIPLE.search(text)
    if triple:
        return (float(triple.group(1)), float(triple.group(2)), float(triple.group(3)))

    length = _num(r"(\d+(?:\.\d+)?)\s*mm\s*(?:long|length|in length)", text)
    width = _num(r"(\d+(?:\.\d+)?)\s*mm\s*(?:wide|width|in width)", text)
    thick = _num(r"(\d+(?:\.\d+)?)\s*mm\s*(?:thick|thickness|tall|high|height|deep|depth)", text)
    if any(v is not None for v in (length, width, thick)):
        return (length or 0.0, width or 0.0, thick or 0.0)
    return None


def _parse_count(text: str) -> Optional[int]:
    m = re.search(r"\b(\d+)\b\s*(?:[a-z]+\s+){0,3}?(?:holes?|bosses|boss|tabs?)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    for word, val in _NUM_WORDS.items():
        if re.search(rf"\b{word}\b\s*(?:[a-z]+\s+){{0,3}}?(?:holes?|bosses|boss|tabs?)", text, re.IGNORECASE):
            return val
    return None


def _parse_hole_diameter(text: str) -> Optional[float]:
    # e.g. "2.2 mm pilot holes", "3.2 mm clearance hole", "6 mm hole"
    return _num(r"(\d+(?:\.\d+)?)\s*mm[^.,;]*?\bholes?\b", text) or _num(
        r"(\d+(?:\.\d+)?)\s*mm\s*(?:pilot|clearance|diameter|dia)", text
    )


def _parse_spacing(text: str) -> Optional[float]:
    return _num(r"(\d+(?:\.\d+)?)\s*mm\s*(?:apart|spacing|spaced|between)", text) or _num(
        r"spaced?\s*(\d+(?:\.\d+)?)\s*mm", text
    )


# --- placement heuristics --------------------------------------------------------------


def _placement(text: str, project: Optional[Project], mesh_id: Optional[str]) -> tuple[float, float, float]:
    """Best-effort placement using the target mesh bounding box and directional words."""
    if not project or not mesh_id:
        return (0.0, 0.0, 0.0)
    try:
        info = project_store.get_mesh(project, mesh_id)
        path = project_store.resolve_relative(project.id, info.source_file)
        mesh = mesh_analyzer.load_mesh(path)
    except Exception:
        return (0.0, 0.0, 0.0)

    lo, hi = mesh.bounds
    cx, cy, cz = (lo + hi) / 2.0
    t = text.lower()
    x, y, z = float(cx), float(cy), float(cz)

    if any(w in t for w in ("underside", "bottom", "lower", "belly")):
        z = float(lo[2])
    elif any(w in t for w in ("top", "upper", "over the top")):
        z = float(hi[2])
    if any(w in t for w in ("nose", "front")):
        y = float(hi[1])
    elif any(w in t for w in ("tail", "rear", "back")):
        y = float(lo[1])
    if "left" in t:
        x = float(lo[0])
    elif "right" in t:
        x = float(hi[0])
    return (round(x, 3), round(y, 3), round(z, 3))


# --- feature keyword table -------------------------------------------------------------
# Ordered: more specific phrases first.

_FEATURE_RULES: list[tuple[tuple[str, ...], str, str, tuple[float, float, float]]] = [
    (("cable channel", "wire channel", "wiring channel"), "cable_channel", "subtractive", (40, 4, 4)),
    (("cable guide", "wire guide", "cable clip"), "cable_guide", "additive", (12, 8, 8)),
    (("screw boss", "screw bosses", "boss"), "screw_boss", "additive", (6, 6, 6)),
    (("mounting tab", "mount tab"), "mounting_tab", "additive", (18, 10, 3)),
    (("camera deck", "camera mounting deck", "mounting deck"), "mounting_deck", "additive", (28, 14, 3)),
    (("camera mount", "camera pad", "flat mount", "mounting pad", "mount pad", "flat pad"),
     "mounting_pad", "additive", (28, 14, 3)),
    (("aerodynamic fairing", "aero fairing", "fairing", "aerodynamic", "wedge"),
     "fairing", "additive", (30, 16, 8)),
    (("vent slot", "cooling vent", "vent", "louver", "louvre"), "vent_slot", "subtractive", (25, 2.5, 12)),
    (("rectangular slot", "slot"), "rectangular_slot", "subtractive", (20, 4, 10)),
    (("pocket",), "pocket", "subtractive", (20, 15, 4)),
    (("rectangular cutout", "box cutout", "rectangular cut", "cutout", "cut out", "remove material"),
     "box_cutout", "subtractive", (12, 12, 12)),
    (("clearance hole",), "screw_clearance_hole", "subtractive", (3.2, 3.2, 20)),
    (("drill", "hole", "bore"), "cylinder_hole", "subtractive", (6, 6, 20)),
    (("rib", "gusset"), "rib_gusset", "additive", (15, 15, 3)),
    (("glue plate", "glue-on plate", "glue on plate"), "glue_plate", "additive", (25, 25, 2.5)),
    (("cylinder", "rod", "post"), "cylinder", "additive", (10, 10, 10)),
    (("box", "block", "cube"), "box", "additive", (20, 20, 10)),
]


def _match_feature(text: str) -> Optional[tuple[str, str, tuple[float, float, float]]]:
    t = text.lower()
    for keywords, feature, mode, default_scale in _FEATURE_RULES:
        if any(k in t for k in keywords):
            return feature, mode, default_scale
    return None


# --- planner interface -----------------------------------------------------------------


class Planner:
    name = "base"

    def plan(self, req: PlanRequest, project: Optional[Project]) -> PlanResponse:  # pragma: no cover
        raise NotImplementedError


class LocalRuleBasedPlanner(Planner):
    name = "rule_based"

    def plan(self, req: PlanRequest, project: Optional[Project]) -> PlanResponse:
        text = (req.prompt or "").strip()
        warnings: list[str] = []
        if not text:
            return PlanResponse(
                planner=self.name, summary="Empty prompt — nothing to plan.",
                features=[], warnings=["Describe the change you want, e.g. "
                                       "'add a 28x14x3 mm camera mounting pad with two 2.2 mm holes'."],
            )

        matched = _match_feature(text)
        if not matched:
            return PlanResponse(
                planner=self.name,
                summary="Could not map that request to a known helper feature.",
                features=[],
                warnings=[
                    "Try keywords like: mounting pad, mounting tab, screw boss, cable "
                    "channel, vent, hole, cutout, fairing, rib. Include dimensions in mm "
                    "(e.g. 25x15x3) for an exact size."
                ],
            )

        feature, mode, default_scale = matched
        dims = _parse_dimensions(text)
        scale = tuple(float(d) if d else default_scale[i] for i, d in enumerate(dims)) if dims else default_scale

        params: dict = {}
        count = _parse_count(text)
        hole_d = _parse_hole_diameter(text)
        spacing = _parse_spacing(text)

        if feature in ("mounting_pad", "mounting_deck", "glue_plate"):
            if count:
                params["holeCount"] = count
                params["holeDiameterMm"] = hole_d or config.DEFAULTS["pilot_hole_mm"]
                params["holeSpacingMm"] = spacing or 20.0
        elif feature == "screw_boss":
            params["outerDiameterMm"] = scale[0] if dims else 6.0
            params["holeDiameterMm"] = hole_d or config.DEFAULTS["pilot_hole_mm"]
            params["heightMm"] = scale[2] if dims else 6.0
        elif feature in ("mounting_tab",):
            params["holeDiameterMm"] = hole_d or config.DEFAULTS["m3_clearance_mm"]
        elif feature in ("cylinder_hole", "screw_clearance_hole"):
            params["diameterMm"] = hole_d or (scale[0] if dims else default_scale[0])
        elif feature == "cable_channel":
            params["cableDiameterMm"] = hole_d or _num(r"(\d+(?:\.\d+)?)\s*mm\s*cable", text) or 4.0

        # glue-on intent overrides the mode for additive features.
        glue = any(p in text.lower() for p in ("glue-on", "glue on", "gluean", "separate piece", "glue piece"))
        export_separate = glue
        if glue and mode == "additive":
            mode = "glue_on"

        position = _placement(text, project, req.mesh_id)

        if scale[2] and scale[2] < config.DEFAULTS["min_wall_mm"]:
            warnings.append(
                f"Requested thickness {scale[2]} mm is below the {config.DEFAULTS['min_wall_mm']} "
                "mm minimum-wall guideline."
            )

        rationale_bits = [f"matched feature '{feature}' ({mode})"]
        if dims:
            rationale_bits.append(f"size {scale[0]}x{scale[1]}x{scale[2]} mm")
        if params:
            rationale_bits.append("params " + ", ".join(f"{k}={v}" for k, v in params.items()))

        feat = PlannedFeature(
            name=_friendly_name(feature, glue),
            mode=mode,
            feature=feature,
            position_mm=position,
            rotation_deg=(0.0, 0.0, 0.0),
            scale_mm=scale,
            parameters=params,
            rationale="; ".join(rationale_bits),
        )
        summary = f"Proposed 1 feature: {feat.name}. Review and edit before creating."
        if export_separate:
            warnings.append("Marked as a glue-on / separate piece; it will export as its own STL.")

        return PlanResponse(planner=self.name, summary=summary, features=[feat], warnings=warnings)


def _friendly_name(feature: str, glue: bool) -> str:
    base = feature.replace("_", " ").title()
    return f"{base} (glue-on)" if glue else base


class _FallbackPlaceholder(Planner):
    """Adapter placeholder: not configured yet, falls back to rule-based with a note."""

    backend_name = "placeholder"

    def plan(self, req: PlanRequest, project: Optional[Project]) -> PlanResponse:
        result = LocalRuleBasedPlanner().plan(req, project)
        result.planner = self.name
        result.warnings = [
            f"The '{self.backend_name}' planner is not configured (no credentials/endpoint). "
            "Used the built-in rule-based planner instead."
        ] + result.warnings
        return result


class OllamaPlanner(_FallbackPlaceholder):
    name = "ollama"
    backend_name = "Ollama (local LLM)"


class AnthropicPlanner(_FallbackPlaceholder):
    name = "anthropic"
    backend_name = "Anthropic API"


class OpenAIPlanner(_FallbackPlaceholder):
    name = "openai"
    backend_name = "OpenAI API"


_PLANNERS: dict[str, Planner] = {
    "rule_based": LocalRuleBasedPlanner(),
    "ollama": OllamaPlanner(),
    "anthropic": AnthropicPlanner(),
    "openai": OpenAIPlanner(),
}


def get_planner(name: str) -> Planner:
    return _PLANNERS.get(name, _PLANNERS["rule_based"])


def plan(req: PlanRequest, project: Optional[Project]) -> PlanResponse:
    return get_planner(req.planner).plan(req, project)
