# Thesis 1 Progress Presentation Slides and Script

- **Research Title:** Persona-Based Multi-Agent LLM Debate as an Automated Playtester: Validating Game Difficulty Data Against Human Performance Baselines
- **Submitted by:** Muhammad Haydar Maulana [203012510020]
- **Concentration:** Informatics Software Engineering
- **Supervisor (I):** Dr. Arfive Gandhi S.T., M.T.I.
- **Supervisor (II):** Dr. Eng. Jati Hiliamsyah Husen S.T., M.Eng.
- **Total Duration:** 15 minutes 00 seconds (17 slides, ~2,015 spoken words at ~134 words/minute)

---

## Slide 1: Title Slide (00:00 - 00:30 | 0:30)

- **Title:** Persona-Based Multi-Agent LLM Debate as an Automated Playtester: Validating Game Difficulty Data Against Human Performance Baselines
- **Subtitle:** Thesis 1 Progress Report (First Monitoring)
- **Presenter:** Muhammad Haydar Maulana [203012510020]
- **Program:** Master of Informatics (Concentration: Informatics Software Engineering), Telkom University
- **Supervisors:** Dr. Arfive Gandhi S.T., M.T.I. and Dr. Eng. Jati Hiliamsyah Husen S.T., M.Eng.

**Spoken Script:**

Good morning to my supervisors and the monitoring committee. My name is Muhammad Haydar Maulana, working under the supervision of Doctor Arfive Gandhi and Doctor Jati Hiliamsyah Husen. Today I will present my Thesis 1 progress report on a persona-based multi-agent LLM debate playtester for game difficulty. This presentation covers the five sections of the report, from the background and objectives to the research method, pilot results and analysis.

---

## Slide 2: 1. Background: The Playtesting Cost Problem (00:30 - 01:30 | 1:00)

- **Why Difficulty Matters**
  - "Is the game hard enough for the intended player?" is a central question during game development [2].
  - Games that are too hard drive players away while games that are too easy soon become stale [3].
  - Both outcomes hurt player engagement and retention [4], [5].
- **Limits of Manual Playtesting**
  - Requires many human testers over many sessions and must be repeated after every major design change [2], [6], [7].
  - Cost is often prohibitive for indie game developers with limited budgets.
- **Current Automated Playtesting Approaches**
  - *Hand-crafted methods:* Programmed test agents [6] and mathematical difficulty models [8] demand heavy engineering effort per game.
  - *Learning-based methods:* Deep reinforcement learning requires large training resources while playing in ways that humans would not [9].
  - *LLM agents:* Play games from chess [10] to Pokémon [11] and Minecraft [12] using text rules alone; Xiao and Yang [1] show LLM difficulty in Wordle and Slay the Spire follows human difficulty.

**Spoken Script:**

Section 1 covers the background of the research. During development, game designers keep asking whether their game is hard enough for the intended player [2]. A game that is too hard drives players away while one that is too easy soon becomes stale, both of which risk losing players [3], [4], [5]. Manual playtesting is resource-intensive since it needs many testers over many sessions and has to be repeated after every design change [2], [6], [7]. For indie game developers, this cost is often prohibitive. Programmed test agents [6] and mathematical models [8] need heavy engineering per game, while deep reinforcement learning needs large training resources and plays unlike humans [9]. Large language models instead play games from text rules alone [10], [11], [12]. Xiao and Yang [1] show that the difficulty LLM agents experience in Wordle follows that of human players.

---

## Slide 3: 1. Background: The Gap in Playstyle Diversity and Consensus (01:30 - 02:30 | 1:00)

- **The Research Gap**
  - Existing LLM playtesters rely on a single agent with only one playstyle [1].
  - Real human players are diverse: some take risks while others play safely.
  - Single LLMs replicate human strategic behavior less closely than multi-agent systems do [13].
  - Multi-agent debate could reconcile several playstyles into one consensus action, yet it remains absent from difficulty measurement.
- **Two Conditions Required for a Usable Playtester**
  1. *Outcome consistency across runs:* LLM outputs vary between calls, while Xiao and Yang [1] play 20 runs per puzzle yet report only the mean.
  2. *Agreement with human difficulty:* A consistent playtester that finds every puzzle equally easy is of no use to designers, while practical utility also needs expert validation.
- **Our Approach and Case Study**
  - Persona-based multi-agent LLM debate measuring *objective difficulty* from play outcomes rather than player perceptions [14].
  - Case study: **Wordle** (short games, deterministic feedback, public human baseline, studied in [1]).

**Spoken Script:**

However, existing LLM playtesters rely on a single agent with only one playstyle. Human players are more diverse, as some take risks while others play safely, while single LLMs replicate human strategic behavior less closely than multi-agent systems do [13]. Multi-agent debate could reconcile several playstyles into one consensus action, yet such frameworks remain absent from difficulty measurement. Two conditions must hold before such a playtester can be used. First, its outcomes must be consistent across runs because LLM outputs vary between calls. Xiao and Yang [1] play each Wordle puzzle 20 times yet report only the average, so this consistency remains unknown. Second, its outcomes must agree with human difficulty, while its value for designers also requires expert validation. We therefore establish a persona-based multi-agent LLM debate playtester that measures objective difficulty from play outcomes [14] on Wordle.

