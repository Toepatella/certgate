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
textually ("Table 4", "Figure 2, centre"). Figure 1 is the pipeline schematic
compiled from figures-src/pipeline.tex; the frozen-constants register lives
in the Supplementary Information as Table S1.

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
# Figure 1 is the pipeline schematic, compiled from figures-src/pipeline.tex;
# Figures 2-9 are experiment artifacts. E6_reliability.png stays
# supplementary-only with no number; the two eICU orphans are the
# Supplementary Information figures S1/S2.
FIGURE_MAP = {
    1: "pipeline.pdf",
    2: "EICU_pooled.png",
    3: "E8_suite.png",
    4: "E9_frontiers.png",
}
# print width per figure, in fractions of \textwidth (single-panel figures
# do not earn a full page-width)
FIG_WIDTHS = {1: 0.8, 2: 0.9, 3: 0.96, 4: 0.8}
SI_FIGURE_MAP = {
    "S1": "EICU_reliability_panel.png",
    "S2": "EICU_per_site.png",
    "S3": "E1_validity.png",
    "S4": "E3_concept_shift.png",
    "S5": "E5_explain.png",
    "S6": "E7_comparator.png",
    "S7": "E4_site_sweep.png",
    "S8": "E6_fairness.png",
    "S9": "E2_label_shift.png",
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
            "\\includegraphics[width=%.2f\\textwidth]{figs/%s}\n"
            "\\caption{%s}\\label{fig:%d}\n"
            "\\end{figure}" % (number - 1, FIG_WIDTHS[number],
                               FIGURE_MAP[number], caption, number))


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
        # Figure 1 (the pipeline) is called out in Methods; the data figures
        # anchor in Results and later
        idx = anchor_paragraph(paras, "Figure", n,
                               0 if n == 1 else results_at)
        inserts.setdefault(idx, []).append(figure_float(n, fig_blocks[n]))
    for n in sorted(tab_blocks):
        # every remaining main-text table anchors in Results or later (the
        # frozen-constants register moved to the SI as Table S1)
        idx = anchor_paragraph(paras, "Table", n, results_at)
        inserts.setdefault(idx, []).append(table_float(n, tab_blocks[n]))
    out = []
    for i, p in enumerate(paras):
        out.append(p)
        out.extend(inserts.get(i, []))
    return pandoc(strip_heading_numbers("\n\n".join(out)))


COMPACT_TEMPLATE = r"""%% Generated by paper/make_submission.py -- DO NOT EDIT BY HAND.
%% Compact READING copy (10pt article) -- NOT the submission typescript.
\documentclass[10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{calc}
\usepackage{textcomp}
\usepackage[numbers,sort&compress]{natbib}
\usepackage[hidelinks]{hyperref}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\newcommand{\bmhead}[1]{\paragraph*{#1}}
\setlength{\textfloatsep}{10pt plus 2pt minus 2pt}
\setlength{\intextsep}{8pt plus 2pt minus 2pt}
\begin{document}
\title{<<TITLE>>\\[6pt]{\normalsize\itshape Compact reading copy --- the submission typescript is CertGate\_DiscoverComputing.pdf}}
\author{<<AUTHOR>>}
\date{}
\maketitle
\begin{abstract}
<<ABSTRACT>>
\end{abstract}
<<BODY>>
<<ACKNOWLEDGEMENTS>>
\section*{Declarations}
<<DECLARATIONS>>
\setcounter{secnumdepth}{-1}
<<SIBODY>>
\bibliographystyle{unsrtnat}
\bibliography{references}
\end{document}
"""

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
% reference list one size down, tighter entry separation (production
% restyles the list anyway)
\renewcommand{\bibfont}{\footnotesize}
\setlength{\bibsep}{3pt plus 0.3ex}

\raggedbottom
% the class alternates margins for two-sided printing; on screen that reads
% as every other page shifting sideways -- make the margins symmetric
\AtBeginDocument{\evensidemargin=\oddsidemargin}

