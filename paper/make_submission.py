"""Build the Discover Computing (Springer Nature) submission package.

Reads the canonical manuscript source -- ``paper/draft.md`` (pandoc markdown,
citations as ``[@key]``) and ``paper/references.bib`` -- and emits a complete
sn-jnl LaTeX project under ``paper/build/out/sn/``, compiled to
``paper/build/out/CertGate_DiscoverComputing.pdf`` plus a Snapp figures zip.

draft.md stays untouched: this script performs, mechanically, exactly the
relocations the journal's format requires (figures and tables moved from
their end-of-draft caption sections to their first in-text callout; manual
heading numbers stripped so LaTeX renumbers identically; back-matter
sections mapped to \\bmhead declarations; the References placeholder replaced
by bibtex over sn-vancouver-num.bst).

Float numbering is forced to the draft's own figure/table numbers via
\\setcounter before every caption, because the prose references those numbers
textually ("Table 5", "Figure 1, centre") and Table 5's first callout
(Section 3.2) precedes Table 1's (Section 4.2).

Requires pandoc and a MiKTeX/TeX Live pdflatex + bibtex on PATH.
Usage: python paper/make_submission.py [--no-compile]
"""

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
SN = PAPER / "build" / "sn"
OUT = PAPER / "build" / "out"
BUILD = OUT / "sn"
FIGSRC = ROOT / "experiments" / "out"
PDF_NAME = "CertGate_DiscoverComputing.pdf"

# The canonical figure -> artifact map (also documented in README.md).
# E6_reliability.png, EICU_per_site.png and EICU_reliability_panel.png are
# supplementary-only by design and carry no figure number.
FIGURE_MAP = {
    1: "E1_validity.png",
    2: "E2_label_shift.png",
    3: "E3_concept_shift.png",
    4: "E4_site_sweep.png",
    5: "E5_explain.png",
    6: "E6_fairness.png",
    7: "E7_comparator.png",
    8: "EICU_pooled.png",
}

# Back-matter sections in the order the journal's end-matter renders them.
# Acknowledgements stays outside the Declarations block.
DECLARATIONS = [
    "Data availability",
    "Code availability",
    "Funding",
    "Author contributions",
    "Ethics approval and consent to participate",
    "Consent for publication",
    "Competing interests",
]

# Data rows above which a table cannot float on one page and is emitted as a
# page-breaking longtable instead (Table 5 is the case that needs this).
LONGTABLE_ROWS = 18


def pandoc(md: str) -> str:
    """markdown -> LaTeX body fragment; [@key] groups become \\citep{...}."""
    r = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "latex", "--wrap=none", "--natbib"],
        input=md.encode("utf-8"), capture_output=True)
    if r.returncode:
        raise RuntimeError(f"pandoc failed:\n{r.stderr.decode('utf-8')}")
    # pandoc on Windows emits CRLF; normalize or write_text doubles the CR
    # into \r\r\n, which TeX reads as a phantom blank line (a \par) and
    # chokes on inside table specs
    return r.stdout.decode("utf-8").replace("\r\n", "\n").strip()


def strip_heading_numbers(md: str) -> str:
    """'# 1 Introduction' -> '# Introduction'; '## A.1 X' -> '## X'.
    LaTeX renumbers in the same order, so the prose's textual cross
    references ('Section 3.3', 'Appendix A.1(iii)') stay correct."""
    out = []
    for line in md.splitlines():
        m = re.match(r"^(#{1,3})\s+(?:\d+(?:\.\d+)*|A\.\d+)\s+(.*)$", line)
        out.append(f"{m.group(1)} {m.group(2)}" if m else line)
    return "\n".join(out)


def split_sections(draft: str):
    """Split the draft into top-level '# ' sections, preserving order."""
    parts, current_name, current = [], None, []
    for line in draft.splitlines():
        if line.startswith("# "):
            if current_name is not None:
                parts.append((current_name, "\n".join(current).strip()))
            current_name, current = line[2:].strip(), []
        else:
            current.append(line)
    parts.append((current_name, "\n".join(current).strip()))
    return parts


def parse_float_blocks(section_md: str, kind: str):
    """Parse the end-of-draft '# Figures'/'# Tables' sections into
    {number: block_markdown}; a block runs from one '**Kind N.' marker to
    the next."""
    blocks, num, buf = {}, None, []
    marker = re.compile(rf"^\*\*{kind} (\d+)\.")
    for para in section_md.split("\n\n"):
        m = marker.match(para.strip())
        if m:
            if num is not None:
                blocks[num] = "\n\n".join(buf).strip()
            num, buf = int(m.group(1)), [para.strip()]
        elif num is not None:
            buf.append(para.strip())
    if num is not None:
        blocks[num] = "\n\n".join(buf).strip()
    return blocks


