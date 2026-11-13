# CHAPTER 3 RESEARCH METHODOLOGY

This chapter presents the playtester and the study that validates it. It describes the bridge, the multi-agent debate and the game knowledge, after which it derives the human baseline from the public Wordle results. It sets out the three conditions, the puzzles and the run, before defining the measures that answer each research question. Every part of the design was fixed before the first game, so the results come from one configuration.

## 3.1 Playtester Design

The playtester has three parts around the game environment, which are the bridge, the multi-agent debate and the game knowledge (Figure 3.1). In each turn, the bridge converts the public game state into text, since a language model cannot see the game board [1]. The agents then debate the next guess from this state, after which the Game Master (GM) decides what to play. The bridge plays this guess in the game, while the feedback of the game becomes the state of the next turn.

![The persona-based multi-agent debate playtester for Wordle. The game under test is external to the playtester and drawn with a dashed edge, while the bridge passes the state and the guess between them.](final-conference/figures/fig-architecture-tikz.png){width=100%}

The example in Figure 3.1 shows one turn. The engine marks the S of SLATE as misplaced and its T as in place, while L, A and E are absent from the answer. The bridge turns this feedback into a text state, which the agents read before they propose the next guess. The GM then decides, after which the bridge validates the decision and the engine plays it.

### 3.1.1 Personas

The debate involves one GM with three advisors, each of which holds a playstyle persona (Table 3.1). Each advisor argues from the same public state, so the playstyle is the only difference between them. The GM weighs the three arguments and returns the guess, while each advisor returns one suggestion with a reason. The GM proposes the guess at the start of a turn and closes it with a decision, so the advisors never act on the engine directly.

| Persona | Role | Playstyle |
|--------------|----------------|--------------------------------------------------|
| Game Master | Managing agent | Neutral. Proposes a guess, evaluates every advisor's argument and keeps or revises its proposal. |
| Bold | Advisor | Plays to win now. Prefers guesses that could still be the answer, even at the risk of using more guesses later. |
| Cautious | Advisor | Plays not to lose. Prefers guesses that rule out the most remaining letters, even if they cannot be the answer. |
| Casual | Advisor | Plays like a typical daily player. Prefers common, familiar words and does not compute letter statistics. |

Table: The personas of the debate.

Players do not share a single playstyle, as gameplay data reveals distinct player types [2]. Wordle is a deterministic single-player game with imperfect information, so the only decision that a player makes is how to spend each guess. A player may exploit with a word that could still be the answer, or explore with a word that mainly rules out letters. This trade-off is a classic problem in human decision making, where people seek more information when more choices remain [3]. Optimal Wordle play leans toward exploration [4], while real players tend to stay close to the words that they have already tried [5]. Thus, the Bold advisor argues for guesses that could win immediately, while the Cautious advisor argues for guesses that narrow the remaining words. The Casual advisor adds the typical daily player, who picks familiar words without computing letter statistics.

The GM holds no playstyle, since its role is to weigh the three arguments and to keep or revise the proposal. One advisor per playstyle is used rather than more advisors, because debates with three agents already show clear gains [6]. Longer debates also make agents lose track of the views of the others [7]. The GM therefore reads one argument per playstyle at every turn, which keeps the review short.

Each persona is implemented as a text instruction that the agent receives in its system message. The instructions and the per-turn tasks of all six agents are reproduced in Appendix A. The same instruction is re-sent on every turn, so the playstyle does not drift during a game. The instruction fixes the playstyle, while the per-turn task asks for a decision with a reason and a stop flag.

### 3.1.2 Bridge and Game Knowledge

The bridge reads the history of the guesses with their feedback. Each letter then shows as green in its correct position, yellow when it belongs elsewhere and gray when the answer lacks it. The bridge renders this history as text with a keyboard-style letter summary, which plays the role of the colored keyboard that a human player sees. The summary lists the confirmed, misplaced and absent letters without any list of candidate words. The answer word, the guess limit and the human results never enter any prompt, so the playtester cannot copy the difficulty that it is measured against.

In the other direction, the bridge accepts a final guess only if it is an unplayed word from the 14,855-word allowed-guess list of Wordle [8]. Every agent also receives the same game knowledge, which holds the game rules, the reply format and its own persona instruction. A reply is a structured decision with an action, a reason and a stop flag, so the debate can read and compare the answers of every agent. A word outside the allowed list is rejected and the turn is sent back for correction before anything is played.

