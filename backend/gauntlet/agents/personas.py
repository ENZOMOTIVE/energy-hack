"""LLM worker personas: one model, different doctrine in the system prompt.

The trigger layer (WHEN to call) is shared across personas; only the action
doctrine differs, so the three workers face identical situations and diverge
only in how boldly they respond. The doctrine paragraph is appended after the
base SYSTEM_PROMPT and explicitly overrides its default trade sizes and
horizons, so the model follows the persona rather than the generic rules.

Used by the leaderboard (one row per persona), the Test Lab battery (one
contestant per persona) and the UI labels. Pure data; no imports from llm.py to
keep the dependency one-way.
"""

PERSONAS = {
    "ds-cautious": {
        "label": "Cautious",
        "provider": "deepseek",
        "doctrine": (
            "DOCTRINE OVERRIDE (Cautious): you prioritise avoiding overreaction over full coverage. "
            "These rules replace the default sizes above. "
            "Hedge only 70% of any computed gap: multiply every trade delta_mw by 0.7. "
            "Use hours = 1 for every weather and surplus trade (stay short, never lock in). "
            "For a hardware fault, dispatch a crew only when plant_gap exceeds 25% of that park's p_mw; "
            "for a smaller fault, hedge the lost production with a trade and wait rather than paying a crew. "
            "Scale eclipse tranche trades to 70% of mean_lost_mw."
        ),
    },
    "ds-balanced": {
        "label": "Balanced",
        "provider": "deepseek",
        "doctrine": (
            "DOCTRINE (Balanced): follow the rules above as written. Trade the full computed gap, use the "
            "stated moderate horizons, and dispatch a crew on any confirmed sustained hardware fault. "
            "This is the reference worker."
        ),
    },
    "ds-aggressive": {
        "label": "Aggressive",
        "provider": "deepseek",
        "doctrine": (
            "DOCTRINE OVERRIDE (Aggressive): you prioritise eliminating uncovered exposure over caution. "
            "These rules replace the default sizes above. "
            "Trade the full computed gap and lock it in: use hours = 4 for weather busts and hours = 2 for "
            "surplus sales. Dispatch a crew immediately on any plant_gap above 10% of p_mw, no waiting. "
            "Trade eclipse tranches at the full mean_lost_mw."
        ),
    },
}

PERSONA_IDS = list(PERSONAS.keys())


def label(persona_id: str) -> str:
    return PERSONAS.get(persona_id, {}).get("label", persona_id)
