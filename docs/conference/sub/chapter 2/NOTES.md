# Chapter 2 – working notes

Structure: 2.1 Automated Game Playtesting, 2.2 Game Difficulty and Behavioral Performance Measures, 2.3 Related Work, 2.4 Research Gap and Positioning.

## Versions

Same layout as Chapter 1: one folder per version, frozen once sent to a supervisor. The tools are shared from `../chapter 1/`.

| Version | Date | Status | Notes |
|---|---|---|---|
| v1 | 2026-10-15 | frozen | First draft, aligned with the proposal's Reference Tracing (1.1 Difficulty and Its Impacts, 1.2 Automatic Playtesting) and the supervisors' comments. 23 references from the pool in `../chapter 1/number_refs.py`: 14 of Chapter 1's, the 7 spare entries, plus the proposal's Guzsvinecz and Klepek (Dark Souls). |
| v2 | 2026-10-15 | working | v1 paraphrased into the proposal's voice ("classical yet highly powerful", "also noteworthy", "LLMs can indeed be employed", "there are two types of difficulty", "operationalized through the guess count", "To accommodate this gap"). Same structure, content and 24 references; first person "we" for the debate choice and positioning. |

## Build

From inside the version folder:
`python3 "../../chapter 1/number_refs.py" chapter-2.src.md chapter-2.md`

Numbering restarts at [1] in this chapter. When the chapters are merged into one paper, build the merged source once so that the numbers run across the whole paper.

## Alignment with the proposal

| Proposal | Chapter 2 |
|---|---|
| 1.1 fun and accomplishment, Dark Souls, souls-like [2], [14], [15] | 2.2 P1 |
| 1.1 Constant: subjective (skill, stress, emotion) vs objective | 2.2 P2 |
| 1.2 APLib goal structures and DSLs, programming effort (credited to Prasetya, not Alvarado Villa) | 2.1 P2 |
| 1.2 Francillette: deterministic, platformer only, complex setup | 2.1 P2 |
| 1.2 Xiao: worse play, human-like difficulty patterns, handicap system | 2.1 P4 |
| 1.2 Zhao: match-3, numerical board, code coverage and bugs | 2.1 P4 |
| 1.2 Bateni: long-term planning, adapts to rule changes | 2.1 P4 |
| Background: Delfosse, no natural human behavior | 2.1 P3 |
| Background: "automated consensus frameworks remain absent" | 2.4 P2 |
| 3.2 Liang "tit for tat" with a managing agent | 2.3 P3 |
| 5 guess count proxy, 3.2 vs 5.8 example, no demographics; RQ1 SD; RQ2 correlation | 2.2 P4–P5 |
| Supervisor II: why debate | 2.3 P4 |
| Supervisor II: random sample, population not individuals | 2.2 P5 |

RQ3 (persona behavior) added on 2026-10-15: MIMIC in 2.3 P2, Baltaji in 2.3 P3, and a third open question in 2.4.

Table 2.1 (related-study comparison) removed on 2026-10-15 as redundant with 2.3–2.4.

Left out on purpose (outside the conference scope): Slay the Spire as a case study, the single-agent comparison, the token-ratio cost, and the expert evaluation (RQ3).

## TODO: verify before submitting

1. Each claim about a cited paper against the paper itself, especially these:
   - ChatEval [chan2024]: that role diversity matters to its results.
   - Guzsvinecz [guzsvinecz2024]: the book editors (copied from the proposal, where they match the authors).
2. Klepek [klepek2017] is a Vice magazine article. A conference reviewer may want a scholarly source for the souls-like sub-genre.
3. 2.3 P4 justifies Liang-style debate (a managing agent, opposing positions). Check that it matches the protocol described in Chapter 3. Pilot-02 uses playstyle advisors (Bold, Cautious, Casual) under a GM, not the Negative/Positive pair in the proposal.
4. Add the 7 spare entries, Guzsvinecz/Klepek and Baltaji/Chen (MIMIC) to `../chapter 1/references.bib` before building a docx with Zotero.
5. "LLM outputs vary between calls" (2.4, and 1.2 in Chapter 1) still has no source.
