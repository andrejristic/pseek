# =============================================================================
# PSEEK — θ (THETA): self/other allocation
# From the PSE corpus: θ measures how much of the state is allocated to the OTHER
# vs the SELF, with a healthy band of [25, 35] (optimum 30 ≈ the 70/30 self/other
# split). Read off the simplex state: the pull toward the two active corners is
# w_s (over-self / Narcissistic) vs w_o (over-other / Codependent); θ is the
# other's share of that pull. θ < 25 → too self-centred (Narcissistic-lean);
# θ > 35 → too other-centred (Codependent-lean); in-band → healthy. A purely
# field-anchored state (no pathological pull) reads as optimal.
# =============================================================================
THETA_MIN = 25.0
THETA_OPT = 30.0
THETA_MAX = 35.0


def theta_from_state(state):
    """θ centred at the optimum 30, moved by the NET pull toward the other (w_o,
    Codependent) vs the self (w_s, Narcissistic). A field-anchored honest state
    (w_s≈w_o≈0) reads ~30 (healthy); growing w_o pushes θ up (Codependent-lean);
    growing w_s pushes θ down (Narcissistic-lean). Band [25,35] ⟺ |w_o−w_s| ≤ 0.1."""
    w_s, w_o, w_f = state
    return max(0.0, min(100.0, THETA_OPT + 50.0 * (w_o - w_s)))


def in_band(theta):
    return THETA_MIN <= theta <= THETA_MAX


def band_label(theta):
    if theta < THETA_MIN:
        return "narcissistic-lean (previše self)"
    if theta > THETA_MAX:
        return "codependent-lean (previše other)"
    return "healthy"


def correction(theta):
    """How to rebalance a combination whose θ has left the band."""
    if theta < THETA_MIN:
        return ("Naginje previše ka sebi (over-reach). Uključi više onoga što "
                "uloga stварno traži — smanji naduvavanje, digni relevantnost.")
    if theta > THETA_MAX:
        return ("Naginje previše ka poslodavcu (izvrtanje). Vrati svoj autentični "
                "profil — manje krojenja pod wishlistu.")
    return None


class ThetaEngine:
    """Tracks θ across a session for the gauge, and advises rebalancing."""
    def __init__(self):
        self.history = []

    def reading(self, state):
        th = theta_from_state(state)
        self.history.append(th)
        return {"theta": round(th, 1), "band": band_label(th),
                "in_band": in_band(th), "optimum": THETA_OPT,
                "correction": correction(th)}

    def average(self):
        return round(sum(self.history) / len(self.history), 1) if self.history else THETA_OPT

    def reset(self):
        self.history = []
