"""A test case as a parameter vector (the 'genome' of a bad day).

A genome fully specifies one stress day: zero or more weather busts (the
realized weather diverging from the day-ahead forecast), an optional silent
hardware fault, an optional eclipse overlay, and a price regime. genome.py only
holds the data plus sampling, mutation, feature and label logic; turning a
genome into a runnable Scenario lives in scenarios.build_from_genome (one-way
dependency, no import cycle).

Every bound here is a realism guardrail: sampled genomes are physically and
economically plausible days by construction, so the generator never wastes its
search budget on nonsense.
"""

from dataclasses import dataclass, field, replace

import numpy as np

from .config import N_STEPS, PARK_IDS

# realism guardrails (steps are 15-min indices, 0..95)
DAY_LO, DAY_HI = 28, 82          # daylight band where production is worth disturbing
BUST_DEPTH_LO, BUST_DEPTH_HI = 0.20, 0.70   # fraction of output removed at the trough
BUST_DUR_LO, BUST_DUR_HI = 4, 24            # 1 h to 6 h
FAULT_MAG_LO, FAULT_MAG_HI = 0.15, 0.55
FAULT_ONSET_LO, FAULT_ONSET_HI = 30, 76
SPIKE_LO, SPIKE_HI = 1.0, 1.8
ECLIPSE_PROB = 0.08
FAULT_PROB = 0.55
N_BUST_WEIGHTS = (0.18, 0.57, 0.25)   # P(0), P(1), P(2) busts
MAX_BUSTS = 2


@dataclass
class Bust:
    park: str
    start: int
    end: int
    depth: float   # fraction removed at trough, 0..1
    sign: int      # +1 shortfall (realized worse), -1 surplus (realized better)


@dataclass
class Fault:
    park: str
    onset: int
    magnitude: float


