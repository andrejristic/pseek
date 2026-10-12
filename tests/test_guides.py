# =============================================================================
# PSEEK — P15 TESTS: guides exist EN + SR for each of the 4 outputs (+ email)
# =============================================================================
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, "guides")
RESULTS = []
def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")

def test_all_output_guides_present():
    outputs = ["SOURCE", "DEB", "EXE", "APP"]
    missing = []
    for o in outputs:
        for lang in ("EN", "SR"):
            f = os.path.join(G, f"INSTALL-{o}-{lang}.md")
            if not (os.path.exists(f) and os.path.getsize(f) > 200):
                missing.append(os.path.basename(f))
    check("EN + SR install guide for each of the 4 outputs", not missing, str(missing))

def test_connect_email_guides_present():
    ok = all(os.path.exists(os.path.join(G, f"CONNECT-EMAIL-{l}.md")) for l in ("EN", "SR"))
    check("connect-email guide EN + SR present (P9)", ok)


def test_using_and_golive_guides_present_and_current():
    missing = []
    for base in ("USING", "GO-LIVE"):
        for lang in ("EN", "SR"):
            f = os.path.join(G, f"{base}-{lang}.md")
            if not (os.path.exists(f) and os.path.getsize(f) > 400):
                missing.append(f"{base}-{lang}")
    check("USING + GO-LIVE guides present EN + SR", not missing, str(missing))
    # USING must reflect the current features (chat commands, apply, opt-in)
    txt = open(os.path.join(G, "USING-EN.md")).read()
    check("USING reflects current features (nađi poslove/Apliciraj/opt-in)",
          "nađi poslove" in txt and "Apliciraj" in txt and "Auto-pretraga" in txt)
    # install guides point to USING/GO-LIVE
    src = open(os.path.join(G, "INSTALL-SOURCE-EN.md")).read()
    check("install guides point to USING + GO-LIVE",
          "USING-EN.md" in src and "GO-LIVE-EN.md" in src)

def test_readme_present():
    check("README documents the 4 outputs + pricing",
          os.path.exists(os.path.join(ROOT, "README.md"))
          and "Four distribution outputs" in open(os.path.join(ROOT, "README.md")).read())

ALL = [test_all_output_guides_present, test_connect_email_guides_present,
       test_using_and_golive_guides_present_and_current, test_readme_present]
if __name__ == "__main__":
    print("PSEEK · P15 guides tests\n" + "=" * 44)
    for t in ALL:
        print(f"\n{t.__name__}:"); t()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 44); print(f"{passed}/{len(RESULTS)} checks green")
    sys.exit(0 if passed == len(RESULTS) else 1)
