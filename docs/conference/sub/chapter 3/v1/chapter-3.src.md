# CHAPTER 3 RESEARCH METHODOLOGY

## 3.1 Playtester Design

The playtester has three parts around the game environment, which are the bridge, the multi-agent debate and the game knowledge (Figure 3.1). In each turn, the bridge converts the public game state into text, since an LLM cannot see the game board [@zhao2025]. The agents then debate the next guess from this state, after which the Game Master (GM) decides the final guess. The bridge plays this guess in the game as the consensus action, while its feedback becomes the game state of the next turn.

![The persona-based multi-agent debate playtester for Wordle. The game environment is drawn as a dashed box, since it is the game under test.](../thesis-1/figures/fig-framework.png){width=95%}

### 3.1.1 Personas

The debate involves one GM with three advisors, each of which holds a playstyle persona (Table 3.1).

| Persona | Role | Playstyle |
|--------------|----------------|--------------------------------------------------|
| Game Master | Managing agent | Neutral. Proposes a guess, evaluates every advisor's argument and keeps or revises its proposal. |
| Bold | Advisor | Plays to win now. Prefers guesses that could still be the answer and accepts the risk of using more guesses later. |
| Cautious | Advisor | Plays not to lose. Prefers guesses that rule out the most remaining letters, even if they cannot be the answer. |
| Casual | Advisor | Plays like a typical daily player. Prefers common, familiar words and does not compute letter statistics. |

Table: The personas of the debate.

Players do not share a single playstyle, as gameplay data reveals distinct player types [@drachen2009]. Wordle is a deterministic single-player game with imperfect information, so the only decision a player makes is how to spend each guess. A player may exploit with a word that could still be the answer, or explore with a word that mainly rules out letters. This trade-off is a classic problem in human decision making, where people seek more information when more choices remain [@wilson2014]. Optimal Wordle play leans toward exploration [@bertsimas2025], while real players tend to stay close to the words they have already tried [@liang2025]. Thus, the Bold advisor argues for guesses that could win immediately, while the Cautious advisor argues for guesses that narrow down the remaining words. The Casual advisor adds the typical daily player, who picks familiar words without computing letter statistics.

We use one advisor per playstyle rather than adding more advisors. Debates with three agents already show clear gains [@du2024], while longer debates make agents lose track of the views of others [@liang2024].

### 3.1.2 Bridge and Game Knowledge

The bridge reads the history of guesses with their feedback. Each letter turns green in its correct position, yellow when it belongs elsewhere in the word and gray when the word lacks it. This state is rendered as text with a keyboard-style letter summary, which plays the role of the colored keyboard that a human player sees. The summary lists the confirmed, misplaced and absent letters without any list of candidate words. The answer word, the guess limit and the human results never enter any prompt, so the playtester cannot copy the difficulty that it is measured against. In the other direction, the bridge accepts a final guess only if it is an unplayed word from the 14,855-word allowed-guess list of Wordle [@atkins2022]. Every agent also receives the same game knowledge, which holds the game rules, the reply format and its own persona instruction.

### 3.1.3 Debate Protocol

In the protocol, a managing agent oversees a reciprocal exchange between the other agents [@liang2024]. The GM first proposes a guess, after which Bold, Cautious and Casual read the proposal in this fixed order with the earlier suggestions of the round. Each advisor then agrees or suggests a different word with a short reason. The GM reviews every suggestion and keeps or revises its guess, which ends the round. A new round starts again from the first advisor, while the GM may stop early once another round is unlikely to change its decision. Three rounds is the upper limit, since each extra round adds four model calls to every turn. Every reply is a structured decision with an action, a reason and a stop flag, while an invalid reply is sent back for correction up to two times.

Figure 3.2 shows a logged turn, in which the GM proposes STORM although S is already ruled out at position 1. Bold and Cautious point this out and suggest STORK, while Casual agrees with STORM because it feels like a normal word. The GM adopts STORK, after which every advisor agrees with it in the next two rounds before it is played.

![The debate protocol in the second turn of a logged game. The quotes are shortened from the logged replies.](../thesis-1/figures/fig-debate.png){width=95%}