@dataclass
class CaseGenome:
    busts: list = field(default_factory=list)
    fault: Fault | None = None
    eclipse: bool = False
    price_spike: float = 1.0

    # ---- identity / caching ----
    def key(self) -> tuple:
        bk = tuple(sorted((b.park, b.start, b.end, round(b.depth, 3), b.sign) for b in self.busts))
        fk = (self.fault.park, self.fault.onset, round(self.fault.magnitude, 3)) if self.fault else None
        return (bk, fk, self.eclipse, round(self.price_spike, 3))

    # ---- sampling ----
    @staticmethod
    def sample(rng: np.random.Generator) -> "CaseGenome":
        n = int(rng.choice(MAX_BUSTS + 1, p=N_BUST_WEIGHTS))
        busts = [_sample_bust(rng) for _ in range(n)]
        fault = _sample_fault(rng) if rng.random() < FAULT_PROB else None
        eclipse = bool(rng.random() < ECLIPSE_PROB)
        spike = 1.0 if rng.random() < 0.5 else float(rng.uniform(SPIKE_LO, SPIKE_HI))
        return CaseGenome(busts=busts, fault=fault, eclipse=eclipse, price_spike=spike)

    def mutate(self, rng: np.random.Generator) -> "CaseGenome":
        """One genome a small edit away: tweak a gene, add/drop a bust, toggle the fault."""
        g = replace(self, busts=[replace(b) for b in self.busts],
                    fault=replace(self.fault) if self.fault else None)
        move = rng.integers(6)
        if move == 0 and g.busts:            # nudge a bust
            b = g.busts[rng.integers(len(g.busts))]
            b.depth = float(np.clip(b.depth + rng.normal(0, 0.08), BUST_DEPTH_LO, BUST_DEPTH_HI))
            shift = int(rng.integers(-6, 7))
            b.start = int(np.clip(b.start + shift, DAY_LO, DAY_HI - BUST_DUR_LO))
            b.end = int(np.clip(b.end + shift, b.start + BUST_DUR_LO, DAY_HI))
        elif move == 1 and len(g.busts) < MAX_BUSTS:   # add a bust
            g.busts.append(_sample_bust(rng))
        elif move == 2 and g.busts:          # drop a bust
            g.busts.pop(int(rng.integers(len(g.busts))))
        elif move == 3 and g.busts:          # flip a bust's sign
            g.busts[rng.integers(len(g.busts))].sign *= -1
        elif move == 4:                      # toggle / move the fault
            g.fault = None if g.fault else _sample_fault(rng)
            if g.fault and rng.random() < 0.5:
                g.fault.magnitude = float(np.clip(g.fault.magnitude + rng.normal(0, 0.08),
                                                  FAULT_MAG_LO, FAULT_MAG_HI))
        else:                                # price regime
            g.price_spike = 1.0 if rng.random() < 0.4 else float(rng.uniform(SPIKE_LO, SPIKE_HI))
        return g

    def jitter(self, rng: np.random.Generator) -> "CaseGenome":
        """A near-copy for Monte-Carlo stability around a fixed case (structure held)."""
        busts = []
        for b in self.busts:
            d = float(np.clip(b.depth + rng.normal(0, 0.04), BUST_DEPTH_LO, BUST_DEPTH_HI))
            s = int(np.clip(b.start + rng.integers(-2, 3), DAY_LO, DAY_HI - BUST_DUR_LO))
            e = int(np.clip(b.end + rng.integers(-2, 3), s + BUST_DUR_LO, DAY_HI))
            busts.append(Bust(b.park, s, e, d, b.sign))
        fault = None
        if self.fault:
            fault = Fault(self.fault.park,
                          int(np.clip(self.fault.onset + rng.integers(-2, 3), FAULT_ONSET_LO, FAULT_ONSET_HI)),
                          float(np.clip(self.fault.magnitude + rng.normal(0, 0.04), FAULT_MAG_LO, FAULT_MAG_HI)))
        return CaseGenome(busts=busts, fault=fault, eclipse=self.eclipse, price_spike=self.price_spike)

    # ---- diversity ----
    def feature_vector(self) -> np.ndarray:
        sev = sum(b.depth * (b.end - b.start) for b in self.busts) / (BUST_DEPTH_HI * BUST_DUR_HI * MAX_BUSTS)
        mids = [(b.start + b.end) / 2 for b in self.busts]
        centroid = (np.mean(mids) / N_STEPS) if mids else 0.0
        return np.array([
            len(self.busts) / MAX_BUSTS,
            min(1.0, sev),
            sum(1 for b in self.busts if b.sign > 0) / MAX_BUSTS,
            sum(1 for b in self.busts if b.sign < 0) / MAX_BUSTS,
            centroid,
            1.0 if self.fault else 0.0,
            (self.fault.magnitude / FAULT_MAG_HI) if self.fault else 0.0,
            (self.fault.onset / N_STEPS) if self.fault else 0.0,
            1.0 if self.eclipse else 0.0,
            (self.price_spike - 1.0) / (SPIKE_HI - 1.0),
        ])

    # ---- coarse failure-mode category (for grouping in the comparison graphs) ----
    def category(self) -> str:
        """One of ECLIPSE | COMBO | FAULT | WEATHER | CALM.

        Eclipse is the defining skill when present; otherwise a day with both a
        fault and a weather bust is a COMBO (you must disentangle them)."""
        if self.eclipse:
            return "ECLIPSE"
        if self.fault and self.busts:
            return "COMBO"
        if self.fault:
            return "FAULT"
        if self.busts:
            return "WEATHER"
        return "CALM"

    # ---- human-readable failure-mode tag ----
    def label(self) -> str:
        parts = []
        if self.fault:
            parts.append(f"silent fault ({_short(self.fault.park)} {int(self.fault.magnitude*100)}%, "
                         f"{_hhmm(self.fault.onset)})")
        for b in self.busts:
            kind = "missed cloud bank" if b.sign > 0 else "under-forecast sun"
            parts.append(f"{kind} ({_short(b.park)}, {_tod((b.start + b.end)//2)})")
        if self.eclipse:
            parts.append("eclipse overlay")
        if not parts:
            return "calm day"
        tag = " + ".join(parts)
        if self.price_spike >= 1.2:
            tag += " on a high-evening-price day"
        return tag


def _sample_bust(rng: np.random.Generator) -> Bust:
    park = PARK_IDS[int(rng.integers(len(PARK_IDS)))]
    dur = int(rng.integers(BUST_DUR_LO, BUST_DUR_HI + 1))
    start = int(rng.integers(DAY_LO, DAY_HI - dur + 1))
    depth = float(rng.uniform(BUST_DEPTH_LO, BUST_DEPTH_HI))
    sign = 1 if rng.random() < 0.65 else -1   # shortfalls more common than surprise sun
    return Bust(park, start, start + dur, depth, sign)


def _sample_fault(rng: np.random.Generator) -> Fault:
    park = PARK_IDS[int(rng.integers(len(PARK_IDS)))]
    onset = int(rng.integers(FAULT_ONSET_LO, FAULT_ONSET_HI + 1))
    return Fault(park, onset, float(rng.uniform(FAULT_MAG_LO, FAULT_MAG_HI)))


def _short(park: str) -> str:
    return park.capitalize()


def _hhmm(step: int) -> str:
    return f"{int(step * 0.25):02d}:{int(step * 15 % 60):02d}"


def _tod(step: int) -> str:
    h = step * 0.25
    if h < 11:
        return "morning"
    if h < 15:
        return "midday"
    if h < 18:
        return "afternoon"
    return "evening"