---

## Slide 4: 2. Objective and Hypotheses: RQs, Objectives and Hypotheses (02:30 - 03:45 | 1:15)

- **2.1 Research Questions**
  - **RQ1:** How consistent are the Wordle playtest outcomes produced by the persona-based multi-agent debate playtester across repeated runs on the same puzzles?
  - **RQ2:** To what extent do the Wordle difficulty estimates derived from the playtester's outcomes agree with human difficulty, measured by average guess scores and difficulty categories?
  - **RQ3:** How do industry experts evaluate the utility and efficacy of multi-agent LLM debate for automated difficulty testing?
- **2.2 Objectives**
  - **Obj 1:** Implement a multi-agent LLM debate framework that operationalizes difficulty measurement through diverse personas on Wordle.
  - **Obj 2:** Evaluate outcome consistency across repeated runs and validate agreement with human performance baselines (answers RQ1 and RQ2).
  - **Obj 3:** Gather expert evaluations on utility and efficacy in game development workflows (answers RQ3).
- **2.3 Hypotheses (tested in final study; pilot is descriptive)**
  - **H1:** Within-puzzle standard deviation stays below a margin fixed from the pilot results before the final run.
  - **H2:** Ranks puzzles in the same order of difficulty as humans while difficulty categories agree beyond chance.
  - **H3:** Industry experts evaluate the framework as viable for automated playtesting.

**Spoken Script:**

Section 2 defines our research questions, objectives and hypotheses. Under Section 2.1, RQ1 asks how consistent the Wordle playtest outcomes are across repeated runs on the same puzzles. RQ2 asks to what extent the difficulty estimates derived from those outcomes agree with human difficulty, measured by average guess scores and difficulty categories. RQ3 asks how industry experts evaluate the utility and efficacy of multi-agent LLM debate for automated difficulty testing. Under Section 2.2, our three objectives match these questions. First, we implement the persona-based debate framework on Wordle. Second, we evaluate outcome consistency and human agreement for RQ1 and RQ2, after which we gather expert evaluations for RQ3. Under Section 2.3, the pilot study is descriptive, so our three hypotheses are tested in the final study. H1 states that within-puzzle standard deviation stays below a margin fixed from the pilot. H2 states that the playtester ranks puzzles in the same order as humans while its categories agree beyond chance. H3 states that industry experts will evaluate the framework as viable.

---

## Slide 5: 2.4 Method and Concept (03:45 - 04:30 | 0:45)

- **Three Foundations Combined**
  - **Playstyle Personas** from persona-based playtesting [15].
  - **Consensus Process** from multi-agent debate with a managing agent [16].
  - **LLM Difficulty Measurement** from play outcome comparison against human baselines [1].
- **Key Conceptual Distinctions**
  - *Multi-persona decision making:* Unlike Xiao and Yang [1], which uses one agent, several agents with different playstyles decide each guess together.
  - *System-level validation:* Unlike studies that compare multi-agent debate against a single LLM benchmark [13], [17], this study validates the playtester as a complete difficulty measurement system against human players.

**Spoken Script:**

Section 2.4 explains the method and concept behind the framework. It takes playstyle personas from persona-based playtesting [15] while taking the consensus process from multi-agent debate [16]. Both components are then applied to the LLM difficulty measurement of Xiao and Yang [1]. Unlike that work, which uses one agent, our playtester lets several agents with different playstyles decide each guess together. Unlike studies that compare multi-agent systems with a single agent [13], [17], this research validates the playtester as a system rather than claiming that debate beats a single agent.

---

## Slide 6: 3.1 Existing Software, Systems and Methods (04:30 - 05:20 | 0:50)

- **Hand-Crafted Playtesters**
  - *APLib goal structures* (Prasetya et al. [6]): High control, yet requires heavy programming effort and a steep learning curve.
  - *Platformer math model* (Francillette et al. [8]): Needs no complex AI, yet is restricted to platformers with a complex setup.
- **Learning-Based Playtesters**
  - *Supervised DNN* (Gudmundsson et al. [18]): Predicts level difficulty from human moves, yet requires large existing human play logs.
  - *Deep RL* (Delfosse et al. [9]): Learns from self-play, yet needs heavy training resources and lacks human behavioral patterns.
  - *Procedural personas* (Holmgård et al. [15]): Represents playstyles via MCTS, yet still relies on game-specific evolved heuristics.
- **LLM Playtesters and Multi-Agent Debate**
  - *Rule-driven play:* Board-to-text match-3 testing [7], Slay the Spire planning [19], single-LLM Wordle with a handicap [1] and MIMIC personality traits [20].
  - *Multi-agent debate:* Iterative revision [21] and manager-led exchange [16], yet results depend on debate setup [17] and agents may drift from assigned personas [22].

**Spoken Script:**

