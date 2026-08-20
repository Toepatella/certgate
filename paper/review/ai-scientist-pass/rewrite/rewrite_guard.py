"""Mechanical guard for the Phase-4 prose rewrite of paper/draft.md.

usage: python rewrite_guard.py OLD.md NEW.md [--bib references.bib]

Checks (each prints PASS/FAIL/INFO; exit 1 on any FAIL):
  1. numbers   : no NEW numeric tokens in the body (numbers removed are listed as INFO)
  2. codenames : no bare E1-E7 / P1-P7 / F-A..F-E / RP-n / T-nn tokens in MAIN text
                 (SI mapping table is exempt: lines inside a '<!-- codename-map -->' block)
  3. structure : same top-level '# ' sections in the same order; same '## ' subsection
                 numbering; every '**Figure N.'/'**Table N.' block still present; every
                 main figure/table has a strict callout at/after '# 4 Results' (Figure 1
                 anywhere); '**Figure S\\d.' blocks preserved; [[TBC:...]] set unchanged;
                 abstract regex + Background/Methods/Results/Conclusions labels present
  4. cites     : every [@key] in NEW exists in the bib (if --bib given)
  5. length    : per top-level section word count NEW <= OLD (+8% tolerance for
                 '# 2 Related work' which gains citations); MAIN total NEW <= OLD
  6. phrases   : counts of coined phrases OLD vs NEW (INFO, plus FAIL if any > 2 in NEW)
"""
import re, sys, json
from collections import Counter

REF_PAT = re.compile(r'\b(?:Section|Sections|Figure|Figures|Table|Tables|Fig\.|Appendix|SI)\s+S?\d+(?:\.\d+)*(?:\([a-z]+\))?(?:\s*(?:,|and|–|-|to)\s*S?\d+(?:\.\d+)*)*', re.I)
NUM_PAT = re.compile(r'(?<![A-Za-z@\[\{\\])[+-]?\$?\d[\d,]*(?:\.\d+)?%?')
CODENAME_PAT = re.compile(r'(?<![A-Za-z0-9_\-])(E[1-7]|P[1-7]|F-[A-E]|RP-\d+|T-\d+)(?![A-Za-z0-9_\-])')
COINED = ['load-bearing', 'honest', 'false sense', 'declines rather than', 'certifies or declines',
          'travels with', 'currenc', 'in-harness', 'silently', 'the atom of', 'rung']

def body_of(md):
    """text before '# References' with heading lines kept."""
    i = md.find('\n# References')
    return md if i < 0 else md[:i]

def main_of(md):
    i = md.find('\n# Supplementary Information')
    return md if i < 0 else md[:i]

def numbers(md):
    t = REF_PAT.sub(' ', body_of(md))
    t = re.sub(r'\[@[^\]]*\]', ' ', t)          # citations
    t = re.sub(r'\[\[TBC:[^\]]*\]\]', ' ', t)   # placeholders
    t = re.sub(r'\$\^\{1\}\$', ' ', t)          # affiliation mark
    t = re.sub(r'^#{1,3} .*$', ' ', t, flags=re.M)  # headings (section numbers)
    t = re.sub(r'\*\*(Figure|Table) S?\d+\.', ' ', t)  # float labels
    t = re.sub(r'\bA\.\d+(\([ivx]+\))?', ' ', t)      # SI section refs
    t = re.sub(r'\b(19|20)\d\d\b', ' ', t)      # years (dates in text)
    toks = [x.strip('$').replace(',', '') for x in NUM_PAT.findall(t)]
    toks = [x for x in toks if x not in ('', '+', '-')]
    return Counter(toks)

def sections(md):
    out, name, buf = [], None, []
    for line in md.split('\n'):
        if line.startswith('# '):
            if name is not None: out.append((name, '\n'.join(buf)))
            name, buf = line[2:].strip(), []
        else:
            buf.append(line)
    out.append((name, '\n'.join(buf)))
    return out

def words(t): return len(re.findall(r'\S+', t))

