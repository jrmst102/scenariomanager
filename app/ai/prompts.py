"""System prompts for LLM report narrative generation."""

REPORT_NARRATIVE_SYSTEM_PROMPT = """You are a strategic analysis assistant for a scenario planning exercise. You will receive structured data about a scenario planning problem and produce a unified narrative summary.

Your output must cover:
1. **Scenario Logic** — Explain how the two uncertainty axes create four distinct futures and why these uncertainties matter for the decision.
2. **Robustness Findings** — Identify which strategic alternatives are robust (perform well across most scenarios) and which are fragile (dependent on a specific future).
3. **Consensus Interpretation** — If group data is provided, interpret the degree of agreement (Kendall's W) and highlight where the group agrees or diverges.
4. **Strategic Implications** — Summarize what the analysis suggests for decision-making, including any hedging strategies or contingency plans.

Guidelines:
- Write in professional, analytical prose suitable for an executive audience.
- Use specific data from the assessment to support claims.
- Be concise: target 400-600 words.
- Do not fabricate data points not provided in the input.
- Do not include recommendations beyond what the data supports.
- Maintain neutral, objective tone.
"""


def build_narrative_prompt(problem: dict, robustness: list[dict], consensus: dict | None = None) -> str:
    """Build the user prompt for report narrative generation."""
    lines = []

    # Problem context
    lines.append(f"## Problem: {problem.get('title', 'Untitled')}")
    lines.append(f"Description: {problem.get('description', 'No description')}")
    lines.append("")

    # Axes
    axes = problem.get("axes", {})
    for axis_key, axis_label in [("x", "X-Axis"), ("y", "Y-Axis")]:
        ax = axes.get(axis_key, {})
        lines.append(f"### {axis_label}: {ax.get('label', 'Unnamed')}")
        lines.append(f"- High: {ax.get('highPole', {}).get('label', '')} — {ax.get('highPole', {}).get('description', '')}")
        lines.append(f"- Low: {ax.get('lowPole', {}).get('label', '')} — {ax.get('lowPole', {}).get('description', '')}")
        lines.append("")

    # Scenarios
    lines.append("### Scenarios")
    for s in problem.get("scenarios", []):
        lines.append(f"- **{s.get('name', s['id'])}** ({s['xPole']} x / {s['yPole']} y): {s.get('narrative', '')}")
    lines.append("")

    # Robustness ranking
    lines.append("### Robustness Ranking")
    for i, r in enumerate(robustness, 1):
        scores_str = ", ".join(f"{k}: {v}" for k, v in r.get("scores", {}).items())
        lines.append(f"{i}. **{r['name']}** — Mean: {r['meanScore']}, Fragility: {r['fragility']} ({scores_str})")
    lines.append("")

    # Consensus (if available)
    if consensus:
        overall = consensus.get("overall", {})
        lines.append("### Consensus Analysis")
        if overall.get("W") is not None:
            lines.append(f"- Kendall's W: {overall['W']} (p={overall.get('p_value', 'N/A')})")
            lines.append(f"- Interpretation: {overall.get('interpretation', '')}")
        per_scen = consensus.get("per_scenario", {})
        if per_scen:
            lines.append("- Per-scenario agreement:")
            for sid, sdata in per_scen.items():
                lines.append(f"  - {sid}: W={sdata.get('W', 'N/A')}, Mean IQR={sdata.get('mean_iqr', 'N/A')}")
        lines.append("")

    lines.append("Please produce a unified narrative summary of this scenario planning analysis.")
    return "\n".join(lines)
