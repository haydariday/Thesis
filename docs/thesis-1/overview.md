# Thesis 1 (TA 1): First Monitoring Overview

This folder holds the material for the first monitoring (*Pemantauan ke-1*) of Thesis 1 (*Tugas Akhir 1*) in the S2 Informatics programme. The source is the programme announcement "Teknis Pemantauan Ke-1 Tugas Akhir 1 S2 IF".

Templates and the submission folder are on the programme page: <https://linktr.ee/miftelkomuniversity>. This includes the LogBook, the Thesis Report, the recommendation letter and the monitoring schedule.

## Timeline

All times are WIB (UTC+7).

| Date | Event |
|---|---|
| **25 October 2026, 23:59** | Deadline to register for the first monitoring of TA 1 (16:59 UTC). |
| 30 October 2026 | Last day of monitoring for students repeating TA 1 only. |
| **2–13 November 2026** | First monitoring of TA 1. Weekdays, working hours. |

## Requirements

Every item is needed for registration.

- [ ] **Supervision.** At least two supervision meetings, recorded in the LogBook.
- [ ] **Thesis Report.** A PDF in English, written on the programme template.
- [ ] **Recommendation letter.** The *Surat Rekomendasi Pemantauan*, signed by the supervisor (PBB).
- [ ] **Slides.** The presentation file or a link to it.
- [ ] **Video.** A recorded monitoring presentation in English. It is at most 15 minutes long. The link must not be private.
- [ ] **SK TA and progress seminar (recommended).** Continue the *Pengajuan SK TA* and the *Penjadwalan Seminar Kemajuan* in iGracias under *Tugas Akhir Pascasarjana*. Follow the steps the application gives.

## Draft

The report content is drafted in `thesis-progress-report.md`, following the template's section order. `build_docx.py` fills the Word template with it and writes `thesis-progress-report.docx` with live Zotero citations:

1. Import `zotero-import-new.bib` into Zotero once (Thompson 1987 and Julious 2005), keeping the keys `thompson1987` and `julious2005`.
2. Start Zotero with Better BibTeX, then run `python3 docs/thesis-1/build_docx.py` (`--plain` builds without Zotero, for a layout check only).
3. Open the .docx in OnlyOffice > Plugins > Zotero, choose IEEE and Refresh. Put the cursor in the empty paragraph under "References" and insert the bibliography.
4. Fill in the "Reported on" date on the cover.

Figures 1 to 3 in section 3.3 are Mermaid sources in `figures/*.mmd`. After editing one, run `figures/render.sh` to redraw the PNGs (set `CHROME=` to a Chrome binary if puppeteer has none), then rebuild the .docx.

## Templates

The programme templates are in `template/`.

| File | Purpose |
|---|---|
| `template/FORMAT THESIS PROGRESS REPORT in Word.docx` | The Thesis Report. It must be discussed with the supervisors (*harus berkonsultasi dengan pembimbing*). |
| `template/Template Surat Rekomendasi Pemantauan.docx` | The recommendation letter, signed by both supervisors. |

### Recommendation letter fields

| Field | Value |
|---|---|
| Pembimbing 1 | Dr. Arfive Gandhi S.T., M.T.I. (NIP: to fill) |
| Pembimbing 2 | Dr. Eng. Jati Hiliamsyah Husen S.T., M.Eng. (NIP: to fill) |
| Mahasiswa | Muhammad Haydar Maulana, NIM 203012510020 |
| Tugas Akhir (....) | 1 |
| Place and date | Bandung, ... 2026 |

Keep Pembimbing 2 in the letter. The footnote "\*jika tidak ada bisa dihapus" only applies when there is no second supervisor.

### Thesis Report header

| Field | Value |
|---|---|
| Reported on | MM/DD/YYYY of submission (on or before 10/25/2026) |
| Research Title | Persona-Based Multi-Agent LLM Debate as an Automated Playtester: Validating Game Difficulty Data Against Human Performance Baselines |
| Submitted by | Muhammad Haydar Maulana [203012510020] |
| Concentration | Informatics Software Engineering |
| E-mail | haydariday@gmail.com |
| Supervisor (I) | Dr. Arfive Gandhi S.T., M.T.I. |
| Supervisor (II) | Dr. Eng. Jati Hiliamsyah Husen S.T., M.Eng. |