def caption_latex(caption_md: str, kind: str, number: int) -> str:
    """'**Table 5. Title.** Legend...' -> caption body LaTeX with the
    'Table 5.' label dropped (LaTeX re-adds it via the forced counter)."""
    m = re.match(rf"\*\*{kind} {number}\.\s*(.*?)\*\*\s*(.*)$",
                 caption_md, re.S)
    if not m:
        raise ValueError(f"unparseable {kind} {number} caption")
    title_md, legend_md = m.group(1).strip(), m.group(2).strip()
    return pandoc(f"**{title_md}** {legend_md}")


def extract_longtable(lt: str):
    """The \\begin{longtable}...\\end{longtable} lines from pandoc output,
    dropping the '{\\def\\LTcaptype{none}' wrapper pandoc 3.x adds."""
    lines = lt.strip().splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.lstrip().startswith("\\begin{longtable}"))
    end = next(i for i, l in enumerate(lines)
               if l.lstrip().startswith("\\end{longtable}"))
    return lines[start:end + 1]


def split_longtable_head(lines):
    """(colspec, body_start_index) for a pandoc longtable whose column spec
    may span several source lines (pandoc 3.x wraps fixed-width specs)."""
    joined = ""
    for i, line in enumerate(lines):
        joined += line.strip()
        m = re.match(r"\\begin\{longtable\}\[[^\]]*\]\{", joined)
        if m:
            start = m.end() - 1
            depth = 0
            for j in range(start, len(joined)):
                if joined[j] == "{":
                    depth += 1
                elif joined[j] == "}":
                    depth -= 1
                    if depth == 0:
                        return joined[start + 1:j], i + 1
    raise ValueError("could not parse longtable head")


def longtable_to_tabular(lt: str) -> str:
    """Rewrite one pandoc longtable into a plain tabular (float-safe)."""
    lines = extract_longtable(lt)
    spec, body_at = split_longtable_head(lines)
    body = []
    for line in lines[body_at:]:
        s = line.strip()
        if s in ("\\endhead", "\\endfirsthead", "\\endfoot",
                 "\\endlastfoot", "\\end{longtable}"):
            continue
        body.append(line)
    # pandoc puts the \bottomrule ahead of \endlastfoot; move it to the end
    bottom = [i for i, l in enumerate(body)
              if l.strip().startswith("\\bottomrule")]
    if bottom:
        body.append(body.pop(bottom[0]))
    return "\\begin{tabular}{%s}\n%s\n\\end{tabular}" % (spec, "\n".join(body))


def table_float(number: int, block_md: str) -> str:
    """One '# Tables' block -> a LaTeX float (or longtable group)."""
    paras = block_md.split("\n\n")
    caption = caption_latex(paras[0], "Table", number)
    segments = paras[1:]
    n_rows = sum(p.count("\n") for p in segments if p.lstrip().startswith("|"))
    size = "\\small" if max(p.count("|") for p in segments
                            if p.lstrip().startswith("|")) <= 7 \
        else "\\footnotesize"

    if n_rows > LONGTABLE_ROWS:
        # page-breaking form: caption inside the first longtable.
        # \begingroup, not a bare '{': pandoc escapes a brace-opened line
        # into literal \{ text, silently unbalancing the group
        out = ["\\begingroup" + size,
               "\\setlength{\\LTcapwidth}{\\textwidth}",
               "\\setcounter{table}{%d}" % (number - 1)]
        first = True
        for seg in segments:
            if seg.lstrip().startswith("|"):
                lt_lines = extract_longtable(pandoc(seg))
                if first:
                    cap_at = next(i for i, l in enumerate(lt_lines)
                                  if "\\toprule" in l)
                    lt_lines.insert(cap_at, "\\caption{%s}\\label{tab:%d}\\\\"
                                    % (caption, number))
                    first = False
                out.append("\n".join(lt_lines))
            else:
                out.append(pandoc(seg))
        out.append("\\endgroup")
        return "\n".join(out)

    parts = []
    for seg in segments:
        if seg.lstrip().startswith("|"):
            parts.append(longtable_to_tabular(pandoc(seg)))
        else:
            parts.append(pandoc(seg))
    return ("\\begin{table}[!htbp]\n"
            "\\setcounter{table}{%d}\n"
            "\\caption{%s}\\label{tab:%d}\n"
            "\\centering %s\n%s\n"
            "\\end{table}" % (number - 1, caption, number, size,
                              "\n".join(parts)))