Section 3 presents our research method, starting with existing systems in Section 3.1. Hand-crafted playtesters, such as goal agents in APLib [6] and mathematical platformer models [8], are controlled but must be rebuilt for each game. Learning-based methods reduce manual coding. Gudmundsson et al. [18] train a neural network on human moves, yet this requires large human play logs. Deep reinforcement learning needs heavy training while lacking human behavior patterns [9], whereas procedural personas still rely on game-specific heuristics [15]. LLM playtesters instead play from rules alone across match-3 games [7], Slay the Spire [19] and Wordle [1], while MIMIC adds personality traits [20]. Multi-agent debate combines agents through revision [21] and a manager [16], although setup [17] and persona drift [22] matter.

---

## Slide 7: 3.2 Software, System and Method Requirement Specification (05:20 - 06:10 | 0:50)

- **3.2.1 Core System Features (Six Requirements)**
  1. Multi-agent collaboration inside a structured debate loop.
  2. Game state extraction from Wordle into readable text.
  3. Distinct agent personas so the debate produces diverse viewpoints.
  4. Game Master adaptive stop and consensus action finalization.
  5. Validation and direct execution of the consensus guess inside the game engine.
  6. Full logging of every model call, debate decision and game outcome.
- **3.2.2 LLM Integration**
  - **Selected Model:** `DeepSeek-V4.1-Flash` (thinking mode disabled, fixed temperature, low cost per game).
  - Must support multi-step reasoning, fit rules + state + turn transcript in context and return valid structured JSON replies with token and latency tracking.
- **3.2.3 Participants for Expert Evaluation (RQ3)**
  - **Pool:** 5 to 7 game designers, QA testers or producers with at least 3 years of industry experience.
  - Must have experience in difficulty balancing or player experience (puzzle, strategy or roguelike games preferred), with informed consent and full anonymity.

**Spoken Script:**

Section 3.2 specifies the requirements across features, LLM integration and participants. Under Section 3.2.1, the system must support multiple agents in a debate loop while converting the Wordle state into readable text. It must also assign distinct personas, let a Game Master finalize the consensus guess, execute that guess in the engine and log every call and outcome. Under Section 3.2.2, we selected DeepSeek-V4.1-Flash because disabling its thinking mode allows a fixed temperature at a low cost. The model handles multi-step reasoning, fits the turn transcript in context and returns valid JSON replies with token logging. Under Section 3.2.3, RQ3 will recruit five to seven game designers, QA testers or producers with at least three years of experience in difficulty balancing.

---

## Slide 8: 3.3.1 - 3.3.2 Playtester Framework and Personas (06:10 - 07:10 | 1:00)

- **3.3.1 Playtester Framework (Figure 1)**
  - Three modules around the dashed Wordle game environment: **Bridge**, **LLM Multi-Agent Debate** and **Game Knowledge** [7].
- **3.3.2 Debate Personas (Table 1)**
  - **Game Master (Managing agent):** Neutral. Proposes a guess, evaluates every advisor's argument and keeps or revises its proposal.
  - **Bold (Advisor):** Plays to win now. Prefers guesses that could still be the answer and accepts the risk of using more guesses later.
  - **Cautious (Advisor):** Plays not to lose. Prefers guesses that rule out the most remaining letters, even if they cannot be the answer.
  - **Casual (Advisor):** Plays like a typical daily player. Prefers common, familiar words with a habitual opener and does not compute letter statistics.
  - Grounded in empirical player types [15], [23] and the explore-exploit trade-off in Wordle [24], [25], [26]; capped at three advisors to prevent context forgetting and high token cost [16], [21].

**Spoken Script:**

Section 3.3 covers the system design, beginning with the playtester framework in Figure 1 and the personas in Table 1. As Figure 1 shows, the framework places three parts around the Wordle environment: the bridge, the multi-agent debate and the game knowledge. In each turn, the bridge converts the public game state into text [7]. The agents then debate the next guess using the game knowledge, after which the bridge executes the final guess. Table 1 lists the four debate personas: one neutral Game Master and three playstyle advisors. In Wordle, players face a trade-off between exploration and exploitation [24]. Cautious explores by testing fresh letters even if the word cannot be the answer, matching optimal play [25]. Bold exploits by guessing words that could win immediately [26], while Casual picks familiar daily words without letter statistics. Three advisors capture these playstyles without the forgetting and higher cost of larger debates [16], [21].

---

## Slide 9: 3.3.3 - 3.3.6 Bridge, Debate Protocol, Knowledge and Turn Logs (07:10 - 08:20 | 1:10)

- **3.3.3 Bridge**
  - *Game state extraction:* Public guess history (green, yellow, gray) + keyboard letter summary (such as `_ _ _ T _`, misplaced S at 1, absent A/E/L). Leaves out the answer word and guess limit.
  - *Consensus action:* Checks that the final guess is an unplayed word in the 14,855-word allowed list [27] before executing it.
- **3.3.4 Debate Protocol (Figure 2)**
  - Reciprocal exchange led by the GM [16]: (1) GM proposes, (2) **Bold → Cautious → Casual** critique in fixed order, (3) GM reviews and keeps or revises.
  - Adaptive break up to **3 rounds** [16]; JSON decision (`action`, `reason`, `stop`) with up to 2 correction retries.
  - *Pilot example (Figure 2):* GM proposes `STORM` (invalid S at pos 1) → Bold & Cautious suggest `STORK`, Casual backs `STORM` → GM adopts `STORK`.
