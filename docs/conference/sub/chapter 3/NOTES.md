# Chapter 3 – working notes

Method chapter for the thesis report: the persona-based multi-agent debate playtester and the final study that validates it (`docs/experiments/final-plan.md`).

Structure of v2: 3.1 Playtester Design (3.1.1 Personas, 3.1.2 Bridge and Game Knowledge, 3.1.3 Debate Protocol, which now also carries the prompt anatomy and the example game of Figure 3.2), then Appendix A with the full prompt texts, 3.2 Human Baseline, 3.3 Study Design (3.3.1 Conditions, 3.3.2 Puzzles and Sample Size, 3.3.3 Configuration and Run), 3.4 Measures (3.4.1 Consistency, 3.4.2 Agreement, 3.4.3 Persona Behavior, 3.4.4 Contrasts and Robustness Checks).
v1 had a shorter structure: 3.3 Experiment Design and 3.4 Measures, without subsections.

## Versions

Same layout as Chapters 1 and 2. The tools are shared from `../chapter 1/`.

| Version | Date | Status | Notes |
|---|---|---|---|
| v1 | 2026-10-28 | superseded | Compact version of Section 3 of `docs/thesis-1/thesis-progress-report.md`. About 1,500 words, 2 figures, 3 tables, 13 references. Cites by number only, without author names. RQ3 is the conference RQ3 (persona behavior), so the measures table adds the persona statistics. Describes the **pilot** method: Experiments A and B, quartiles, 12-guess handicap, sequential debate, temperature 0.2. |
| v2 | 2026-11-11 | working | Rewritten from `final-plan.md` to the **final study**: three conditions (C1 persona debate, C2 single agent, C3 debate without personas), one balanced design of 100 puzzles × 10 runs × 3 conditions, terciles 4.07 / 4.42, six-guess limit with a loss scored 7, parallel debate protocol, frozen vB model configuration, and the analysis tests (Wilcoxon contrasts with Holm, position-matched persona check). About 4,600 words, 3 figures, 4 tables. On 2026-11-12 the supervisor's review added the prompt anatomy and Table 3.2 (the instruction and task of every agent) to 3.1.3, and the example game (Figure 3.2, puzzle 1008) both inside 3.1.3. The verbatim prompt texts moved to Appendix A, so the main tables are 3.1 personas, 3.2 conditions and 3.3 measures, and the pipeline figure is 3.3. |

## Build

From inside the version folder:

```bash
python3 "../../chapter 1/number_refs.py" chapter-3.src.md chapter-3.md
python3 ../../../../.agents/skills/thesis-writing-style/check_style.py chapter-3.md
```

Numbering restarts at [1] in this chapter, as in Chapter 2. v2 draws 14 references.

The assembled paper (`../../build_paper.py`) includes a chapter by path from its `CHAPTERS` map, which still lists `sub/chapter 3/v1/chapter-3.src.md`. Bump that line to `v2` before rebuilding `conference.tex`. The build reads images relative to `docs/conference/`, so the chapter's image paths are written from there and not from the version folder.

## Figures

v2 uses the two standalone TikZ figures of the conference paper rather than the Mermaid drawings of v1, so there is one source per figure:

| Chapter | File |
|---|---|
| Figure 3.1, the playtester | `../../final-conference/figures/fig-architecture-tikz.png` (`fig-architecture.tex`) |
| Figure 3.2, one game | `../../final-conference/figures/fig-example-tikz.png` (`fig-example.tex`) |
| Figure 3.3, the study pipeline | `../../final-conference/figures/fig-pipeline-tikz.png` (`fig-pipeline.tex`) |

Rebuild after editing a `.tex`: `pdflatex <name>.tex`, then `pdftoppm -r 300 -png -singlefile <name>.pdf <name>-tikz`. The figures are 17 cm wide, so they are placed at full text width and the smallest labels print at about 5 pt. v1 used `docs/thesis-1/figures/fig-framework.png` and `fig-debate.png`; the second one draws the pilot's sequential protocol and must not be reused.

The pipeline figure was relabeled on 2026-11-11: `RQ3 persona behavior` became `persona behavior`, since Chapters 1 and 2, the conference paper and Section 3.4 of this chapter all use two research questions plus a descriptive persona analysis. The `puzzle list` arrow label was shortened to `puzzles` so that it fits between the panels.

