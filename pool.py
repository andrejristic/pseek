# =============================================================================
# PSEEK — DOCUMENT POOL
# The user's raw material: as many résumés and cover letters as they want (dropped
# into their workspace, or generated conversationally). Résumés parse to citable
# lines; cover letters to paragraphs. The pool is the ground truth the
# Combinatorial Synthesis Engine draws from — it may select and arrange, never
# invent, so the truthfulness floor holds.
# =============================================================================
import os
import re
from dataclasses import dataclass, field

from jobs.domain import ResumeLine, Profile, tokens
from jobs.loaders import docx_text, pdf_text, _clean_lines


def _read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return docx_text(path)
    if ext == ".pdf":
        return pdf_text(path)
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def classify(filename, text):
    f = filename.lower()
    if "cover" in f or "letter" in f:
        return "cover"
    if "resume" in f or "cv" in f or "cirriculum" in f or "curriculum" in f:
        return "resume"
    # heuristic: a cover letter is prose that greets someone
    return "cover" if re.search(r"\bdear\b|hiring team|to whom", text.lower()) else "resume"


@dataclass
class ResumeDoc:
    doc_id: str
    name: str
    lines: list = field(default_factory=list)     # ResumeLine


@dataclass
class CoverDoc:
    doc_id: str
    name: str
    paragraphs: list = field(default_factory=list)  # (para_id, text)


@dataclass
class DocumentPool:
    resumes: list = field(default_factory=list)
    covers: list = field(default_factory=list)

    def all_lines(self):
        return [ln for r in self.resumes for ln in r.lines]

    def as_profile(self):
        """One profile over every résumé line, so any cited line resolves for the
        truthfulness check regardless of which résumé it came from."""
        return Profile("pool", "Document Pool", self.all_lines())

    def resume(self, doc_id):
        return next((r for r in self.resumes if r.doc_id == doc_id), None)

    def cover(self, doc_id):
        return next((c for c in self.covers if c.doc_id == doc_id), None)

    def summary(self):
        return {"resumes": len(self.resumes), "covers": len(self.covers),
                "lines": len(self.all_lines())}


def add_resume(pool, name, text):
    did = f"r{len(pool.resumes) + 1}"
    lines = [ResumeLine(f"{did}:{i:03d}", ln, did)
             for i, ln in enumerate(_clean_lines(text))]
    pool.resumes.append(ResumeDoc(did, name, lines))
    return pool.resumes[-1]


def add_cover(pool, name, text):
    did = f"c{len(pool.covers) + 1}"
    paras = [(f"{did}:{i}", re.sub(r"\s+", " ", p).strip())
             for i, p in enumerate(re.split(r"\n\s*\n", text))
             if len(p.strip()) > 40]
    pool.covers.append(CoverDoc(did, name, paras))
    return pool.covers[-1]


def load_pool(docs_dir, guardian=None):
    """Scan a workspace docs/ directory; classify + parse every file."""
    pool = DocumentPool()
    if not os.path.isdir(docs_dir):
        return pool
    for fn in sorted(os.listdir(docs_dir)):
        path = os.path.join(docs_dir, fn)
        if not os.path.isfile(path):
            continue
        if guardian is not None:
            guardian.guard_read(path)
        text = _read_text(path)
        if classify(fn, text) == "cover":
            add_cover(pool, fn, text)
        else:
            add_resume(pool, fn, text)
    return pool