def figure_float(number: int, block_md: str) -> str:
    caption = caption_latex(block_md.split("\n\n")[0], "Figure", number)
    return ("\\begin{figure}[!htbp]\n"
            "\\setcounter{figure}{%d}\n"
            "\\centering\n"
            "\\includegraphics[width=\\textwidth]{figs/%s}\n"
            "\\caption{%s}\\label{fig:%d}\n"
            "\\end{figure}" % (number - 1, FIGURE_MAP[number],
                               caption, number))


def anchor_paragraph(paras, kind: str, number: int, start: int) -> int:
    """Index of the paragraph carrying the first strict '<Kind> N' callout
    at or after ``start`` ('Figures 1--7'-style plural sweeps are ignored
    on purpose -- they are reproducibility statements, not callouts)."""
    pat = re.compile(rf"\b{kind} {number}\b")
    for i in range(start, len(paras)):
        if pat.search(paras[i]):
            return i
    raise ValueError(f"no callout found for {kind} {number}")


def build_body(body_md: str, fig_blocks, tab_blocks) -> str:
    paras = body_md.split("\n\n")
    results_at = next(i for i, p in enumerate(paras)
                      if re.match(r"^#\s+(?:4\s+)?Results", p))
    inserts = {}  # paragraph index -> [latex floats]
    for n in sorted(fig_blocks):
        idx = anchor_paragraph(paras, "Figure", n, results_at)
        inserts.setdefault(idx, []).append(figure_float(n, fig_blocks[n]))
    for n in sorted(tab_blocks):
        # Table 5's home is Section 3.2; everything else anchors in Results+
        start = 0 if n == 5 else results_at
        idx = anchor_paragraph(paras, "Table", n, start)
        inserts.setdefault(idx, []).append(table_float(n, tab_blocks[n]))
    out = []
    for i, p in enumerate(paras):
        out.append(p)
        out.extend(inserts.get(i, []))
    return pandoc(strip_heading_numbers("\n\n".join(out)))