## Changes from v1 (pilot method) to v2 (final study)

| Item | v1 pilot | v2 final study |
|---|---|---|
| Conditions | persona debate only | C1 persona debate, C2 single agent, C3 debate without personas |
| Design | two experiments, 12 × 32 and 48 × 3 | 100 puzzles × 10 runs × 3 conditions, paired by puzzle |
| Categories | quartiles 3.98 / 4.24 / 4.53 | terciles 4.07 / 4.42, quartiles kept as a sensitivity check |
| Guess limit | hidden 12-guess handicap, read at 6 and 12 | 6 guesses, a loss scores 7 |
| Debate | sequential, advisors read the earlier suggestions of the round | parallel, advisors answer independently within a round |
| Model | DeepSeek-V4.1-Flash, thinking disabled, temperature 0.2, 1,024-token reply limit | deepseek-flash, thinking enabled at low effort, 8,192 tokens, JSON mode, no temperature |
| Measures | ICC(1,1)/ICC(1,k), Pearson/Spearman, bias/MAE, quartiles, retention, adoption, non-candidate share | the same families on terciles, plus ICC(1,10) with F intervals, the constant-guess baseline, bias-corrected MAE, QWK, same-word share and the position-matched persona check |
| Analysis | bootstrap intervals | Wilcoxon contrasts with Holm, p-values, no resampling |
| Protocol figure | `fig-debate.png` (sequential order) | removed, because the drawing shows the pilot order; the parallel rule is described in 3.1.3 instead |

Deliberately left out of v2: the protocol figure, the formula for the ICC, and the expert evaluation. The measures table stays here, since a method chapter is expected to define them. The conference paper takes the opposite decision: its Section III has no measures, which are defined at first use in the results.

## Compared with the thesis report

This table maps **v1** onto the progress report. v2 keeps the same content in the new structure, with the changes listed above.

| Thesis report | Chapter 3 |
|---|---|
| 3.1 Existing methods | Left out (covered by Chapter 2) |
| 3.2 Requirements, LLM choice, participants | Left out. The model settings are in 3.3.3. |
| 3.3.1 Framework, Figure 1 | 3.1, Figure 3.1 |
| 3.3.2 Personas, Table 1 | 3.1.1, Table 3.1 (the Casual opener detail dropped) |
| 3.3.3 Bridge, 3.3.5 Game knowledge | 3.1.2, merged. The JSON detail dropped. |
| 3.3.4 Debate protocol, Figure 2 | 3.1.3, text only |
| 3.3.6 Turn statistics | 3.4.3 |
| 3.4.1 Study pipeline, Figure 3 | 3.3, now Figure 3.3 |
| 3.4.2 Human data, Figure 4 | 3.2, text only |
| 3.4.3 Pilot design, Table 2 | 3.3.2, the final design |
| 3.4.4 Measures | 3.4, Table 3.3 |

## TODO: verify before submitting

1. Done 2026-11-11: v2 no longer calls the runs a pilot. The pilot appears only as the earlier study that the final design replaced.
2. Done 2026-10-28: all 34 citation keys of Chapters 1–3 are in Zotero, and `../../conference.docx` builds with live citations (`python3 docs/conference/build_docx_paper.py`, Zotero running). `koo2016` was added on 2026-11-11 to `../chapter 1/number_refs.py` and still needs an entry in `../chapter 1/references.bib` and in Zotero before that docx build.
3. Chapter 2 TODO 3 (Liang-style debate vs the protocol here) is answered by 3.1.3: a managing GM with three playstyle advisors, under the parallel rule.
4. The power argument in 3.3.2 comes from the simulation in `docs/experiments/final-power-sim.py`. If the supervisors want it as a figure or an appendix, `final-plan.md` Section 5 holds the table.
5. 3.3.3 reports cost and runtime. If the budget should stay out of the method, that sentence can move to the results chapter.
6. 3.1.3 states that the pilot's sequential protocol was replaced. The full statement, with the same-word shares that motivated it, stays in `final-plan.md` Section 7.1.