### 3.1.3 Debate Protocol

The debate follows the structure of Liang et al. [7], in which a managing agent oversees an exchange between the other agents. The GM first proposes a guess, after which each advisor reads the proposal and the transcript of every earlier round. Under the parallel protocol, an advisor does not see the advice that the other advisors give in the same round, so the three advisors of a round answer independently. Each advisor then agrees with the proposal or suggests another word with a short reason. The GM reviews every suggestion and keeps or revises its guess, which ends the round. A new round starts again from the first advisor, while the GM may stop early once another round is unlikely to change its decision.

The parallel rule follows debates in which agents read the others only from the previous round [6]. It also keeps the speaking order out of the debate, since an advisor can no longer copy the alternative that an earlier advisor named. The pilot used a sequential protocol, in which each advisor also read the suggestions of the earlier advisors in the same round. Under that protocol, later advisors often named the same alternative as an earlier one, which tied each persona to its position in the order. The final study uses the parallel rule instead, although the advisors are still called in the same fixed order.

Three rounds is the upper limit, since each extra round adds four model calls to every turn. An invalid reply is sent back for correction up to two times before the turn continues. A turn that uses all three rounds therefore costs thirteen model calls. Both limits keep a failing turn bounded in time and in cost, which matters when 3,000 games must finish.

Suppose that the GM proposes STORM even though its S is already absent from the answer. Bold and Cautious can both point this out and suggest STORK, while Casual may keep STORM because it feels like an ordinary word. The GM weighs the three replies and decides, after which the bridge validates STORK and the engine plays it. This example also shows why the parallel rule matters, since the agreement of Bold and Cautious is independent rather than copied.

Every call behind such an exchange is a single zero-shot request built from two messages. The system message holds the agent's instruction, one of those reproduced in Appendix A, followed by the JSON schema of the reply and a short rule on its format. The user message holds one JSON object with the public game context and the task of the current turn. No worked example, no few-shot demonstration and no chain-of-thought exemplar is included. The agents also keep no memory between calls, so earlier turns reach them only through the transcript field of the context.


The context carries four fields. The game context repeats the rules, the public observation and the keyboard summary of the letters. The proposal holds the word that the GM last proposed. The transcript holds one line for every exchange already completed, while completed_rounds counts the rounds of the current turn. The suggestions field holds the advice given in the same round, which the parallel protocol leaves empty for the advisors. A reply that fails validation is sent back with a repair object. The object quotes the validation error and the rejected decision. It asks for a corrected reply within the same turn, so a repair never starts a new round.

Figure 3.2 shows one complete game from its first guess to its last, on puzzle 1008. The game runs for three turns and ends with the answer, which shows how the debate, the bridge and the engine interact.

![One game of the persona debate on puzzle 1008. Each row is a turn, with the guess, the feedback that the bridge renders as text and the debate behind it. The GM keeps its own proposal in all three turns.](final-conference/figures/fig-example-tikz.png){width=100%}

The GM opens with SLATE, which the bridge reports as S and E misplaced with L, A and T absent. Bold and Casual prefer CRANE, while Cautious keeps the proposal. The GM keeps its own word. Cautious keeps the proposal on this turn, which is the behaviour that its instruction asks for at an early board.

The second turn plays RESIN, which places R, S and N and leaves E and I misplaced. Bold and Casual back RESIN again, while Cautious prefers CRONY to rule out letters. The GM retains RESIN. Cautious dissents again, which shows that the playstyles stay distinct from turn to turn.

The third turn proposes RISEN, which all three advisors endorse. The GM then stops after one round. The game is solved in three guesses, against a human average of 3.79 for this puzzle. The GM keeps its own proposal in all three turns, which is the pattern that the results report.

## 3.2 Human Baseline

The human baseline comes from the public Engaging Data guess distribution for past Wordle puzzles. It gives the share of players who solved each past puzzle in one to six guesses. The remaining share is treated as a loss scored 7, which turns the distribution of a puzzle into seven bins with a human mean. Four puzzles are removed for data errors, such as a missing sample size, which leaves 1,861 of the 1,865 archived puzzles.

