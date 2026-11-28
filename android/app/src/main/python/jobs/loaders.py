# =============================================================================
# PSE-JOBS — RÉSUMÉ LOADERS (build the two self-models from the real files)
# Pure stdlib, zero third-party deps: DOCX via zipfile+XML, PDF via a minimal
# FlateDecode (zlib) + text-operator (Tj/TJ) extractor. Good enough to recover
# the résumé's words and line structure, which is all the fit-scorer and the
# truthfulness floor need. Reads go through the Guardian when one is supplied, so
# even loading a résumé obeys the filesystem jail / read-roots.
# =============================================================================
import html
import json
import os
import re
import zipfile
import zlib

from .domain import ResumeLine, Profile


# ---- DOCX ------------------------------------------------------------------
def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)          # paragraph -> newline
    xml = re.sub(r"<[^>]+>", "", xml)           # strip all tags
    return html.unescape(xml)


# ---- PDF (minimal, stdlib only) -------------------------------------------
def _pdf_unescape(s):
    s = re.sub(r"\\([nrtbf()\\])",
               lambda m: {"n": "\n", "r": "\r", "t": "\t", "b": "\b",
                          "f": "\f", "(": "(", ")": ")", "\\": "\\"}[m.group(1)], s)
    s = re.sub(r"\\([0-7]{1,3})", lambda m: chr(int(m.group(1), 8)), s)
    return s

def _hex_to_unicode(h):
    return "".join(chr(int(h[i:i + 4], 16)) for i in range(0, len(h) - 3, 4))

def _parse_cmaps(cmap_sources):
    """Build glyph-code -> Unicode from every ToUnicode CMap in the file.
    Résumé PDFs subset their fonts and ship a ToUnicode map; without it the
    hex glyph IDs are meaningless. Combined across fonts (fine for a résumé)."""
    cmap = {}
    for s in cmap_sources:
        for blk in re.findall(r"beginbfchar(.*?)endbfchar", s, re.S):
            for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                cmap[int(a, 16)] = _hex_to_unicode(b)
        for blk in re.findall(r"beginbfrange(.*?)endbfrange", s, re.S):
            for m in re.finditer(
                    r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]+>)",
                    blk, re.S):
                start, end, dst = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
                if dst.startswith("["):
                    for i, u in enumerate(re.findall(r"<([0-9A-Fa-f]+)>", dst)):
                        cmap[start + i] = _hex_to_unicode(u)
                else:
                    base = int(dst.strip("<>"), 16)
                    for i in range(end - start + 1):
                        cmap[start + i] = chr(base + i)
    return cmap

def _decode_hex(h, cmap):
    h = re.sub(r"\s", "", h)
    return "".join(cmap.get(int(h[i:i + 4], 16), "") for i in range(0, len(h) - 3, 4))

def _content_to_text(content, fontmaps, default_cmap):
    s = content.decode("latin-1", "ignore")
    out, cur = [], default_cmap
    # Each visual line is positioned by a Tm/Td and shown with Tj/TJ; the active
    # font is selected by `/Fxx <size> Tf`. Decode each run with ITS font's map
    # (glyph codes are font-local) and break lines on the positioning operators.
    for chunk in re.split(r"(/F\w+\s+[\d.]+\s+Tf|Tm|T\*|Td|TD|TJ|Tj|ET|BT)", s):
        fm = re.match(r"/(F\w+)\s+[\d.]+\s+Tf", chunk)
        if fm:
            cur = fontmaps.get(fm.group(1), default_cmap)
            continue
        for m in re.finditer(r"<([0-9A-Fa-f\s]+)>|\((?:[^()\\]|\\.)*\)", chunk):
            tok = m.group(0)
            if tok.startswith("<"):
                out.append(_decode_hex(m.group(1), cur))
            else:
                out.append(_pdf_unescape(tok[1:-1]))
        if chunk in ("Tm", "T*", "Td", "TD", "ET"):
            out.append("\n")
    return "".join(out)

def _is_content_stream(dec):
    """A page content stream shows text (BT..ET with Tj/TJ) and is mostly ASCII.
    Embedded fonts/images decompress to binary and are rejected here."""
    if b"BT" not in dec or (b"Tj" not in dec and b"TJ" not in dec):
        return False
    printable = sum(1 for c in dec if c in (9, 10, 13) or 32 <= c <= 126)
    return printable / max(1, len(dec)) > 0.85