\begin{document}

\title[CertGate]{<<TITLE>>}

\author*[1]{<<AUTHOR>>}\email{<<EMAIL>>}
\affil*[1]{<<AFFIL>>}

\abstract{<<ABSTRACT>>}

\keywords{<<KEYWORDS>>}

\maketitle

<<BODY>>

\backmatter

\bmhead{Supplementary information}

The online version contains supplementary material: Supplementary Information A (deferred proofs; software and reproducibility details with the frozen-constants register, Table S1; the post-hoc reliability panel on eICU-CRD, Figures S1--S2; and extended results, Figures S3--S9 and Tables S2--S9).

<<ACKNOWLEDGEMENTS>>

\section*{Declarations}

<<DECLARATIONS>>

\bibliography{references}

\end{document}
"""

SI_TEMPLATE = r"""%% Generated by paper/make_submission.py -- DO NOT EDIT BY HAND.
%% Canonical source: paper/draft.md (Supplementary Information A section).
\documentclass[pdflatex,sn-vancouver-num]{sn-jnl}

\usepackage{graphicx}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{calc}
\usepackage{textcomp}

\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}

\raggedbottom
\AtBeginDocument{\evensidemargin=\oddsidemargin}
\unnumbered% headings keep their literal A.x labels

\begin{document}

\title[Supplementary Information]{Supplementary Information for: <<TITLE>>}

\author*[1]{<<AUTHOR>>}\email{<<EMAIL>>}
\affil*[1]{<<AFFIL>>}

\abstract{Supplementary Information A for the main article: deferred proofs (A.1, A.2), software and reproducibility details (A.3) with the frozen-constants register (Table S1), the post-hoc selective reliability panel on eICU-CRD v2.0 (A.4, Figures S1--S2), and extended results (A.5, Figures S3--S9 and Tables S2--S9). References of the form ``Section 3.x'' point into the main article.}

\keywords{}

\maketitle