- **3.3.5 Game Knowledge & 3.3.6 Turn Statistics**
  - Static rules, JSON schema and per-agent persona prompt (no shared strategy).
  - Logs initial proposal, final guess, every advisor word and whether each word is still a valid candidate to verify persona behavior [22], [28].

**Spoken Script:**

Sections 3.3.3 through 3.3.6 detail the bridge, the debate protocol, the game knowledge and the turn statistics. The bridge extracts the guess history and a keyboard letter summary with confirmed positions, misplaced letters and absent letters, while leaving out the answer word and guess limit. After the debate, the bridge validates the final guess against the 14,855-word allowed list [27] and executes it. Figure 2 shows the debate protocol on a real pilot turn [16]. First, the Game Master proposes STORM even though S was already ruled out at position 1. Next, Bold and Cautious both point this out and suggest STORK, whereas Casual agrees with STORM because it feels familiar. The Game Master adopts STORK in its review, after which all advisors agree up to the three-round limit. Meanwhile, the game knowledge gives the rules, JSON format and persona prompt, while turn statistics log whether each suggested word could still be the answer [22], [28].

---

## Slide 10: 3.4.1 Study Pipeline (08:20 - 08:50 | 0:30)

- **3.4.1 Study Pipeline (Figure 3)**
  - **Strict Information Boundary:** Puzzle answers go only to the Wordle engine under test; human scores go only to preparation and outside evaluation [1].
  - **Playtester Input and Output:** Receives only the stratified puzzle list (puzzles × repetitions) and outputs run records (guesses used, turn debates, call logs).
  - **Outside Evaluation:** Compares run records with the human baseline to answer RQ1 and RQ2 [1], followed by the planned expert evaluation for RQ3.

**Spoken Script:**

Section 3.4 covers the experiment design, starting with the study pipeline in Figure 3. In Figure 3, the solid box in the center is the playtester system, while the dashed boxes are the study steps and the game around it. From the Wordle archive, puzzle answers go only to the Wordle engine, while human shares go only to data cleaning and outside evaluation. The playtester takes only the puzzle list and outputs run records with guesses used, turn debates and call logs for RQ1 and RQ2 evaluation. Because neither the answer nor the human score enters any prompt, the playtester cannot copy the difficulty it is measured against [1].

---

## Slide 11: 3.4.2 Human Data (08:50 - 09:20 | 0:30)

- **3.4.2 Human Performance Baseline (Figure 4)**
  - **Source:** Engaging Data Wordle archive [29] containing daily solve shares for 1 to 6 guesses; unsolved share is scored as **7** (7-bin objective difficulty distribution [14]).
  - **Data Cleaning:** Removed 4 puzzles with missing sample sizes or implausible solve shares, leaving **1,861 of 1,865 puzzles**.
  - **Frozen Difficulty Quartiles (Figure 4):** Sorted by human mean into four equal groups **D1 (easiest) to D4 (hardest)** with cut-points frozen before any pilot run at **3.98, 4.24 and 4.53 guesses**, where the two middle quartiles span only **0.55 guesses**.

**Spoken Script:**

Section 3.4.2 describes the human data in Figure 4. The baseline comes from the Engaging Data Wordle archive [29], which gives the share of players solving each puzzle in 1 to 6 guesses, with unsolved games scored as 7. Each puzzle therefore has a 7-bin distribution measuring objective difficulty [14]. Removing four records with missing sample sizes or implausible solve shares leaves 1,861 of 1,865 puzzles. These puzzles are sorted by human mean and split into four equal quartiles D1 to D4 at frozen cut-points of 3.98, 4.24 and 4.53 guesses. Figure 4 shows these quartiles, where the two middle quartiles span only 0.55 guesses.

---

## Slide 12: 3.4.3 - 3.4.4 Pilot Design and Measures (09:20 - 10:05 | 0:45)

- **3.4.3 Pilot Design (Table 2) and Configuration**
  - **Exp A (deep, for RQ1 & second check of RQ2):** 12 puzzles (3 per quartile) × **32 runs** (stratified seed `20261013`), sized by Thompson's multinomial rule (±20 pp across all 7 bins at 95% confidence) [30].
  - **Exp B (wide, primary for RQ2):** 48 puzzles (12 per quartile, disjoint, seed `20261014`) × **3 runs**, sized by Julious's rule of 12 per group for pilot studies [31].
  - **Frozen Configuration:** `DeepSeek-V4.1-Flash` (thinking off, temp `0.2`, 1,024-token limit) with a hidden **12-guess handicap** [1]; failed games retried once.
- **3.4.4 Dual Scoring and Evaluation Measures**
  - **12-guess score:** Actual guesses used (loss = 13), keeping hard puzzles apart [1].
  - **6-guess score:** Same game cut at 6 guesses (loss = 7), matching the human scale because agents never see the limit.
  - **RQ1 Measures:** Within-puzzle SD, single-game **ICC(1,1)** and k-run mean **ICC(1,k)**.
  - **RQ2 Measures:** **Pearson r**, **Spearman ρ** (with p-values), **Bias**, **MAE** (on 6-guess scale vs. constant baseline) and rank-based **D1-D4 confusion matrix**.

**Spoken Script:**