MAIN_TEMPLATE = r"""%% Generated by paper/make_submission.py -- DO NOT EDIT BY HAND.
%% Canonical source: paper/draft.md + paper/references.bib.
\documentclass[pdflatex,sn-vancouver-num]{sn-jnl}

\usepackage{graphicx}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{calc}
\usepackage[title]{appendix}
\usepackage{textcomp}

% pandoc emits \tightlist after list openings
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}

\raggedbottom

\begin{document}

\title[CertGate]{<<TITLE>>}

\author*[1]{<<AUTHOR>>}\email{<<EMAIL>>}
\affil*[1]{<<AFFIL>>}

\abstract{<<ABSTRACT>>}

\keywords{<<KEYWORDS>>}

\maketitle

<<BODY>>

\begin{appendices}

<<APPENDIX>>

\end{appendices}

\backmatter

<<ACKNOWLEDGEMENTS>>

\section*{Declarations}

<<DECLARATIONS>>

\bibliography{references}

\end{document}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-compile", action="store_true",
                    help="emit the LaTeX project without running pdflatex")
    args = ap.parse_args()

    draft = (PAPER / "draft.md").read_text(encoding="utf-8")

    tbc = sorted(set(re.findall(r"\[\[TBC:[^\]]*\]\]", draft)))
    if tbc:
        print("=" * 72)
        print("WARNING: author-supplied blanks remain (the PDF will show "
              "them verbatim):")
        for t in tbc:
            print(f"  {t}")
        print("=" * 72)

    # ---- front matter -----------------------------------------------------
    lines = draft.splitlines()
    title = lines[0].lstrip("# ").strip()
    m = re.search(r"\*\*Abstract\*\*\s*\n\n(.*?)\n\n\*\*Keywords\*\*\s*(.*?)\n",
                  draft, re.S)
    if not m:
        raise SystemExit("could not locate Abstract/Keywords block")
    abstract_latex = pandoc(m.group(1))
    keywords = ", ".join(k.strip() for k in m.group(2).split("\u00b7"))

    corr = re.search(r"\*\*Corresponding author:\*\*\s*(.*?),\s*(.*)$",
                     draft, re.M)
    author_names = lines[2].split("$")[0].strip()
    affil = re.sub(r"^\$\^\{1\}\$\s*", "", lines[4]).strip()
    email = corr.group(2).strip() if corr else "[[TBC:corresponding-email]]"

    # ---- sections ---------------------------------------------------------
    sections = dict(split_sections(draft))
    order = [name for name, _ in split_sections(draft)]
    body_names = [n for n in order
                  if re.match(r"^\d+\s", n)]           # '1 Introduction' ...
    appendix_name = next(n for n in order if n.startswith("Appendix A"))

    body_md = "\n\n".join(f"# {n}\n\n{sections[n]}" for n in body_names)
    fig_blocks = parse_float_blocks(sections["Figures"], "Figure")
    tab_blocks = parse_float_blocks(sections["Tables"], "Table")
    if set(fig_blocks) != set(FIGURE_MAP):
        raise SystemExit(f"figure blocks {sorted(fig_blocks)} != map "
                         f"{sorted(FIGURE_MAP)}")

    body_latex = build_body(body_md, fig_blocks, tab_blocks)

    appendix_title = appendix_name.split(":", 1)[1].strip()
    appendix_latex = pandoc(strip_heading_numbers(
        f"# {appendix_title}\n\n{sections[appendix_name]}"))

    ack_md = sections.get("Acknowledgements", "").strip()
    ack_latex = ""
    if ack_md:
        ack_latex = "\\bmhead{Acknowledgements}\n\n" + pandoc(ack_md)

    decl_parts = []
    for name in DECLARATIONS:
        if name not in sections:
            raise SystemExit(f"missing back-matter section: {name}")
        decl_parts.append(f"\\bmhead{{{name}}}\n\n{pandoc(sections[name])}")
    decl_latex = "\n\n".join(decl_parts)

    # ---- assemble ---------------------------------------------------------
    main_tex = (MAIN_TEMPLATE
                .replace("<<TITLE>>", pandoc(title))
                .replace("<<AUTHOR>>", author_names)
                .replace("<<EMAIL>>", email)
                .replace("<<AFFIL>>", pandoc(affil))
                .replace("<<ABSTRACT>>", abstract_latex)
                .replace("<<KEYWORDS>>", keywords)
                .replace("<<BODY>>", body_latex)
                .replace("<<APPENDIX>>", appendix_latex)
                .replace("<<ACKNOWLEDGEMENTS>>", ack_latex)
                .replace("<<DECLARATIONS>>", decl_latex))

    if BUILD.exists():
        # ignore_errors: a shell sitting in the build dir must not kill the
        # build -- contents are cleared, the locked root survives
        shutil.rmtree(BUILD, ignore_errors=True)
    (BUILD / "figs").mkdir(parents=True, exist_ok=True)
    (BUILD / "main.tex").write_text(main_tex, encoding="utf-8", newline="\n")
    shutil.copy(PAPER / "references.bib", BUILD / "references.bib")
    shutil.copy(SN / "sn-jnl.cls", BUILD / "sn-jnl.cls")
    shutil.copy(SN / "sn-vancouver-num.bst", BUILD / "sn-vancouver-num.bst")
    for png in FIGURE_MAP.values():
        shutil.copy(FIGSRC / png, BUILD / "figs" / png)

    with zipfile.ZipFile(OUT / "CertGate_figures.zip", "w") as z:
        for n, png in sorted(FIGURE_MAP.items()):
            z.write(FIGSRC / png, f"Fig{n}_{png}")
    print(f"[make_submission] wrote {BUILD / 'main.tex'} and "
          f"{OUT / 'CertGate_figures.zip'}")

    if args.no_compile:
        return

    # ---- compile ----------------------------------------------------------
    def run(*cmd):
        r = subprocess.run(cmd, cwd=BUILD, capture_output=True)
        return r.returncode, r.stdout.decode("utf-8", "replace")

    steps = [("pdflatex", "pdflatex", "-interaction=nonstopmode", "main.tex"),
             ("bibtex", "bibtex", "main"),
             ("pdflatex", "pdflatex", "-interaction=nonstopmode", "main.tex"),
             ("pdflatex", "pdflatex", "-interaction=nonstopmode", "main.tex")]
    for name, *cmd in steps:
        code, out = run(*cmd)
        if code and name == "pdflatex":
            errs = [l for l in out.splitlines() if l.startswith("!")]
            raise SystemExit(f"{name} failed:\n" + "\n".join(errs[:20]))

    log = (BUILD / "main.log").read_text(encoding="utf-8", errors="replace")
    problems = [l for l in log.splitlines()
                if "undefined" in l.lower() and "warning" in l.lower()]
    if problems:
        print("[make_submission] WARNING — unresolved references/citations:")
        for p in problems[:20]:
            print("  " + p)
    shutil.copy(BUILD / "main.pdf", OUT / PDF_NAME)
    print(f"[make_submission] wrote {OUT / PDF_NAME}")


if __name__ == "__main__":
    main()
