# Chapter 1 – working notes

Working title: **Persona-Based Multi-Agent LLM Debate as an Automated Playtester: Validating Game Difficulty Data Against Human Performance Baselines**
Scope: conference scope (Wordle only, RQ1 consistency, RQ2 human difficulty alignment). This follows the repo roadmap. The single-agent comparison, Slay the Spire, and expert evaluation are out of scope.

## Files

- `chapter-1.md`: final text with IEEE numbers (paste into Word).
- `chapter-1.src.md`: the source with citation keys such as `[@xiao2025]`. Edit this file, then rebuild:
  `python3 number_refs.py chapter-1.src.md chapter-1.md`
  `number_refs.py` also holds unused entries (Bateni, Chan, Holmgård, Gudmundsson, Smit, StS dataset) for later chapters.

## Word / OnlyOffice export (live Zotero citations)

- `references.bib`: the 15 Chapter 1 references, using the same keys as `chapter-1.src.md`. Import it into Zotero (with Better BibTeX) via File > Import, into the collection `Thesis – Chapter 1`.
- `./build_docx.sh` builds `chapter-1.docx` with pandoc and `zotero.lua` (BBT's filter). Zotero must be running.
- In OnlyOffice (Plugins > Zotero, desktop mode) or Word (Zotero tab), choose IEEE, then Refresh. Then put the cursor under "References" and use Insert/Add Bibliography, because zotero.lua only inserts the bibliography for .odt output.
- If you add a citation: add it to Zotero, keep its Citation Key equal to the `[@key]` in the source, then rebuild.

## Structure: 1.1 Background, 1.2 Problem Identification, 1.3 Objective and Hypotheses

| Background paragraph | Role | Rubric criteria |
|---|---|---|
| P1 | Difficulty, manual playtesting cost, need for cheap human-like difficulty evidence | 1, 2 |
| P2 | Existing approaches, single-agent LLM gap, specific problem | 1, 2, 4 |
| P3 | "To accommodate this gap, we establish...", key terms, consensus on actions (protocol details deferred to the method chapter, where Supervisor I's consensus question must be answered) | 2, 6 |
| P4 | Why Wordle, method overview, scope limits, contribution | 6, 7, 8 |

## Changes from the proposal

- Reframed from "difficulty assessment" to "automated playtester that produces difficulty data".
- Background, paragraph 2: the proposal put deep learning next to [5], but Prasetya et al. (APLib) uses programmed agents. Deep RL is now cited to Delfosse et al.
- The proposal's Background credited APLib to "Alvarado Villa et al.", which was wrong; it is now credited to Prasetya et al.
- RQs, objectives, and hypotheses were rewritten for the conference scope. H2 uses the majority-class baseline, as in `experiments/pilot-01/metrics.json`.
- Reference list converted from the Indonesian Mendeley locale to English IEEE.

## TODO: verify before submitting

1. [8] Delfosse et al.: add the arXiv ID.
2. [15] Engaging Data: check the page title and add the access date.
3. The scope change (thesis scope narrowed to the conference scope) still needs the supervisors' approval.

## Deferred to the method chapter

- Why debate (Supervisor II): the debate-justification paragraph (Liang et al., Du et al.) was removed from Chapter 1 for flow. Its citation entries remain in `number_refs.py` for reuse.