<<SIBODY>>

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

    # ---- front matter (anchor on the title heading, never on offsets) ------
    lines = draft.splitlines()
    t_at = next(i for i, l in enumerate(lines) if l.startswith("# "))
    title = lines[t_at].lstrip("# ").strip()
    if not title:
        raise SystemExit("empty title parsed from draft.md")
    m = re.search(r"\*\*Abstract\*\*\s*\n\n(.*?)\n\n\*\*Keywords\*\*\s*(.*?)\n",
                  draft, re.S)
    if not m:
        raise SystemExit("could not locate Abstract/Keywords block")
    abstract_latex = pandoc(m.group(1))
    keywords = ", ".join(k.strip() for k in m.group(2).split("\u00b7"))

    corr = re.search(r"\*\*Corresponding author:\*\*\s*(.*?),\s*(.*)$",
                     draft, re.M)
    author_names = lines[t_at + 2].split("$")[0].strip()
    affil = re.sub(r"^\$\^\{1\}\$\s*", "", lines[t_at + 4]).strip()
    if not author_names or not affil:
        raise SystemExit("empty author/affiliation parsed from draft.md")
    email = corr.group(2).strip() if corr else "[[TBC:corresponding-email]]"

    # ---- sections ---------------------------------------------------------
    sections = dict(split_sections(draft))
    order = [name for name, _ in split_sections(draft)]
    body_names = [n for n in order
                  if re.match(r"^\d+\s", n)]           # '1 Introduction' ...
    si_name = next(n for n in order
                   if n.startswith("Supplementary Information A"))

    body_md = "\n\n".join(f"# {n}\n\n{sections[n]}" for n in body_names)
    fig_blocks = parse_float_blocks(sections["Figures"], "Figure")
    tab_blocks = parse_float_blocks(sections["Tables"], "Table")
    if set(fig_blocks) != set(FIGURE_MAP):
        raise SystemExit(f"figure blocks {sorted(fig_blocks)} != map "
                         f"{sorted(FIGURE_MAP)}")

    body_latex = build_body(body_md, fig_blocks, tab_blocks)

    # ---- Supplementary Information document --------------------------------
    # Heading numbers are NOT stripped here: the A.x labels are the SI's own
    # numbering and the main text cites them literally ("Supplementary
    # Information A.1(iii)"). Figure S-blocks become embedded floats with
    # hand-set labels (never \caption, which would number them "Fig. 1").
    si_title = si_name.split(":", 1)[1].strip()
    si_paras = []
    for para in sections[si_name].split("\n\n"):
        m = re.match(r"\*\*Figure (S\d)\.\s*(.*?)\*\*\s*(.*)$",
                     para.strip(), re.S)
        if m:
            tag, cap_title, cap_rest = m.groups()
            cap = pandoc(f"**{cap_title.strip()}** {cap_rest.strip()}")
            si_paras.append(
                "\\begin{figure}[!htbp]\n\\centering\n"
                "\\includegraphics[width=\\textwidth]{figs/%s}\n"
                "\\par\\vspace{4pt}\n"
                "{\\small \\textbf{Figure %s.} %s}\n"
                "\\end{figure}" % (SI_FIGURE_MAP[tag], tag, cap))
        else:
            si_paras.append(para)
    si_body_latex = pandoc(f"# {si_title}\n\n" + "\n\n".join(si_paras))
    # pandoc wraps longtables in {\def\LTcaptype{none} ...}, which trips
    # sn-jnl ("No counter 'none' defined"); the SI tables carry no \caption,
    # so the guard protects nothing -- unwrap it
    si_body_latex = re.sub(r"\{\\def\\LTcaptype\{none\}[^\n]*\n", "",
                           si_body_latex)
    si_body_latex = si_body_latex.replace("\\end{longtable}\n}",
                                          "\\end{longtable}")

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
    title_latex = pandoc(title)
    affil_latex = pandoc(affil)
    main_tex = (MAIN_TEMPLATE
                .replace("<<TITLE>>", title_latex)
                .replace("<<AUTHOR>>", author_names)
                .replace("<<EMAIL>>", email)
                .replace("<<AFFIL>>", affil_latex)
                .replace("<<ABSTRACT>>", abstract_latex)
                .replace("<<KEYWORDS>>", keywords)
                .replace("<<BODY>>", body_latex)
                .replace("<<ACKNOWLEDGEMENTS>>", ack_latex)
                .replace("<<DECLARATIONS>>", decl_latex))
    si_tex = (SI_TEMPLATE
              .replace("<<TITLE>>", title_latex)
              .replace("<<AUTHOR>>", author_names)
              .replace("<<EMAIL>>", email)
              .replace("<<AFFIL>>", affil_latex)
              .replace("<<SIBODY>>", si_body_latex))
    compact_body = re.sub(   # reading copy: figures at 80% of print size
        r"width=([0-9.]+)\\textwidth",
        lambda m: "width=%.2f\\textwidth" % (float(m.group(1)) * 0.8),
        body_latex)
    compact_tex = (COMPACT_TEMPLATE
                   .replace("<<TITLE>>", title_latex)
                   .replace("<<AUTHOR>>", author_names)
                   .replace("<<ABSTRACT>>", abstract_latex)
                   .replace("<<BODY>>", compact_body)
                   .replace("<<ACKNOWLEDGEMENTS>>", ack_latex)
                   .replace("<<DECLARATIONS>>", decl_latex)
                   .replace("<<SIBODY>>", si_body_latex))

    if BUILD.exists():
        # ignore_errors: a shell sitting in the build dir must not kill the
        # build -- contents are cleared, the locked root survives
        shutil.rmtree(BUILD, ignore_errors=True)
    (BUILD / "figs").mkdir(parents=True, exist_ok=True)
    (BUILD / "main.tex").write_text(main_tex, encoding="utf-8", newline="\n")
    (BUILD / "si.tex").write_text(si_tex, encoding="utf-8", newline="\n")
    (BUILD / "compact.tex").write_text(compact_tex, encoding="utf-8",
                                       newline="\n")
    shutil.copy(PAPER / "references.bib", BUILD / "references.bib")
    shutil.copy(SN / "sn-jnl.cls", BUILD / "sn-jnl.cls")
    shutil.copy(SN / "sn-vancouver-num.bst", BUILD / "sn-vancouver-num.bst")
    for f in FIGURE_MAP.values():
        if f.endswith(".png"):
            shutil.copy(FIGSRC / f, BUILD / "figs" / f)
    for f in SI_FIGURE_MAP.values():
        shutil.copy(FIGSRC / f, BUILD / "figs" / f)

    # ---- Figure 1: compile the pipeline schematic --------------------------
    r = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode",
         f"-output-directory={BUILD / 'figs'}", "pipeline.tex"],
        cwd=PAPER / "figures-src", capture_output=True)
    if r.returncode or not (BUILD / "figs" / "pipeline.pdf").exists():
        raise SystemExit("pipeline.tex failed to compile:\n"
                         + r.stdout.decode("utf-8", "replace")[-2000:])

    # journal naming convention for the figures zip: Fig1.pdf, Fig2.png, ...
    with zipfile.ZipFile(OUT / "CertGate_figures.zip", "w") as z:
        for n, f in sorted(FIGURE_MAP.items()):
            src = (BUILD / "figs" / f) if f == "pipeline.pdf" else FIGSRC / f
            z.write(src, f"Fig{n}{Path(f).suffix}")
        for tag, f in sorted(SI_FIGURE_MAP.items()):
            z.write(FIGSRC / f, f"Fig{tag}{Path(f).suffix}")
    print(f"[make_submission] wrote {BUILD / 'main.tex'}, "
          f"{BUILD / 'si.tex'} and {OUT / 'CertGate_figures.zip'}")

    if args.no_compile:
        return

    # ---- compile ----------------------------------------------------------
    def run(*cmd):
        r = subprocess.run(cmd, cwd=BUILD, capture_output=True)
        return r.returncode, r.stdout.decode("utf-8", "replace")

    def build_doc(base):
        steps = [("pdflatex", "pdflatex", "-interaction=nonstopmode",
                  f"{base}.tex"),
                 ("bibtex", "bibtex", base),
                 ("pdflatex", "pdflatex", "-interaction=nonstopmode",
                  f"{base}.tex"),
                 ("pdflatex", "pdflatex", "-interaction=nonstopmode",
                  f"{base}.tex")]
        for name, *cmd in steps:
            code, out = run(*cmd)
            if code and name == "pdflatex":
                errs = [l for l in out.splitlines() if l.startswith("!")]
                raise SystemExit(f"{name} ({base}) failed:\n"
                                 + "\n".join(errs[:20]))
        log = (BUILD / f"{base}.log").read_text(encoding="utf-8",
                                                errors="replace")
        problems = [l for l in log.splitlines()
                    if "undefined" in l.lower() and "warning" in l.lower()]
        if problems:
            print(f"[make_submission] WARNING ({base}) — unresolved "
                  "references/citations:")
            for p in problems[:20]:
                print("  " + p)

    build_doc("main")
    build_doc("si")
    build_doc("compact")
    shutil.copy(BUILD / "main.pdf", OUT / PDF_NAME)
    shutil.copy(BUILD / "si.pdf", OUT / "CertGate_SI.pdf")
    shutil.copy(BUILD / "compact.pdf", OUT / "CertGate_compact.pdf")
    print(f"[make_submission] wrote {OUT / PDF_NAME}, "
          f"{OUT / 'CertGate_SI.pdf'} and {OUT / 'CertGate_compact.pdf'}")


if __name__ == "__main__":
    main()