def _pdf_objects(data):
    """Return (obj_bodies:str by num, streams:bytes by num) for classic
    `N 0 obj ... endobj` objects, decompressing each object's flate stream."""
    bodies, streams = {}, {}
    for m in re.finditer(rb"(\d+)\s+0\s+obj(.*?)endobj", data, re.S):
        num, body = int(m.group(1)), m.group(2)
        bodies[num] = body.decode("latin-1", "ignore")
        sm = re.search(rb"stream\r?\n", body)
        if sm:
            end = body.find(b"endstream", sm.end())
            raw = body[sm.end():end].rstrip(b"\r\n")
            try:
                streams[num] = zlib.decompress(raw)
            except Exception:
                pass
    return bodies, streams

def _pdf_fontmaps(data, streams, bodies):
    """Map each font resource name (F52, ...) to its ToUnicode CMap, via
    /Resources /Font << /F52 52 0 R >> -> obj 52 /ToUnicode 60 0 R -> obj 60."""
    text = data.decode("latin-1", "ignore")
    name2obj = {}
    for fontdict in re.findall(r"/Font\s*<<(.*?)>>", text, re.S):
        for name, num in re.findall(r"/(F\w+)\s+(\d+)\s+0\s+R", fontdict):
            name2obj[name] = int(num)
    fontmaps = {}
    for name, objnum in name2obj.items():
        m = re.search(r"/ToUnicode\s+(\d+)\s+0\s+R", bodies.get(objnum, ""))
        if m and int(m.group(1)) in streams:
            fontmaps[name] = _parse_cmaps(
                [streams[int(m.group(1))].decode("latin-1", "ignore")])
    return fontmaps

def pdf_text(path):
    with open(path, "rb") as fh:
        data = fh.read()
    bodies, streams = _pdf_objects(data)
    fontmaps = _pdf_fontmaps(data, streams, bodies)
    # a merged map as a fallback when a run's font can't be resolved
    default = {}
    for cm in fontmaps.values():
        default.update(cm)
    parts = [_content_to_text(d, fontmaps, default)
             for d in streams.values() if _is_content_stream(d)]
    return "\n".join(parts)


# ---- text -> Profile -------------------------------------------------------
def _clean_lines(text, min_tokens=3):
    """Keep substantive lines (>= min_tokens content words), de-duplicated."""
    seen, lines = set(), []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip(" \t•·-–—●•")
        if not line:
            continue
        words = re.findall(r"[A-Za-z0-9+#]+", line)
        if len(words) < min_tokens:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return lines

def profile_from_text(text, key, name):
    lines = [ResumeLine(f"{key}:{i:04d}", ln, key)
             for i, ln in enumerate(_clean_lines(text))]
    return Profile(key, name, lines)

def load_profile(path, key, name, guardian=None):
    if guardian is not None:
        guardian.guard_read(path)              # obey the jail / read-roots
    ext = os.path.splitext(path)[1].lower()
    text = docx_text(path) if ext == ".docx" else pdf_text(path)
    return profile_from_text(text, key, name)


# Andrej's two files, established earlier: docx = coding, pdf = teaching.
ANDREJ_FILES = {
    "coding":   ("Andrej_Ristic_Resume.docx", "AI Engineer & Researcher"),
    "teaching": ("Andrej Ristic Resume.pdf",  "Mathematics & CS Teacher"),
}

def load_andrej_profiles(dir_123, guardian=None):
    profiles = {}
    for key, (fname, name) in ANDREJ_FILES.items():
        profiles[key] = load_profile(os.path.join(dir_123, fname), key, name, guardian)
    return profiles


# ---- persistence (registry) — profiles are self-models that grow -----------
def save_profiles(profiles, registry_dir):
    os.makedirs(registry_dir, exist_ok=True)
    for key, p in profiles.items():
        obj = {"key": p.key, "name": p.name,
               "lines": [{"line_id": ln.line_id, "text": ln.text} for ln in p.lines]}
        with open(os.path.join(registry_dir, f"profile_{key}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)

def load_profiles(registry_dir):
    profiles = {}
    for fn in sorted(os.listdir(registry_dir)):
        if fn.startswith("profile_") and fn.endswith(".json"):
            with open(os.path.join(registry_dir, fn), encoding="utf-8") as fh:
                obj = json.load(fh)
            lines = [ResumeLine(l["line_id"], l["text"], obj["key"]) for l in obj["lines"]]
            profiles[obj["key"]] = Profile(obj["key"], obj["name"], lines)
    return profiles