The title is the current conference-paper title (`docs/conference/build_paper.py`). It replaces the proposal title "Multi-Agent LLM Debate for Consensus-Based Difficulty Assessment in Automatic Playtesting" (20-06-2026), so the supervisors should confirm the change.

## Thesis Report sections and sources

Each template section maps to material that already exists in this repository.

| Template section | Content | Source |
|---|---|---|
| Progress Summary (max 500 words) | Scope change, system built, pilot-02 done, early RQ1/RQ2 results | Roadmap, `docs/experiments/pilot-02-plan.md`, pilot-02 `metrics.json` |
| Previous revisions table | Revisions since the proposal (title, scope, RQs, personas) | See below |
| Background | Cost of manual playtesting, limits of current automated methods, the gap in persona diversity and consensus | Proposal Background, conference chapter 1 (`docs/conference/sub/chapter 1/`) |
| Objective and Hypotheses | RQ1 (outcome consistency over repeated runs), RQ2 (alignment with human difficulty) and RQ3 (expert evaluation, unchanged from the proposal) | Proposal, roadmap, conference chapter 1 v2 (1.3, 1.4) |
| Existing software/system/method | Heuristic, RL and single-agent LLM playtesters, multi-agent debate | Conference chapter 2 (`docs/conference/sub/chapter 2/`) |
| Requirement specification | Public feedback only, no answer or human scores in prompts, JSON decisions with repair, full call logging, resumable runner | `CLAUDE.md` Architecture, `src/multi_agent_testing/` |
| Design | Data flow with the playtester boundary (Figure 1), framework (Figure 2), bridge, debate protocol with a real pilot-02 turn (Figure 3), game knowledge, personas | `orchestra/flow/sequential.py`, `orchestra/debate.py`, `agent/personas.py` |
| Implementation result | Inputs, process, outputs and environment: DeepSeek backend, LangGraph, run JSON, `run_summary.csv` | `experiment/runner.py`, `run_log.py`, `experiments/*/experiment_config.json` |
| Experiment result | Pilot-02 wide (48 × 3) and deep (12 × 32) under configuration vA. Do not report other pilots. | `experiments/pilot-02-va-wide/`, `experiments/pilot-02-va-deep/`, `experiments/pilot-02-va-analysis/` (metrics and figures) |
| Analysis of the experiment result | Within-puzzle SD, ICC, exact-match. MAE, Spearman, Kendall tau, D1–D4 confusion, weighted kappa. Distribution comparison and persona statistics | `experiment.analysis_pilot02` outputs |
| Schedule Realization | Planned versus actual dates for each activity | Proposal Timetable, git history of `pilot-2` |

### Results to report (minimum set)

Section 3.5 reports only the metrics that the RQ wording and the hypotheses name. The rest stays in `experiments/pilot-02-va-analysis/metrics.json` for the thesis. RQ3 is the expert evaluation, so it has no pilot metrics. The persona statistics are not reported. All values are configuration vA with 95% puzzle-bootstrap CIs.

**RQ1, Exp A (deep, 12 puzzles × 32 runs).** Keep the two scale columns (raw 12-guess and the 6-guess Wordle scale).

| Metric | What it tells the reader | 12-guess | 6-guess |
|---|---|---|---|
| Mean within-puzzle SD (H1) | How much one puzzle varies from game to game, in guesses | 1.53 [1.22, 1.83] | 0.96 [0.82, 1.10] |
| ICC(1,1) | Whether puzzle differences stand out from the noise of one game | 0.49 [0.24, 0.63] | 0.55 [0.25, 0.71] |
| ICC(1,k), k = 32 | The same for the averaged score that is used; it also justifies the runs per puzzle | 0.97 [0.91, 0.98] | 0.98 [0.91, 0.99] |

**RQ2, Exp B (wide, 48 puzzles × 3 runs), with Exp A as a check column.** The ranking measures use the raw 12-guess scores, while the level measures use the 6-guess scale.