These puzzles are sorted by their human mean and cut into three equal groups, from T1 (easiest) to T3 (hardest). The cut-points of 4.07 and 4.42 guesses fall where that split lands rather than at values chosen in advance. They were frozen before any final game. Four categories would need three cut-points instead of two, so more puzzles would sit close to one. A small error in a human mean can then move such a puzzle to another label. Terciles also match the categories that the second research question scores, so the sample and the measure share one scheme. The quartile cut-points of 3.98, 4.24 and 4.53 stay available as a sensitivity check.

## 3.3 Study Design

The study follows the pipeline in Figure 3.3. It is a quantitative system validation, since every measure comes from the records of complete games rather than from ratings or questionnaires. The archive and its human data are cleaned into a puzzle list with a human mean per puzzle, after which the runner plays that list under the three conditions. The records of those games are then analyzed against the human mean of each puzzle.

![The pipeline of the study. The three conditions play the same puzzle list, while every record is analyzed against the human mean of its puzzle. The dashed route carries the human means from the cleaning step to the analysis.](final-conference/figures/fig-pipeline-tikz.png){width=100%}

### 3.3.1 Conditions

The study compares three conditions, which differ only in the agents that decide each guess (Table 3.2). The puzzles, the run settings and the measures are the same for all three, so any difference between them comes from the decision. Table 3.2 sets out the agents, the per-turn work and the setting that each condition isolates. C1 is the full playtester, C2 removes the debate and C3 removes the personas.

| | C1 Persona debate | C2 Single agent | C3 Debate without personas |
|---|---|---|---|
| Agents | GM and three playstyle advisors | One player agent | GM and three neutral advisors |
| Per turn | proposal, three advisors, review, up to three rounds | one decision | as in C1 |
| Personas | Bold, Cautious and Casual | none | none |
| Isolates | the full playtester | the reference point | the effect of the personas |

Table: The three conditions of the study.

C1 is the playtester with the GM and the three playstyle advisors, whose persona text and game knowledge come unchanged from the pilot. C2 plays the game with one agent, as the single-agent playtesters of Xiao and Yang do [9]. Its agent receives the same game knowledge, bridge output and reply format, while its request holds only the game state and its task. Each turn it returns one decision, which the bridge validates and the engine plays. C2 does not rate difficulty, since a rating could not be compared with guess counts.

C3 keeps the GM and the three advisor slots of C1, while the three advisors share one instruction with no playstyle. The advisors keep separate keys, so the debate and the statistics can still tell them apart. This condition asks whether the playstyle text changes anything beyond having three advisors. If the personas matter, C1 should differ from C3 on behaviour and on the outcomes.

The contrasts are fixed in advance. The difference between C3 and C2 isolates the debate, since both conditions use the same model and prompts without playstyles. The difference between C1 and C3 isolates the personas, since both conditions hold the same debate. The overall difference between C1 and C2 is reported as context rather than as a separate test. The pilot measured the persona debate on its own, so it could not say what the debate or the personas add [10].

### 3.3.2 Puzzles and Sample Size

The three conditions play the same 100 puzzles with the same ten runs each, which gives 3,000 games. Every comparison is paired by puzzle, since each condition faces exactly the same words. Each puzzle therefore supplies ten runs to each condition, which is what the consistency measures need. A game is one run of one puzzle, so a comparison across conditions always pairs runs of the same word.

The draw removes duplicate answers and every puzzle that the pilots used, which leaves a pool of 1,729 puzzles out of the 1,861. From that pool the draw takes puzzles at random within each tercile, with 33 from T1, 33 from T2 and 34 from T3. The hardest tercile receives the hundredth puzzle because its range of human means is the widest. The final set still holds 25, 22, 28 and 25 puzzles in the four quartiles of the earlier split, so the sensitivity check has cases in every quartile.

The sample size comes from a simulation that was calibrated on the pilot. The simulation draws puzzles from the real human means and generates whole-number guess counts with the noise and the bias that the pilot measured. At 100 puzzles and ten runs, it puts the power of a Spearman test against zero at 92 to 95 percent for a true correlation of 0.4. That power reaches 99 percent at 0.5 and 100 percent at 0.6, while a test between two correlations would need several hundred puzzles. Ten runs leave a puzzle mean reliable enough, since the Spearman–Brown relation puts its reliability at 0.77 to 0.89. The hundred puzzles also exceed the thirty subjects that an ICC study needs [11].

