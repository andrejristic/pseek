# =============================================================================
# PSE-JOBS GUARDIAN — FILESYSTEM JAIL
# The swarm may write only inside the PSE-Jobs working directory. Any path that
# resolves (after following symlinks and '..') outside the jail root is refused
# BEFORE the write happens. Reads are allowed from explicitly whitelisted roots
# (e.g. the résumés in ~/Desktop/123) but nowhere else.
# =============================================================================
import os
from .errors import GuardianViolation


def _real(path):
    return os.path.realpath(os.path.abspath(path))


def _within(path, root):
    path, root = _real(path), _real(root)
    return path == root or path.startswith(root + os.sep)


class FSJail:
    def __init__(self, jail_root, read_roots=None):
        self.jail_root = _real(jail_root)
        self.read_roots = [_real(r) for r in (read_roots or [])]

    def guard_write(self, path):
        """Return the resolved path if it is inside the jail; else raise."""
        if not _within(path, self.jail_root):
            raise GuardianViolation(
                f"write blocked: {path!r} resolves outside jail {self.jail_root!r}")
        return _real(path)

    def guard_read(self, path):
        """Reads allowed inside the jail or any explicit read-root; else raise."""
        roots = [self.jail_root] + self.read_roots
        if not any(_within(path, r) for r in roots):
            raise GuardianViolation(
                f"read blocked: {path!r} is outside jail and read-roots")
        return _real(path)