| Metric | Part of the RQ | Wide | Deep (check) |
|---|---|---|---|
| Spearman ρ (primary) | Average scores: the same order? | 0.34 [0.11, 0.56] | 0.72 [0.38, 0.95] |
| Signed error (bias) | Average scores: how far off in level | +1.28 [1.00, 1.55] | +1.04 [0.53, 1.50] |
| MAE | Average scores: how far off in level | 1.38 [1.15, 1.61] | 1.26 [0.95, 1.54] |
| Rank-based D1–D4: weighted κ | Difficulty categories | 0.27 [0.05, 0.53] | 0.53 [0.27, 1.00] |
| Rank-based D1–D4: adjacent agreement | Difficulty categories | 0.65 [0.54, 0.81] | 0.83 [0.67, 1.00] |

In the text only:
- **Constant baseline.** Predicting the all-puzzle human mean of 4.28 for every puzzle gives an MAE of 0.28 on the wide puzzles, yet it cannot rank any puzzle. That is why MAE is reported with the bias and not alone.
- **Pearson r.** Wide 0.30 [0.10, 0.51], one line for comparison with Xiao and Yang.
- **Rank-based D1–D4.** The system means are ranked among themselves and split into four equal groups (`quartiles.rank_split`), which are compared with the human quartiles. The value-based split is not used, since the bias puts most puzzles in D4.

The pasted selection had two numbers from other cells. The SD of 0.85 is the wide experiment (3 runs per puzzle) on the 6-guess scale, while RQ1 uses the deep 0.96. The adjacent agreement of 0.71 is on the 6-guess scale, while the 0.65 above matches the raw scale of ρ and κ.

**Left out of the report (thesis only):**
- Kendall τ, which repeats ρ.
- Value-based D1–D4 exact rate and κ, including the "39 of 48 puzzles in D4" sentence and the matching sentence in the Progress Summary.
- Bland-Altman limits.
- Exact-match rate and win rate.
- The 7-bin distribution measures (W1, chi-square, split-half), cut to at most one sentence. Check with the supervisor, since they asked for it.
- The completion and cost table, cut to one sentence: 525 games, about 70 s and 85k tokens per game.

Figures stay as F2 (RQ1 spread) and F5 (RQ2 means and ranks). Sections 4.2 and 4.4 and H2 already judge RQ2 by rank order and categories, so they stay consistent with this set.

### Previous revisions table

The "Comments/Feedback from Reviewers" column stays blank. The "Updates" column lists the revisions since the proposal: the title, the scope, the RQs and the personas.

### Schedule Realization rows

The template rows match the proposal timetable. The proposal gives months 1–12 without calendar dates, so the actual start and end dates have to be filled in by hand. Git history on `pilot-2` and the dates in the roadmap help for the implementation and experiment rows.

| Template activity | Proposal sub-activities |
|---|---|
| Reference tracing | Automatic playtesting, game difficulty, gap identification |
| Requirement identification | LLM and expert profile, RQs, hypotheses and scope |
| Design process | Bridge, debate protocol, data logging |
| Implementation process | Wordle prototype (Slay the Spire dropped) |
| Experiment design and plan | Ground truth data acquisition, RQ1 and RQ2 |
| Analysis/Evaluation | Quantitative analysis |

## Suggested presentation outline (15 minutes)

1. Problem and motivation: manual playtesting is costly. Can an LLM debate act as a playtester? (2 min)
2. Research questions: RQ1 is outcome consistency across repeated runs. RQ2 is alignment with human difficulty. RQ3 is the expert evaluation, unchanged from the proposal. (1 min)
3. System: Game Master, persona advisors, the LangGraph debate flow and the Wordle bridge. (3 min)
4. Data: the human Wordle scores and the frozen D1–D4 cut-points (3.98 / 4.24 / 4.53). (2 min)
5. Pilot-02 design: the deep and wide experiments and configuration vA. (2 min)
6. Early results: RQ1 spread and ICC. RQ2 MAE, rank correlation and D1–D4 agreement. (3 min)
7. Next steps: final-study sizing (P15), the RQ3 expert evaluation and the plan for Thesis 2. (2 min)

## Progress log

| Date | Item | Note |
|---|---|---|
| | | |