Sections 3.4.3 and 3.4.4 cover the pilot design in Table 2 and our evaluation measures. Experiment A is the deep experiment for RQ1, playing 12 puzzles 32 times each. Under Thompson's rule, 32 runs keep all seven bin shares within 20 percentage points at 95 percent confidence [30]. Experiment B is the wide experiment for RQ2, playing 48 disjoint puzzles three times each under Julious's rule of 12 per quartile [31]. Every agent runs on DeepSeek-V4.1-Flash at temperature 0.2 with a hidden 12-guess handicap so hard puzzles do not all tie at 7 [1]. Each game is read on both the 12-guess score and the 6-guess score capped at 7. RQ1 uses within-puzzle standard deviation, ICC(1,1) and ICC(1,k), while RQ2 uses Pearson r, Spearman rho, bias, MAE and a rank-based quartile confusion matrix.

---

## Slide 13: 4.1 Experiment Result: Completion and Cost (10:05 - 10:50 | 0:45)

- **Run Completion Across Both Experiments**
  - **Total:** **525 completed games** out of 543 attempts (96.7% completion rate).
  - **Exp A (deep):** 383 completed of 395 attempts; **11 of 12 puzzles** reached all 32 planned runs after one retry.
  - **Exp B (wide):** 142 completed of 148 attempts; **46 of 48 puzzles** reached all 3 planned runs after one retry.
  - **18 Failed Attempts:** 13 ended after an agent still gave an invalid reply following two correction requests; 4 were cut off when a run was stopped; 1 ended on a model service timeout.
- **Runtime, Token Cost and Debate Length**
  - **Exp A average per game:** **71 seconds**, **75,800 prompt tokens** and **3,900 completion tokens**.
  - **Exp B average per game:** **67 seconds**, **84,800 prompt tokens** and **4,300 completion tokens**.
  - **Adaptive Debate Stop:** The GM ended the debate early in **57 of 2,198 turns** (Exp A) and **19 of 887 turns** (Exp B); all other turns ran to the 3-round limit. Every call returned the same model version identifier.

**Spoken Script:**

Section 4 presents the experiment results, starting with completion and cost in Section 4.1. The pilot made 543 attempts, of which 525 ended as completed games: 383 in Experiment A and 142 in Experiment B. Thirteen of the 18 failed attempts ended on invalid replies after two repair requests, four were cut off when a run was stopped and one ended on a timeout. After one retry, 11 of 12 deep puzzles and 46 of 48 wide puzzles reached all planned runs. A game averaged 71 seconds with 75,800 prompt tokens in Experiment A, while taking 67 seconds with 84,800 prompt tokens in Experiment B. The Game Master stopped the debate early in 57 of 2,198 turns in Experiment A and 19 of 887 turns in Experiment B.

---

## Slide 14: 4.2 RQ1 Results: Outcome Consistency (10:50 - 11:45 | 0:55)

- **Table 3: Overall RQ1 Measures on 12-Guess and 6-Guess Scores**

| Measure | Exp A (12×32), 12-guess | Exp A (12×32), 6-guess | Exp B (48×3), 12-guess | Exp B (48×3), 6-guess |
|---|---|---|---|---|
| Within-puzzle SD (guesses) | 1.53 | 0.96 | 1.52 | 0.85 |
| ICC(1,1), one game | 0.49 | 0.55 | 0.48 | 0.44 |
| ICC(1,k), mean of all runs | 0.97 | 0.98 | 0.73 | 0.70 |

- **Table 4: Mean Within-Puzzle SD (guesses) by Human Quartile**

| Human quartile | Exp A, 12-guess | Exp A, 6-guess | Exp B, 12-guess | Exp B, 6-guess |
|---|---|---|---|---|
| D1 | 0.94 | 0.74 | 1.06 | 0.89 |
| D2 | 1.37 | 1.10 | 1.75 | 0.78 |
| D3 | 1.48 | 0.95 | 1.35 | 0.79 |
| D4 | 2.30 | 1.04 | 1.93 | 0.95 |

- **Key Observations from Exp A and Exp B**
  - Single-game consistency is moderate: **ICC(1,1) = 0.49** (12-guess) and **0.55** (6-guess) in Exp A.
  - Multi-run average consistency is high: **ICC(1,k) reaches 0.97** (12-guess) and **0.98** (6-guess) over 32 runs in Exp A, and **0.73** over 3 runs in Exp B.
  - Spread grows with difficulty on 12-guess score: mean SD rises from **0.94 guesses (D1)** to **2.30 (D4)** in Exp A, while staying between **0.74 and 1.10** on the 6-guess score.

**Spoken Script:**

Section 4.2 reports the RQ1 consistency results in Tables 3 and 4 across both experiments and both scoring scales. In Experiment A across 12 puzzles with 32 runs each, the within-puzzle standard deviation is 1.53 guesses on the 12-guess score and 0.96 on the 6-guess score. A single game gives an intraclass correlation ICC(1,1) of 0.49 on the 12-guess score and 0.55 on the 6-guess score. However, the mean of 32 games reaches an ICC(1,k) of 0.97 on the 12-guess score and 0.98 on the 6-guess score. In Experiment B across 48 puzzles with three runs each, ICC(1,1) is 0.48 while the three-run mean reaches an ICC(1,k) of 0.73. Table 4 breaks this spread down by quartile. On the 12-guess score, the mean standard deviation rose from 0.94 guesses for D1 puzzles to 2.30 for D4 puzzles. On the 6-guess score, it stayed between 0.74 and 1.10 guesses.

