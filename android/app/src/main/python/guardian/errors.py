# PSE-JOBS GUARDIAN — shared exception types.
class GuardianViolation(Exception):
    """A swarm action tried to cross the host boundary the Guardian enforces
    (write outside the jail, reach a non-allowlisted host, act while tripped)."""