The bin shares of a single puzzle are still too imprecise to read with ten runs, so the distribution comparison is pooled by category rather than by puzzle. Pooling gives each tercile 330 games, which is enough to compare its seven bins against the human ones. A comparison at the puzzle level would need many more runs to say anything about a single bin. The pooled comparison therefore asks whether the whole distribution of a tercile matches the human one.

### 3.3.3 Configuration and Run

Every condition runs on DeepSeek-V4.1-Flash, which the API serves under the model name deepseek-flash. The model runs with thinking enabled at low reasoning effort, a reply limit of 8,192 tokens, JSON mode and no temperature. Each game ends within six guesses, while a loss is scored 7 to match the human data. The agents never see this limit, since a limit that they could count would change how they play.

A debate turn allows up to three rounds and two repair re-asks, while a single-agent turn allows one decision and two repairs. The request timeout is 300 seconds, while a failed game is retried once. The settings, the prompts and the six-guess limit were frozen before the first final game, so every game of the study uses one configuration. The single agent therefore spends at most three calls on a turn, against thirteen for a full debate turn.

The three conditions ran from 2 to 4 November 2026 under one code revision with a clean working tree. All 3,000 games completed, although 55 of them needed a second attempt after a provider error. Every answered call returned the same model snapshot, so no game mixes two versions of the model. The three conditions cost 48.51 US dollars in total.

## 3.4 Measures

Two research questions and one descriptive analysis need a small set of measures (Table 3.3). RQ1 asks how consistent the outcomes are across repeated runs, while RQ2 asks how far the difficulty estimates agree with human difficulty. Correlations are reported with their p-values and read as very weak below 0.2, weak up to 0.4, moderate up to 0.6 and strong above 0.6 [9]. The bias and the mean absolute error (MAE) use the six-guess score, since they compare the playtester with the human data directly.

| RQ | Measure | Definition |
|---------|---------------------|--------------------------------------------------|
| RQ1 | Within-puzzle SD | Spread of the guess counts over the ten runs of a puzzle, averaged over the puzzles. |
| RQ1 | ICC(1,1), ICC(1,10) | Share of the score variation that comes from the puzzle rather than from run-to-run noise, for one game and for the mean of ten runs. |
| RQ2 | Spearman ρ, Pearson r | Agreement between the playtester's puzzle means and the human means, on ranks and on values. |
| RQ2 | Bias, MAE | Mean signed difference and mean distance from the human mean, compared with a constant guess at the human average. |
| RQ2 | Tercile agreement | Playtester means split into T1 to T3 at the human cut-points, then compared with the human terciles as exact matches, adjacent matches and a weighted κ. |
| Persona | GM retention | Share of turns in which the played word is the first proposal of the GM. |
| Persona | Adoption, agreement | Share of turns in which the GM switched to an advisor's word, and in which an advisor kept the GM proposal in every round. |
| Persona | Non-candidate share | Share of an advisor's suggestions after the first turn that can no longer be the answer given the public feedback. |
| Persona | Same-word share | Share of an advisor's dissents that name the same word as another advisor's dissent in the same round. |

Table: The measures for each research question.

### 3.4.1 Consistency

The within-puzzle standard deviation measures how far the ten runs of a puzzle spread around their own mean, after which the values are averaged over the hundred puzzles. The intraclass correlation treats every game as one score of its puzzle and asks how much of the total variation comes from differences between puzzles. ICC(1,1) describes a single game, while ICC(1,10) describes the mean of ten runs, which is the value that a difficulty estimate rests on. Both use a one-way random-effects model with absolute agreement and carry 95 percent intervals from the F distribution [11].

### 3.4.2 Agreement with Human Difficulty

Spearman ρ is the primary measure of agreement, since the categories of RQ2 are ordered and the human means are bounded by the game. Pearson r describes the same agreement on the raw values. Bias is the mean signed difference between the playtester and the human mean, so a positive value means that the playtester needs more guesses. MAE is the mean absolute difference, which is compared with a constant predictor that returns the human mean of the puzzles at hand. A bias-corrected MAE removes the shift of a condition, so a value below the constant baseline shows puzzle-level information beyond a constant offset. Tercile agreement maps every playtester mean to T1, T2 or T3 at the human cut-points, after which exact matches, adjacent matches and the quadratic-weighted κ summarize the confusion.