---

## Slide 15: 4.3 RQ2 Results: Agreement with Human Difficulty (11:45 - 12:45 | 1:00)

- **Table 5: RQ2 Results of Exp B (48×3) and Exp A (12×32)**

| Measure | Exp B, 12-guess | Exp B, 6-guess | Exp A, 12-guess | Exp A, 6-guess |
|---|---|---|---|---|
| Playtester avg. guesses | 6.34 | 5.54 | 5.76 | 5.29 |
| Human avg. guesses | 4.26 | 4.26 | 4.25 | 4.25 |
| Pearson r | 0.30 (p = 0.039) | 0.38 (p = 0.007) | 0.70 (p = 0.011) | 0.60 (p = 0.041) |
| Spearman ρ | 0.34 (p = 0.017) | 0.36 (p = 0.012) | 0.72 (p = 0.008) | 0.62 (p = 0.031) |
| Bias (guesses) | - | +1.28 | - | +1.04 |
| MAE (guesses) | - | 1.38 | - | 1.26 |

- **Level Bias vs. Rank Category Agreement (Figure 5)**
  - On the 6-guess score in Exp B, the playtester averages **5.54 guesses vs. 4.26 for humans** (**+1.28 bias**, **1.38 MAE**); in Exp A, 6-guess fail share is ~27 percentage points above humans.
  - **Rank-Based Quartiles (Figure 5, Exp B):** **16 of 48 puzzles** fall on the exact diagonal, while **31 of 48** lie within one quartile. Five human D2 puzzles were placed in D4, yet **no human D4 puzzle was placed in D1** (Exp A: 4/12 exact, 10/12 within one quartile).

**Spoken Script:**

Section 4.3 reports the RQ2 human agreement results in Table 5 and Figure 5. In Experiment B across 48 puzzles, the playtester's averages correlate with the human averages at Spearman rho equal to 0.34 with a p-value of 0.017. In Experiment A across 12 puzzles with 32 runs each, Spearman rho reaches 0.72 with a p-value of 0.008. On the 6-guess score, the playtester averaged 5.54 guesses on the Experiment B puzzles compared with 4.26 for humans. That is a bias of about 1.3 guesses with an MAE of 1.38 guesses. In Experiment A, the playtester also failed within six guesses about 27 percentage points more often than humans did. Figure 5 compares the rank-based difficulty quartiles for the 48 wide puzzles. Sixteen of the 48 puzzles fell on the diagonal while 31 lay within one quartile, with no human D4 puzzle placed in D1.

---

## Slide 16: 5.1 - 5.2 Analysis of RQ1 (Consistency) and RQ2 (Human Agreement) (12:45 - 13:55 | 1:10)

- **5.1 RQ1 Analysis: Single-Game Noise vs. Multi-Run Reliability**
  - A single run is only moderately consistent (**ICC(1,1) = 0.49**): roughly half of the score variance lies between puzzles while half comes from run-to-run noise (~1.5 guesses spread).
  - Averaging across repeated runs produces a highly reliable difficulty score (**ICC(1,k) = 0.97** at 32 runs; **0.73** even at 3 runs), showing why each puzzle must be played multiple times.
  - Larger spread on D4 puzzles comes from long games and occasional losses, which is necessary variance to separate hard puzzles from easy ones.
- **5.2 RQ2 Analysis: Relative vs. Absolute Difficulty**
  - Both experiments show statistically significant positive rank correlation ($p < 0.05$).
  - Alignment is stronger in Exp A (**ρ = 0.72**) than Exp B (**ρ = 0.34**) because 32 runs reduce noise in each puzzle's mean; this matches the best 20-run correlation (**r = 0.62**) of Xiao and Yang [1].
  - The **1.38 MAE** is more than twice the **0.55-guess width** of the middle two quartiles (3.98 to 4.53), while an MAE close to the bias (+1.28) shows that most error is a constant shift.
  - **Core Finding:** Rank-based quartiles place two thirds of Exp B puzzles within one quartile, showing the playtester measures **relative difficulty** much better than **absolute difficulty**.

**Spoken Script:**

Section 5 analyzes the experiment results, starting with RQ1 and RQ2 in Sections 5.1 and 5.2. For RQ1, a single run is only moderately consistent, as its ICC(1,1) of 0.49 means that about half of the score variance comes from run-to-run noise of about 1.5 guesses. However, the mean over many runs is highly reliable, reaching an ICC(1,k) of 0.97 at 32 runs and 0.73 at three runs. That is why a puzzle must be played several times before using its mean. Part of this spread comes from hard puzzles that produce long games and losses, which is needed to separate puzzles. For RQ2, the playtester ranks puzzles in the same direction as humans in both experiments. The ranking is stronger in Experiment A at 0.72 than in Experiment B at 0.34, which is close to the 0.62 correlation of Xiao and Yang [1]. However, the 1.38 MAE is more than twice the 0.55-guess width of the middle two quartiles, while an MAE close to the bias shows a constant shift. Thus, the playtester measures relative difficulty better than absolute difficulty.

