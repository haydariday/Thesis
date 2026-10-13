# Thesis Title Refactor and Alignment

## 1. Why the current title does not fit

Current title: **Multi-Agent LLM Debate for Consensus-Based Difficulty Assessment in Automatic Playtesting**

| What the title suggests | What the design actually does |
|---|---|
| The LLM agents assess or judge difficulty | The LLM agents **play** the game (Wordle, Slay the Spire) as automated playtesters |
| Consensus is reached on a **difficulty verdict** | Consensus is reached on the **next in-game action** (a guess, a card, end turn) |
| Difficulty is the LLM's output | Difficulty comes from **playtest outcomes** (guess count, remaining HP), which are then correlated with **human performance baselines** |

Terms to drop or move: "Difficulty Assessment" and "Consensus-Based" as modifiers of difficulty. Consensus belongs to action selection, so it can stay in the abstract and method but should not describe difficulty in the title.

This reframing also answers Supervisor I's note ("perlu lebih diperjelas bagaimana seluruh agent mencapai consensus"): the agents reach consensus per action, inside a playtesting loop.

---

## 2. Title options

Constraints applied: debate-as-playtester first, persona/playstyle included, human baseline included, English.

1. **Persona-Based Multi-Agent LLM Debate as an Automated Playtester: Validating Game Difficulty Data Against Human Performance Baselines** (recommended)
2. Multi-Agent LLM Debate Playtesters with Diverse Playstyle Personas for Evaluating Game Difficulty Against Human Performance Baselines
3. Debating Playtesters: Persona-Driven Multi-Agent LLM Agents for Human-Aligned Game Difficulty Evaluation
4. Automated Playtesting via Persona-Based Multi-Agent LLM Debate: Correlating Playtest Outcomes with Human Performance for Game Difficulty Evaluation

Why option 1:
- **"Multi-Agent LLM Debate as an Automated Playtester"** makes the debate framework the thing being built, and makes clear that it plays the game.
- **"Persona-Based"** covers the Negative/Positive and Aggressive/Defensive/Velocity advisor agents.
- **"Game Difficulty Data"** says the framework produces data about difficulty. It does not judge difficulty itself.
- **"Validating ... Against Human Performance Baselines"** matches RQ2, which correlates results with engaging-data.com and the Slay the Spire human dataset.

Shorter variant if a length limit applies:
**Persona-Based Multi-Agent LLM Debate Playtesters for Human-Aligned Game Difficulty Evaluation**

---

## 3. Aligned proposal text (before → after)

### 3.1 Topic Summary

Paragraph 1, last sentence:
- Before: "Recent single-agent LLM frameworks demonstrate cross-genre difficulty measurement capability but fail to capture the diversity of player play styles..."
- After: "Recent single-agent LLM playtesters produce play outcomes that reflect human-perceived difficulty across genres, but a single agent fails to capture the diversity of player play styles, achieving only limited accuracy when modeling heterogeneous personas."

Paragraph 2 (replace whole paragraph):
> The proposed framework uses structured multi-agent debate as an automated playtester. At every game turn, a GM Agent proposes an action while Advisor Agents with distinct playstyle personas critique it from opposing strategic perspectives, and the agents reach consensus on the action to execute through iterative argumentation. The resulting playthrough outcomes serve as objective difficulty data, which is validated against human performance baselines. This shifts automated playtesting from a single agent's playstyle to decisions that combine several playstyle perspectives. The study employs Wordle and Slay the Spire as case studies.

Paragraph 3 (replace whole paragraph):
> Three research questions guide the investigation: (1) the consistency of the playtester's outcomes across repeated runs in distinct game genres, measured by outcome variance; (2) how well its playtest outcomes correlate with human performance baselines, and at what computational cost, compared with a single-agent LLM playtester; and (3) industry expert evaluations of the practical utility and efficacy of the playtester and its data for difficulty evaluation. Ground truth derives from empirical human performance data: guess counts for Wordle and remaining HP for Slay the Spire.

Paragraph 4 (replace whole paragraph):
> The research contributes methodologically by introducing a persona-based multi-agent debate playtester whose consensus-driven play produces difficulty data; empirically by quantifying the human-alignment versus cost trade-off of multi-agent versus single-agent playtesters; and practically by providing expert-validated guidelines for using LLM playtesting in resource-constrained game development workflows.