### 3.4.3 Persona Behavior

C2 has no advisors, so the persona measures apply to C1 and C3. GM retention is the share of turns in which the played word is the first proposal of the GM. Adoption counts the turns in which the played word comes from an advisor, while agreement counts the turns in which an advisor keeps the proposal in every round. The non-candidate share uses the candidate filter of the bridge, which keeps only the words that are still possible given the public feedback. It measures how often an advisor argues for a word that the game has already ruled out, which shows exploration rather than error for Cautious. A high share for Bold would contradict its playstyle instead. The same-word share counts the dissents that name the same word as another advisor in the same round, which measures how often independent advisors agree on an alternative.

Persona prompts can shape an LLM decision only when the debate carries them into the action [12], while debating agents may drift from their personas [13]. The persona measures therefore check that Cautious suggests non-candidates more often than Bold does. They also check that this gap exceeds the gap between two neutral advisors at the same positions in C3. A gap that survives both checks belongs to the playstyle rather than to the debate or to the position.

### 3.4.4 Contrasts and Robustness Checks

The two condition contrasts use the puzzle as the unit. For each puzzle the analysis takes the absolute error, the signed error and the within-puzzle standard deviation. A two-sided Wilcoxon signed-rank test then compares the paired values of two conditions, while their mean difference serves as the effect size. A Holm correction keeps the two contrasts at a family-wise error of 0.05 per measure. A test between two correlations would need several hundred puzzles, so each correlation is tested against zero and report the differences as values.

The persona check is position-matched. Bold holds the first slot and Cautious the second in C1, while neutral_1 holds the first and neutral_2 the second in C3. Since no advisor sees the advice of its own round, the gap between the two neutral advisors is the difference that one shared instruction can produce by chance. For each puzzle the analysis takes the mean per-game difference between the second and the first speaker in both conditions. A Wilcoxon test over the puzzles asks whether the gap of C1 exceeds the gap of C3, which the personas must do to count as working.

Three robustness checks repeat the main measures under another choice. The quartile split replaces the terciles and missing games are scored as losses, while the seven-bin distribution is pooled by category instead of by puzzle. The last check follows from the ten runs per puzzle, since a single bin share of one puzzle then has a margin of about 36 percentage points [14]. The first two checks test whether the results depend on the split, while the third sets the precision of a single puzzle.

## References

