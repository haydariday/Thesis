# Chapter 3 – working notes

Structure: 3.1 Playtester Design (3.1.1 Personas, 3.1.2 Bridge and Game Knowledge, 3.1.3 Debate Protocol), 3.2 Human Baseline, 3.3 Experiment Design, 3.4 Measures.

## Versions

Same layout as Chapters 1 and 2. The tools are shared from `../chapter 1/`.

| Version | Date | Status | Notes |
|---|---|---|---|
| v1 | 2026-10-28 | working | Compact version of Section 3 of `docs/thesis-1/thesis-progress-report.md`. About 1,500 words, 2 figures, 3 tables, 13 references. Cites by number only, without author names. RQ3 is the conference RQ3 (persona behavior), so the measures table adds the persona statistics. |

## Build

From inside the version folder:
`python3 "../../chapter 1/number_refs.py" chapter-3.src.md chapter-3.md`

The paper (`../../build_paper.py`) now includes this chapter. Its preamble gained graphicx, longtable/booktabs and a ρ mapping for the figures and tables. Figures are read from `docs/thesis-1/figures/`. In the docx, the figures span both columns and the cross-references become Fig. 1 and Table I, as the template numbers them.

## Compared with the thesis report

| Thesis report | Chapter 3 |
|---|---|
| 3.1 Existing methods | Left out (covered by Chapter 2) |
| 3.2 Requirements, LLM choice, participants | Left out. The model settings are in 3.3. |
| 3.3.1 Framework, Figure 1 | 3.1, Figure 3.1 |
| 3.3.2 Personas, Table 1 | 3.1.1, Table 3.1 (the Casual opener detail dropped) |
| 3.3.3 Bridge, 3.3.5 Game knowledge | 3.1.2, merged. The SLATE example and JSON detail dropped. |
| 3.3.4 Debate protocol, Figure 2 | 3.1.3, Figure 3.2 |
| 3.3.6 Turn statistics | 3.4 (RQ3 rows of Table 3.3 and the last paragraph) |
| 3.4.1 Study pipeline, Figure 3 | Left out. The no-leak sentence moved to 3.1.2. |
| 3.4.2 Human data, Figure 4 | 3.2, text only |
| 3.4.3 Pilot design, Table 2 | 3.3, Table 3.2 (seeds dropped) |
| 3.4.4 Measures | 3.4, Table 3.3 |

## TODO: verify before submitting

1. The text calls the study "the study" with Experiments A and B. Only the Julious sentence still says "pilot study". Decide whether the paper presents these runs as a pilot.
2. Done 2026-10-28: all 34 citation keys of Chapters 1–3 are in Zotero, and `../../conference.docx` builds with live citations (`python3 docs/conference/build_docx_paper.py`, Zotero running).
3. Chapter 2 TODO 3 (Liang-style debate vs the protocol here) is now answered by 3.1.3: a managing GM with three playstyle advisors.