---

## Slide 17: 5.3 - 5.4 Planned Expert Evaluation (RQ3) and Final Study Implications (13:55 - 15:00 | 1:05)

- **5.3 RQ3: Expert Evaluation (Planned Next Stage)**
  - Follows the completed quantitative analysis in the research schedule.
  - **Mixed-Method Design:**
    1. *Likert-scale survey (1 to 5):* Industry experts rate utility statements after inspecting the final RQ1 and RQ2 results; overall average score is reported.
    2. *Semi-structured interviews:* Analyzed thematically, with each recurring theme reported as a share of the expert pool.
- **5.4 Four Design Implications Fixed for the Final Study**
  1. **Run sizing per puzzle:** Set repetition count $k$ so the puzzle mean reaches a reliability target (such as **ICC(1,k) ≥ 0.9**).
  2. **Fixed RQ1 consistency margin (H1):** Set before the final run from pilot spread (such as within-puzzle **SD ≤ 0.5** on the 6-guess score).
  3. **Primary RQ2 measures (H2):** Judge human agreement primarily through **rank correlation** and **rank-based quartiles**.
  4. **Descriptive distribution case study:** Present the **3 easiest and 3 hardest puzzles** by human mean, using fresh puzzles never played in the pilot.

**Spoken Script:**

Finally, Sections 5.3 and 5.4 cover the planned expert evaluation for RQ3 and the implications for the final study. The expert evaluation follows the quantitative analysis and combines a Likert-scale survey with semi-structured interviews. Five to seven experts will inspect the final RQ1 and RQ2 results and rate utility statements from 1 to 5, after which the mean rating and interview themes are reported. Before any final run begins, the pilot results fix four design choices for the final study on fresh unseen puzzles. First, the runs per puzzle will be set to reach a reliability target such as an ICC(1,k) of at least 0.9. Second, the H1 consistency margin, such as a within-puzzle standard deviation of at most 0.5 on the 6-guess score, will be fixed from the pilot spread. Third, the primary RQ2 measures will be the rank correlation and rank-based quartiles. Fourth, the three easiest and three hardest puzzles will be shown as a distribution case study. Thank you for your attention.

---

## References