[1] Y. Zhao and C. Tang, "Towards LLM-based automatic playtest," in *Proc. 33rd ACM Int. Conf. Foundations of Software Engineering (FSE Companion)*, Trondheim, Norway, Jun. 2025, pp. 1645–1651, doi: 10.1145/3696630.3728700.  
[2] A. Drachen, A. Canossa, and G. N. Yannakakis, "Player modeling using self-organization in Tomb Raider: Underworld," in *Proc. IEEE Symp. Computational Intelligence and Games (CIG)*, Milan, Italy, 2009, pp. 1–8, doi: 10.1109/CIG.2009.5286500.  
[3] R. C. Wilson, A. Geana, J. M. White, E. A. Ludvig, and J. D. Cohen, "Humans use directed and random exploration to solve the explore–exploit dilemma," *J. Exp. Psychol.: General*, vol. 143, no. 6, pp. 2074–2081, 2014, doi: 10.1037/a0038199.  
[4] D. Bertsimas and A. Paskov, "An exact solution to Wordle," *Operations Research*, vol. 73, no. 3, pp. 1384–1394, 2025, doi: 10.1287/opre.2022.0434.  
[5] J. Liang, A. Kabbara, J. Liu, R. Luo, K. Kim, and M. Guerzhoy, "Semantic, orthographic, and phonological biases in humans' Wordle gameplay," in *Findings of the Association for Computational Linguistics: IJCNLP-AACL 2025*, 2025, *arXiv:2411.18634*.  
[6] Y. Du, S. Li, A. Torralba, J. B. Tenenbaum, and I. Mordatch, "Improving factuality and reasoning in language models through multiagent debate," in *Proc. 41st Int. Conf. Machine Learning (ICML)*, PMLR, vol. 235, 2024.  
[7] T. Liang *et al.*, "Encouraging divergent thinking in large language models through multi-agent debate," in *Proc. 2024 Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Miami, FL, USA, 2024, pp. 17889–17904, doi: 10.18653/v1/2024.emnlp-main.992.  
[8] T. Atkins Jr., "wordle-list," GitHub repository, Sep. 2022. [Online]. Available: https://github.com/tabatkins/wordle-list  
[9] C. Xiao and Z. Yang, "LLMs may not be human-level players, but they can be testers: Measuring game difficulty with LLM agents," *Proc. ACM Hum.-Comput. Interact.*, vol. 9, no. 6, pp. 1097–1123, Oct. 2025, doi: 10.1145/3748634.  
[10] A. P. Smit, N. Grinsztajn, P. Duckworth, T. D. Barrett, and A. Pretorius, "Should we be going MAD? A look at multi-agent debate strategies for LLMs," in *Proc. 41st Int. Conf. Machine Learning (ICML)*, PMLR, vol. 235, 2024.  
[11] T. K. Koo and M. Y. Li, "A guideline of selecting and reporting intraclass correlation coefficients for reliability research," *Journal of Chiropractic Medicine*, vol. 15, no. 2, pp. 155–163, Jun. 2016, doi: 10.1016/j.jcm.2016.02.012.  
[12] J. Licato, S. Steinle, and B. Hollis, "Do persona-infused LLMs affect performance in a strategic reasoning game?" in *Proc. IJCNLP-AACL 2025*, 2025, *arXiv:2512.06867*.  
[13] R. Baltaji, B. Hemmatian, and L. R. Varshney, "Persona inconstancy in multi-agent LLM collaboration: Conformity, confabulation, and impersonation," in *Proc. 2nd Workshop on Cross-Cultural Considerations in NLP (C3NLP)*, 2024, *arXiv:2405.03862*.  
[14] S. K. Thompson, "Sample size for estimating multinomial proportions," *The American Statistician*, vol. 41, no. 1, pp. 42–46, 1987, doi: 10.1080/00031305.1987.10475440.

## Appendix A Agent Prompts

| Agent | Instruction | Per-turn task |
|--------------|--------------------------------------------------|--------------------------------------------------|
| Game Master | You are the GM in a Wordle playtesting system. Propose a guess based on the available game state. After the advisors respond, evaluate every advisor's argument and retain or revise your proposal. Do not invent game feedback or claim unanimous agreement. | Supplied by the graph: propose an initial action, then review every suggestion and set stop only when another round is unlikely to change the decision. |
| Bold | You are the Bold advisor in a Wordle playtesting system. You prefer guesses that could still be the answer, so the game can be won as early as possible. Critique the GM's proposal from this view and suggest a better candidate answer if one exists. Accept the risk of using more guesses later. | Critique the current GM proposal from the Bold view. Suggest a guess that could still be the answer and explain why. If the proposal is already the best such guess, return it unchanged. Set stop to false. |
| Cautious | You are the Cautious advisor in a Wordle playtesting system. You prefer guesses that rule out the most remaining letters, even if the guess cannot be the answer. Critique the GM's proposal from this view and suggest a more informative guess if one exists. Your priority is never losing the game. | Critique the current GM proposal from the Cautious view. Suggest the guess that rules out the most remaining letters and explain why, even if it cannot be the answer. If the proposal is already the most informative guess, return it unchanged. Set stop to false. |
| Casual | You are the Casual advisor in a Wordle playtesting system. You play like a typical daily player. You prefer common, familiar words and a habitual opening word. You do not compute letter statistics. Critique the GM's proposal from this view and suggest the guess an everyday player would make. | Respond to the current GM proposal as an everyday player. Suggest the guess you would make and explain why in plain terms. If you would play the proposal too, return it unchanged. Set stop to false. |
| Neutral advisor (C3) | You are an advisor in a Wordle playtesting system. Critique the GM's proposal and suggest a better guess if one exists. If you see no clear improvement, return the proposal unchanged. | Critique the current GM proposal. If you see a better guess, suggest it and explain why. Otherwise return the proposal unchanged. Set stop to false. |
| Solo player (C2) | You are a player in a Wordle playtesting system. Choose the next guess based on the available game state and explain your choice briefly. Do not invent game feedback. | Choose the next guess and explain why. Set stop to false. |

Table: The instruction and per-turn task of every agent. The last two rows belong to the two reference conditions, C2 and C3.