## 3.2 Human Baseline

The human baseline comes from the Engaging Data guess distribution introduced in Section 2.2, which gives the share of players who solved each past puzzle in 1 to 6 guesses. The remaining share is treated as a loss scored 7, which gives each puzzle a 7-bin distribution with a human mean. Four puzzles are removed for data errors, such as a missing sample size, which leaves 1,861 of 1,865 puzzles. These puzzles are sorted by their human mean and split into four equal quartiles, from D1 (easiest) to D4 (hardest). The cut-points of 3.98, 4.24 and 4.53 guesses were fixed before any game was played.

## 3.3 Experiment Design

The study consists of two experiments, since consistency is measured over repeated runs of the same puzzle while agreement is measured across many puzzles. Both experiments draw their puzzles at random from each quartile in equal numbers, without any puzzle in common (Table 3.2). Experiment A answers RQ1 and also checks RQ2, since its puzzle means rest on many games. Experiment B is the main evidence for RQ2, while RQ3 uses the debate turns of both experiments.

| | Experiment A (deep) | Experiment B (wide) |
|---|---|---|
| Puzzles | 12 (3 per quartile) | 48 (12 per quartile) |
| Runs per puzzle | 32 | 3 |
| Planned games | 384 | 144 |

Table: The two experiments of the study.

Thirty-two runs keep every bin share of a puzzle within 20 percentage points of its true value at 95% confidence [@thompson1987]. Twelve puzzles per quartile follow the rule of thumb of 12 units per group for a pilot study [@julious2005]. A failed game, such as one where an agent keeps giving invalid replies, is retried once, while only completed games are analyzed.

All agents run on DeepSeek-V4.1-Flash with its thinking mode disabled, temperature 0.2 and a 1,024-token reply limit. This configuration was frozen before the first run, so every game uses the same model, prompts and debate rules. Since an LLM agent loses many games within six guesses, the playtester plays with a hidden limit of 12 guesses as a handicap [@xiao2025]. The agents never see this limit, so their first six guesses are the same as under the normal rule. Each game is therefore read on two scores, of which the 12-guess score is the guess count as played with a loss scored 13. The 6-guess score cuts the game at six guesses, so a longer game becomes a loss scored 7 as in the human data.

## 3.4 Measures

Each research question is answered with a small set of measures (Table 3.3). The bias and the mean absolute error (MAE) use the 6-guess score, since they compare the playtester with the human data directly. Every other measure uses the 12-guess score. Correlations are reported with their p-values and read as very weak below 0.2, weak up to 0.4, moderate up to 0.6 and strong above 0.6 [@xiao2025].

| RQ | Measure | Definition |
|---------|---------------------|--------------------------------------------------|
| RQ1 | Within-puzzle SD | Spread of the guess counts over the runs of a puzzle, averaged over the puzzles. |
| RQ1 | ICC(1,1), ICC(1,k) | Share of the score variation that comes from the puzzle rather than from run-to-run noise, for one game and for the mean of k runs. |
| RQ2 | Pearson r, Spearman ρ | Agreement between the playtester's puzzle means and the human means, and between their orders of difficulty. |
| RQ2 | Bias, MAE | Mean difference and mean distance from the human mean, compared with a constant guess of the human average. |
| RQ2 | Rank quartiles | Playtester means split into four equal groups, then compared with the human quartiles in a confusion matrix. |
| RQ3 | GM retention | Share of turns in which the played word is the first proposal of the GM. |
| RQ3 | Adoption, agreement | Share of turns in which the GM switched to the advisor's word, and in which the advisor agreed with the GM in every round. |
| RQ3 | Non-candidate share | Share of an advisor's suggestions after the first turn that can no longer be the answer given the public feedback. |

Table: The measures for each research question.

For RQ3, persona prompts can improve LLM game play only when a mediator translates them into heuristic values [@licato2025]. Moreover, debating agents may drift from their assigned personas [@baltaji2024]. Thus, the Cautious advisor is expected to suggest non-candidates more often than the Bold advisor, which serves as a check that the personas behave as intended. This gap is reported with a 95% bootstrap interval that resamples whole games.

## References

{{REFERENCES}}
