"""Flag style problems in thesis prose: ', and', em dashes, marker words,
long sentences, and runs of short (choppy) sentences.

Usage: python3 check_style.py FILE [FILE ...]
Skips headings, list items, tables, and everything after '## References'.
"""
import re
import sys

MARKERS = ["delve", "crucial", "pivotal", "landscape", "tapestry", "seamless",
           "leverage", "notably", "furthermore", "it is worth noting",
           "plays a vital role", "in the realm of", ", that is,",
           "game content"]
LONG, SHORT, RUN = 30, 12, 3
CITE = re.compile(r"\[(?:@[\w;\s@]+|\d+(?:\]\s*,\s*\[\d+)*)\]")
SPLIT = re.compile(r'(?<=[.?!"])\s+(?=[A-Z"])')


def paragraphs(text):
    text = text.split("## References")[0]
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s and not re.match(r"(#|[-*|]|\d+\.)", s):
            yield n, s


def check(path):
    issues = 0
    for n, para in paragraphs(open(path, encoding="utf-8").read()):
        def flag(msg):
            nonlocal issues
            issues += 1
            print(f"{path}:{n}: {msg}")

        if ", and" in para:
            flag(f"', and' x{para.count(', and')}")
        if "—" in para:
            flag("em dash")
        for w in MARKERS:
            if re.search(rf"\b{w}" if w[0].isalpha() else re.escape(w), para, re.I):
                flag(f"marker word '{w}'")
        sents = SPLIT.split(para)
        lens = [len(CITE.sub("", s).split()) for s in sents]
        for s, k in zip(sents, lens):
            if k > LONG:
                flag(f"long sentence ({k} words): {s[:70]}...")
        run = 0
        for s, k in zip(sents, lens):
            run = run + 1 if k < SHORT else 0
            if run == RUN:
                flag(f"choppy run of {RUN}+ short sentences near: {s[:60]}...")
    return issues


if __name__ == "__main__":
    total = sum(check(p) for p in sys.argv[1:])
    print(f"{total} issue(s)")
    sys.exit(1 if total else 0)