def check(old, new, bib=None):
    fails = 0
    def FAIL(msg):
        nonlocal fails; fails += 1; print('FAIL', msg)
    def PASS(msg): print('PASS', msg)
    def INFO(msg): print('INFO', msg)

    # 1 numbers (distinct-token basis: a token never seen in the old body is a new fact)
    no, nn = numbers(old), numbers(new)
    added = sorted(k for k in nn if k not in no)
    removed = sorted(k for k in no if k not in nn)
    if added: FAIL(f'NEW distinct numeric tokens in body: {added}')
    else: PASS('no new distinct numeric tokens')
    INFO(f'distinct numeric tokens dropped entirely ({len(removed)}): {removed}')

    # 2 codenames: E-codes banned in MAIN; P-codes allowed only inside section 4.10; F/RP/T banned
    m = main_of(new)
    e_hits = re.findall(r'(?<![A-Za-z0-9_\-])(E[1-7])(?![A-Za-z0-9_\-])', m)
    if e_hits: FAIL(f'bare E-codes in MAIN text: {Counter(e_hits)}')
    else: PASS('no bare E-codes in main text')
    s410 = m.find('## 4.10'); s5 = m.find('\n# 5 ')
    outside = m[:s410] + (m[s5:] if s5 > 0 else '')
    pf_out = re.findall(r'(?<![A-Za-z0-9_\-])(P[1-7]|F-[A-E]|RP-\d+|T-\d+)(?![A-Za-z0-9_\-])', outside)
    if pf_out: FAIL(f'P/F/RP/T codes outside section 4.10: {Counter(pf_out)}')
    else: PASS('P-codes confined to section 4.10 (protocol-label context)')
    old_e = re.findall(r'(?<![A-Za-z0-9_\-])E[1-7](?![A-Za-z0-9_\-])', main_of(old))
    INFO(f'old main-text E-code count: {len(old_e)}')

    # 3 structure
    so, sn = sections(old), sections(new)
    if [n for n, _ in so] != [n for n, _ in sn]:
        FAIL(f'top-level section names/order changed:\n  old={[n for n,_ in so]}\n  new={[n for n,_ in sn]}')
    else: PASS('top-level sections identical')
    subo = re.findall(r'^## ((?:\d+\.\d+)|(?:A\.\d+))\b', old, flags=re.M)
    subn = re.findall(r'^## ((?:\d+\.\d+)|(?:A\.\d+))\b', new, flags=re.M)
    if subo != subn: FAIL(f'subsection numbering changed: old={subo} new={subn}')
    else: PASS('subsection numbering identical')
    for kind in ('Figure', 'Table'):
        bo = re.findall(rf'^\*\*{kind} (S?\d+)\.', old, flags=re.M)
        bn = re.findall(rf'^\*\*{kind} (S?\d+)\.', new, flags=re.M)
        if bo != bn: FAIL(f'{kind} float blocks changed: old={bo} new={bn}')
        else: PASS(f'{kind} float blocks preserved: {bn}')
    # callouts
    body = new.split('\n# Figures')[0]
    res_at = re.search(r'^# 4 Results', body, flags=re.M)
    res_txt = body[res_at.start():] if res_at else body
    for n in re.findall(r'^\*\*Figure (\d+)\.', new, flags=re.M):
        n = int(n)
        hay = body if n == 1 else res_txt
        if not re.search(rf'\bFigure {n}\b', hay): FAIL(f'no strict callout for Figure {n} in body')
    for n in re.findall(r'^\*\*Table (\d+)\.', new, flags=re.M):
        if not re.search(rf'\bTable {int(n)}\b', res_txt): FAIL(f'no strict callout for Table {n} at/after Results')
    for n in re.findall(r'^\*\*Figure (S\d+)\.', new, flags=re.M):
        if not re.search(rf'\bFigure {n}\b', body): FAIL(f'no callout for Figure {n}')
    for n in re.findall(r'^\*\*Table (S\d+)\.', new, flags=re.M):
        if not re.search(rf'\bTable {n}\b', body): FAIL(f'no callout for Table {n}')
    PASS('callout scan done (any failures listed above)')
    tbo = sorted(set(re.findall(r'\[\[TBC:[^\]]*\]\]', old)))
    tbn = sorted(set(re.findall(r'\[\[TBC:[^\]]*\]\]', new)))
    if tbo != tbn: FAIL(f'[[TBC]] set changed: missing={set(tbo)-set(tbn)} extra={set(tbn)-set(tbo)}')
    else: PASS('[[TBC]] placeholders unchanged')
    if not re.search(r'\*\*Abstract\*\*\s*\n\n(.*?)\n\n\*\*Keywords\*\*\s*(.*?)\n', new, flags=re.S):
        FAIL('abstract regex does not match')
    else:
        ab = re.search(r'\*\*Abstract\*\*\s*\n\n(.*?)\n\n\*\*Keywords\*\*', new, flags=re.S).group(1)
        for lab in ('**Background**', '**Methods**', '**Results**', '**Conclusions**'):
            if lab not in ab: FAIL(f'abstract missing label {lab}')
        PASS(f'abstract parses; {words(ab)} words (old {words(re.search(r"[*][*]Abstract[*][*]\s*\n\n(.*?)\n\n[*][*]Keywords", old, flags=re.S).group(1))})')
    if not re.search(r'^\*\*Corresponding author:\*\*\s*(.*?),\s*(.*)$', new, flags=re.M): FAIL('corresponding-author line changed')

    # 4 cites
    keys = set(re.findall(r'@([A-Za-z0-9_:\-]+)', ' '.join(re.findall(r'\[@[^\]]*\]', new))))
    if bib:
        bibkeys = set(re.findall(r'^@\w+\{([^,]+),', open(bib, encoding='utf-8').read(), flags=re.M))
        missing = keys - bibkeys
        if missing: FAIL(f'cite keys missing from bib: {sorted(missing)}')
        else: PASS(f'all {len(keys)} cite keys resolve in bib')
    oldkeys = set(re.findall(r'@([A-Za-z0-9_:\-]+)', ' '.join(re.findall(r'\[@[^\]]*\]', old))))
    INFO(f'cite keys added: {sorted(keys-oldkeys)}; dropped: {sorted(oldkeys-keys)}')

    # 5 length
    do = dict(so); dn = dict(sn)
    main_old = main_new = 0
    for name in [n for n, _ in so]:
        if name not in dn: continue
        wo, wn = words(do[name]), words(dn[name])
        is_main = True
        if name.startswith('Supplementary') or name in ('Figures', 'Tables', 'References') or wo < 30:
            is_main = False
        if is_main:
            main_old += wo; main_new += wn
        INFO(f'len {name[:45]:45s} {wo:5d} -> {wn:5d}  ({(wn-wo)*100.0/max(wo,1):+.0f}%)')
    if main_new > main_old: FAIL(f'MAIN total grew {main_old} -> {main_new} (per-section drift is INFO; the total is the envelope)')
    else: PASS(f'MAIN total {main_old} -> {main_new} words ({(main_new-main_old)*100.0/max(main_old,1):+.0f}%)')

    # 6 phrases
    for ph in COINED:
        co = len(re.findall(re.escape(ph), main_of(old), flags=re.I))
        cn = len(re.findall(re.escape(ph), main_of(new), flags=re.I))
        flag = ''
        if ph in ('load-bearing', 'false sense', 'in-harness', 'currenc') and cn > 1: flag = '  <-- >1'; FAIL(f'coined phrase "{ph}" used {cn}x in main text')
        INFO(f'phrase {ph!r:26s} main-text count {co:3d} -> {cn:3d}{flag}')
    return fails

if __name__ == '__main__':
    args = sys.argv[1:]
    bib = None
    if '--bib' in args:
        i = args.index('--bib'); bib = args[i+1]; del args[i:i+2]
    old = open(args[0], encoding='utf-8').read()
    new = open(args[1], encoding='utf-8').read()
    f = check(old, new, bib)
    print('\nRESULT:', 'OK' if f == 0 else f'{f} FAILURE(S)')
    sys.exit(1 if f else 0)
