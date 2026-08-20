"""Revision-2 prose guard (forked from the archived ai-scientist-pass
rewrite_guard; SPEC/plan: the no-new-numbers rule becomes a CLAIM-TRACE rule).

Checks OLD (pre-revision, e.g. `git show main:paper/draft.md`) vs NEW:
 1. every ADDED distinct numeric token in the body appears in claim-trace.md
    (which maps it to a named artifact) -- an untraced new number FAILS;
 2. bare experiment codes E1-E9 never appear in MAIN text (P-codes allowed
    only inside section 4.10, the protocol-label context);
 3. every '**Figure N/SN.' and '**Table N/SN.' block has a strict in-text
    callout ('Figure 1' anywhere; other mains at/after '# 4 Results');
 4. [[TBC:...]] placeholder set unchanged; abstract still parses with its four
    labels; every cite key resolves in references.bib;
 5. section/length report (INFO) -- the built page count is the binding gate.

usage: python revision_guard.py OLD.md NEW.md CLAIM_TRACE.md --bib refs.bib
"""
import json
import re
import sys
from pathlib import Path

REF_PAT = re.compile(
    r'\b(?:Section|Sections|Figure|Figures|Table|Tables|Fig\.|Appendix|SI)\s+'
    r'S?\d+(?:\.\d+)*(?:\([a-z]+\))?(?:\s*(?:,|and|–|-|to)\s*'
    r'S?\d+(?:\.\d+)*)*', re.I)
NUM_PAT = re.compile(r'(?<![A-Za-z@\[\{\\])[+-]?\$?\d[\d,]*(?:\.\d+)?%?')


def body_of(md):
    i = md.find('\n# References')
    return md if i < 0 else md[:i]


def main_of(md):
    i = md.find('\n# Supplementary Information')
    return md if i < 0 else md[:i]


def numbers(md):
    t = REF_PAT.sub(' ', body_of(md))
    t = re.sub(r'\[@[^\]]*\]', ' ', t)
    t = re.sub(r'\[\[TBC:[^\]]*\]\]', ' ', t)
    t = re.sub(r'^#{1,3} .*$', ' ', t, flags=re.M)
    t = re.sub(r'\*\*(Figure|Table) S?\d+\.', ' ', t)
    t = re.sub(r'\bA\.\d+(\([ivx]+\))?', ' ', t)
    t = re.sub(r'\b(19|20)\d\d\b', ' ', t)
    toks = [x.strip('$').replace(',', '') for x in NUM_PAT.findall(t)]
    return {x for x in toks if x not in ('', '+', '-')}


def main(old_p, new_p, trace_p, bib_p):
    old = Path(old_p).read_text(encoding='utf-8')
    new = Path(new_p).read_text(encoding='utf-8')
    trace = Path(trace_p).read_text(encoding='utf-8')
    fails = []

    added = sorted(numbers(new) - numbers(old))
    trace_toks = {x.strip('$').replace(',', '')
                  for x in NUM_PAT.findall(trace)}
    untraced = [a for a in added if a not in trace_toks]
    print(f'PASS added distinct tokens: {len(added)}; all traced'
          if not untraced else '', end='')
    if untraced:
        fails.append(f'untraced new numeric tokens: {untraced}')
    else:
        print()

    m = main_of(new)
    e_hits = re.findall(r'(?<![A-Za-z0-9_\-])(E[1-9])(?![A-Za-z0-9_\-])', m)
    if e_hits:
        fails.append(f'bare E-codes in MAIN: {sorted(set(e_hits))}')
    s410, s5 = m.find('## 4.10'), m.find('\n# 5 ')
    outside = m[:s410] + (m[s5:] if s5 > 0 else '')
    pf = re.findall(r'(?<![A-Za-z0-9_\-])(P[1-7]|F-[A-E])(?![A-Za-z0-9_\-])',
                    outside)
    if pf:
        fails.append(f'P/F codes outside 4.10: {sorted(set(pf))}')

    body = new.split('\n# Figures')[0]
    res_at = re.search(r'^# 4 Results', body, flags=re.M)
    res_txt = body[res_at.start():] if res_at else body
    for n in re.findall(r'^\*\*Figure (\d+)\.', new, flags=re.M):
        hay = body if n == '1' else res_txt
        if not re.search(rf'\bFigure {n}\b', hay):
            fails.append(f'no callout Figure {n}')
    for n in re.findall(r'^\*\*Table (\d+)\.', new, flags=re.M):
        if not re.search(rf'\bTable {n}\b', res_txt):
            fails.append(f'no callout Table {n}')
    for kind in ('Figure', 'Table'):
        for n in re.findall(rf'^\*\*{kind} (S\d+)\.', new, flags=re.M):
            if not re.search(rf'\b{kind} {n}\b', body):
                fails.append(f'no callout {kind} {n}')

    tbo = sorted(set(re.findall(r'\[\[TBC:[^\]]*\]\]', old)))
    tbn = sorted(set(re.findall(r'\[\[TBC:[^\]]*\]\]', new)))
    if tbo != tbn:
        fails.append('[[TBC]] set changed')
    ab = re.search(r'\*\*Abstract\*\*\s*\n\n(.*?)\n\n\*\*Keywords\*\*',
                   new, flags=re.S)
    if not ab or any(lab not in ab.group(1) for lab in
                     ('**Background**', '**Methods**', '**Results**',
                      '**Conclusions**')):
        fails.append('abstract structure broken')

    keys = set(re.findall(r'@([A-Za-z0-9_:\-]+)',
                          ' '.join(re.findall(r'\[@[^\]]*\]', new))))
    bibkeys = set(re.findall(r'^@\w+\{([^,]+),',
                             Path(bib_p).read_text(encoding='utf-8'),
                             flags=re.M))
    missing = keys - bibkeys
    if missing:
        fails.append(f'cite keys missing: {sorted(missing)}')

    wo = len(re.findall(r'\S+', main_of(old)))
    wn = len(re.findall(r'\S+', main_of(new)))
    print(f'INFO main words {wo} -> {wn} ({wn - wo:+d}); '
          f'the BUILT page count is the binding envelope gate')
    print('RESULT:', 'OK' if not fails else f'{len(fails)} FAILURE(S)')
    for f in fails:
        print('FAIL', f)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--bib']
    main(args[0], args[1], args[2], args[3])