[1] C. Xiao and Z. Yang, "LLMs may not be human-level players, but they can be testers: Measuring game difficulty with LLM agents," *Proc. ACM Hum.-Comput. Interact.*, vol. 9, no. 6, pp. 1097-1123, Oct. 2025, doi: 10.1145/3748634.  
[2] M. Weber and P. Notargiacomo, "Dynamic difficulty adjustment in digital games using genetic algorithms," in *Proc. 19th Brazilian Symp. Computer Games and Digital Entertainment (SBGames)*, Recife, Brazil, Nov. 2020, pp. 62-70, doi: 10.1109/SBGames51465.2020.00019.  
[3] L. Karavidas, H. Apostolidis, and T. Tsiatsos, "Usability evaluation of an adaptive serious game prototype based on affective feedback," *Information*, vol. 13, no. 9, p. 425, Sep. 2022, doi: 10.3390/info13090425.  
[4] E. A. Romero-Mendez, P. C. Santana-Mancilla, M. Garcia-Ruiz, O. A. Montesinos-López, and L. E. Anido-Rifón, "The use of deep learning to improve player engagement in a video game through a dynamic difficulty adjustment based on skills classification," *Applied Sciences*, vol. 13, no. 14, p. 8249, Jul. 2023, doi: 10.3390/app13148249.  
[5] D. A. Alvarado Villa, O. A. Montesinos López, and P. C. Santana-Mancilla, "Training of an intelligent agent to improve the gaming experience for video gamers," *Avances en IHC*, vol. 6, no. 1, pp. 123-125, Nov. 2021, doi: 10.47756/aihc.y6i1.105.  
[6] I. S. W. B. Prasetya *et al.*, "Programming smart playtesting," *ACM Trans. Softw. Eng. Methodol.*, vol. 35, no. 3, pp. 1-47, Mar. 2026, doi: 10.1145/3742473.  
[7] Y. Zhao and C. Tang, "Towards LLM-based automatic playtest," in *Proc. 33rd ACM Int. Conf. Foundations of Software Engineering (FSE Companion)*, Trondheim, Norway, Jun. 2025, pp. 1645-1651, doi: 10.1145/3696630.3728700.  
[8] Y. Francillette, H. Tremblay, B. Bouchard, and B.-A. Menelas, "A comprehensive model of automated evaluation of difficulty in platformer games," *ACM Games: Research and Practice*, vol. 3, no. 1, Jan. 2025, doi: 10.1145/3705013.  
[9] Q. Delfosse *et al.*, "Deep reinforcement learning agents are not even close to human intelligence," 2025, *arXiv preprint*.  
[10] X. Feng *et al.*, "ChessGPT: Bridging policy learning and language modeling," in *Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track*, 2023.  
[11] S. Hu, T. Huang, and L. Liu, "PokeLLMon: A human-parity agent for Pokémon battles with large language models," 2024, *arXiv:2402.01118*.  
[12] G. Wang *et al.*, "Voyager: An open-ended embodied agent with large language models," 2023, *arXiv:2305.16291*, doi: 10.48550/arXiv.2305.16291.  
[13] K. Sreedhar and L. Chilton, "Simulating strategic reasoning: Comparing the ability of single LLMs and multi-agent systems to replicate human behavior," in *Proc. 58th Hawaii Int. Conf. System Sciences (HICSS)*, 2025, doi: 10.24251/HICSS.2025.100.  
[14] T. Constant, G. Levieux, A. Buendia, and S. Natkin, "From objective to subjective difficulty evaluation in video games," in *Human-Computer Interaction - INTERACT 2017*, Lecture Notes in Computer Science, vol. 10514. Cham, Switzerland: Springer, 2017, pp. 107-127, doi: 10.1007/978-3-319-67684-5_8.  
[15] C. Holmgård, M. C. Green, A. Liapis, and J. Togelius, "Automated playtesting with procedural personas through MCTS with evolved heuristics," *IEEE Trans. Games*, vol. 11, no. 4, pp. 352-362, Dec. 2019.  
[16] T. Liang *et al.*, "Encouraging divergent thinking in large language models through multi-agent debate," in *Proc. 2024 Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Miami, FL, USA, 2024, pp. 17889-17904, doi: 10.18653/v1/2024.emnlp-main.992.  
[17] A. P. Smit, N. Grinsztajn, P. Duckworth, T. D. Barrett, and A. Pretorius, "Should we be going MAD? A look at multi-agent debate strategies for LLMs," in *Proc. 41st Int. Conf. Machine Learning (ICML)*, PMLR, vol. 235, 2024.  
[18] S. F. Gudmundsson *et al.*, "Human-like playtesting with deep learning," in *Proc. 2018 IEEE Conf. Computational Intelligence and Games (CIG)*, Maastricht, Netherlands, 2018, pp. 1-8.  
[19] B. Bateni and J. Whitehead, "Language-driven play: Large language models as game-playing agents in Slay the Spire," in *Proc. 19th Int. Conf. Foundations of Digital Games*, Worcester, MA, USA, May 2024, pp. 1-10, doi: 10.1145/3649921.3650013.  
[20] Y. Chen, S. Habchi, and L. Wei, "MIMIC: Integrating diverse personality traits for better game testing using large language model," in *Proc. 40th IEEE/ACM Int. Conf. Automated Software Engineering (ASE)*, 2025, *arXiv:2510.01635*.  
[21] Y. Du, S. Li, A. Torralba, J. B. Tenenbaum, and I. Mordatch, "Improving factuality and reasoning in language models through multiagent debate," in *Proc. 41st Int. Conf. Machine Learning (ICML)*, PMLR, vol. 235, 2024.  
[22] R. Baltaji, B. Hemmatian, and L. R. Varshney, "Persona inconstancy in multi-agent LLM collaboration: Conformity, confabulation, and impersonation," in *Proc. 2nd Workshop on Cross-Cultural Considerations in NLP (C3NLP)*, 2024, *arXiv:2405.03862*.  
[23] A. Drachen, A. Canossa, and G. N. Yannakakis, "Player modeling using self-organization in Tomb Raider: Underworld," in *Proc. IEEE Symp. Computational Intelligence and Games (CIG)*, Milan, Italy, 2009, pp. 1-8, doi: 10.1109/CIG.2009.5286500.  
[24] R. C. Wilson, A. Geana, J. M. White, E. A. Ludvig, and J. D. Cohen, "Humans use directed and random exploration to solve the explore-exploit dilemma," *J. Exp. Psychol.: General*, vol. 143, no. 6, pp. 2074-2081, 2014, doi: 10.1037/a0038199.  
[25] D. Bertsimas and A. Paskov, "An exact solution to Wordle," *Operations Research*, vol. 73, no. 3, pp. 1384-1394, 2025, doi: 10.1287/opre.2022.0434.  
[26] J. Liang, A. Kabbara, J. Liu, R. Luo, K. Kim, and M. Guerzhoy, "Semantic, orthographic, and phonological biases in humans' Wordle gameplay," in *Findings of the Association for Computational Linguistics: IJCNLP-AACL 2025*, 2025, *arXiv:2411.18634*.  
[27] T. Atkins Jr., "wordle-list," GitHub repository, Sep. 2022. [Online]. Available: https://github.com/tabatkins/wordle-list  
[28] J. Licato, S. Steinle, and B. Hollis, "Do persona-infused LLMs affect performance in a strategic reasoning game?" in *Proc. IJCNLP-AACL 2025*, 2025, *arXiv:2512.06867*.  
[29] Engaging Data, "Wordle guess distribution." [Online]. Available: https://engaging-data.com/wordle-guess-distribution/  
[30] S. K. Thompson, "Sample size for estimating multinomial proportions," *The American Statistician*, vol. 41, no. 1, pp. 42-46, 1987.  
[31] S. A. Julious, "Sample size of 12 per group rule of thumb for a pilot study," *Pharmaceutical Statistics*, vol. 4, no. 4, pp. 287-291, 2005, doi: 10.1002/pst.185.
