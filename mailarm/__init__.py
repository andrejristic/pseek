"""PSE-Jobs email arm (robot account; forwards to Proton). Named `mailarm` so it
does not shadow the stdlib `email` module."""
from .robot import RobotMailer, EmailError

__all__ = ["RobotMailer", "EmailError"]
