"""PSE governance kernel — the moat (vendored verbatim from ~/Desktop/pse-kali).

Only the pure-standard-library moat is vendored here: constants, geometry,
scoring, membrane, kernel, audit. The scoring/membrane/kernel files are byte-for-
byte identical to pse-kali (sha256-checked at vendor time) — PSE-Jobs is a new
vertical PACK on this kernel, not a kernel edit. The kali-specific orchestrator,
operator backends and EngagementContext are NOT vendored; PSE-Jobs supplies its
own jobs-domain context and arms.
"""
from .constants import ATTRACTORS, EPSILON, EPSILON_AUTH, VAR_LIMIT
from .audit import AuditLog, NullAudit
from .kernel import evaluate, Decision
from .membrane import Intervention, membrane
from .scoring import score
from .geometry import simplex_dist, nearest_attractor, trajectory_variance

__all__ = [
    "ATTRACTORS", "EPSILON", "EPSILON_AUTH", "VAR_LIMIT",
    "AuditLog", "NullAudit",
    "evaluate", "Decision", "Intervention", "membrane", "score",
    "simplex_dist", "nearest_attractor", "trajectory_variance",
]