### 3.2 Background (last two paragraphs)

- Before: "While multi-agent debate could reconcile these heterogeneous strategies into unified metrics, automated consensus frameworks remain absent from current difficulty assessment methods. However, whether such automated consensus mechanisms provide actionable insights..."
- After: "Multi-agent debate could combine these different strategies into each in-game decision, but no current LLM playtesting framework uses debate-based consensus to produce difficulty data. Whether the data from such a playtester gives game designers actionable insights and matches professional difficulty evaluation practice is still an open question that needs expert validation."

- Before: "This paper develops a multi-agent LLM debate consensus mechanism for automated difficulty assessment."
- After: "This research develops a persona-based multi-agent LLM debate framework that acts as an automated playtester, generating play outcome data for evaluating game difficulty."

- Before: "...empirical validation within difficulty measurement contexts remains necessary. This comparison quantifies the incremental benefit of debate-based consensus in terms of correlation with human performance baselines..."
- After: "...empirical validation in the context of playtesting for game difficulty remains necessary. This comparison quantifies how much debate-based consensus adds, measured as the correlation between playtest outcomes and human performance baselines, together with the extra computational cost."

### 3.3 Research Questions

- **RQ1.** To what extent does the persona-based multi-agent debate playtester produce consistent playtest outcomes across repeated runs in Wordle and Slay the Spire?
- **RQ2.** How do the playtest outcomes of the multi-agent debate playtester compare with those of a single-agent LLM playtester in terms of correlation with human performance baselines and computational cost?
- **RQ3.** How do industry experts evaluate the utility and efficacy of the multi-agent debate playtester and its playtest data for evaluating game difficulty?

### 3.4 Objectives

1. To implement a persona-based multi-agent LLM debate framework that acts as an automated playtester, selecting in-game actions through consensus and logging play outcomes as difficulty data.
2. To evaluate the consistency of the playtester's outcomes across distinct game genres (Wordle and Slay the Spire), and to validate their correlation with human performance baselines and their computational cost against a single-agent LLM playtester.
3. To gather expert evaluations of the utility and efficacy of the multi-agent debate playtester and its data for game difficulty evaluation in game development workflows.

### 3.5 Hypotheses

- **H1.** The multi-agent debate playtester produces consistent playtest outcomes (low outcome variance) across repeated runs in both Wordle and Slay the Spire.
- **H2.** Playtest outcomes from the multi-agent debate playtester correlate more strongly with human performance baselines than those from a single-agent LLM playtester, at a higher computational cost.
- **H3.** Industry experts will evaluate the multi-agent debate playtester as a viable automated playtester for game difficulty evaluation.

(Also fixes the original H2 typo: "higher computational" → "higher computational cost".)

### 3.6 Smaller wording fixes elsewhere

| Section | Before | After |
|---|---|---|
| 1.1, last sentence | "this study leverages LLMs to predict empirical difficulty metrics—specifically, human performance baseline data—automating the measurement of objective behavioral outcomes." | "this study uses LLM agents as automated playtesters whose play outcomes serve as objective difficulty data, validated against human performance baselines." |
| 1.2, Xiao et al. | "LLMs can indeed be employed to measure game difficulty" | "LLM agents can be employed as playtesters whose outcomes reflect game difficulty" |
| 3, Figure 1 caption | "The multi-agent debate playtester framework" | Keep (already correct) |
| 5, ground truth | "the human performance proxy that the LLM frameworks attempt to predict" | "the human performance proxy against which the LLM playtesters' outcomes are compared" |
| 5, RQ1 text | "reliability is assessed through outcome variance" | "consistency of playtest outcomes is assessed through outcome variance" |
| 5, RQ2 text | "to determine which better predicts actual human difficulty" | "to determine which playtester's outcomes better track human performance" |
| 5, RQ2 text | "predictive validity is measured by the Pearson correlation" | "human alignment is measured by the Pearson correlation" (or keep "predictive validity" if your supervisors prefer the psychometric term) |

---

## 4. Note

Both supervisors marked the old title "OK", and the proposal header says "HARUS BERKONSULTASI DENGAN PEMBIMBING". Present option 1 with the table in Section 1 as the reason for the change.
