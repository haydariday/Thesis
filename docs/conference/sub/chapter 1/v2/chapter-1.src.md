# CHAPTER 1 INTRODUCTION

## 1.1 Background

"Is the game hard enough for the intended player?" is one of the key questions that game designers keep asking during development [@weber2020]. A game that is too hard drives players away while one that is too easy soon becomes stale, both of which risk losing players and receiving a negative reception [@karavidas2022]. That is why difficulty can be an indicator of player engagement and experience [@romero2023; @alvarado2021]. Designers measure this difficulty through playtesting. However, manual playtesting is resource-intensive since it needs many testers over many sessions and has to be repeated after every significant design change [@weber2020; @prasetya2026; @zhao2025]. For indie game developers with limited budgets, this cost is often prohibitive. Thus, they need a cheaper way to obtain difficulty data that still reflects human players.

Automatic playtesting has gained popularity among industry and academic researchers alike. The methods explored so far fall into two groups. Hand-crafted methods, such as programmed test agents [@prasetya2026] and mathematical difficulty models [@francillette2025], require heavy engineering effort for each game or genre. Learning-based methods such as deep reinforcement learning need large training resources while also tending to play in ways that humans would not [@delfosse2025]. Large Language Models (LLMs) provide an alternative, as LLM agents can play games ranging from chess [@feng2023] to Pokémon battles [@hu2024] and Minecraft [@wang2023] using only a text description of the rules. Xiao and Yang [@xiao2025] show that the difficulty LLM agents experience in Wordle and Slay the Spire follows that of human players, even though the agents play worse. However, these LLM playtesters rely on a single agent that plays with only one playstyle. Human players are more diverse, as some take risks while others play safely. The difficulty that matters to a designer is the one experienced by this diverse population. Moreover, single LLMs replicate human strategic behavior less closely than multi-agent systems do [@sreedhar2025]. Thus, it remains unclear whether an LLM playtester can produce difficulty data that is both consistent and aligned with human players once multiple playstyles are considered.

To accommodate this gap, we establish a persona-based multi-agent LLM debate framework that acts as an automated playtester. Such a playtester plays a game through the same actions available to a human player while recording the outcome of each playthrough. Game difficulty here refers to objective difficulty, which is the part of difficulty measured from play outcomes rather than the difficulty perceived by individual players [@constant2017]. In this framework, several LLM agents with different playstyle personas debate each in-game decision until they reach consensus on the action to play. In other words, the agents reach consensus on what to play rather than on how hard the game is. The difficulty data comes from the outcome of each playthrough, such as the number of guesses used. These outcomes are then compared with human performance baselines, which are the average results of real players on the same puzzles. The exact agent roles and debate protocol are defined later in the research method.

We employ Wordle as the case study for three reasons. First, its games are short with deterministic feedback. Second, it was studied by Xiao and Yang [@xiao2025], so our results can be related to prior single-agent work. Third, Wordle has public per-puzzle human results^[Engaging Data, "Wordle Guess Distribution," <https://engaging-data.com/wordle-guess-distribution/>.] that express the difficulty of each puzzle as the average number of guesses human players needed. The playtester plays a sample of historical puzzles several times each, after which we measure how much its outcomes vary across repeated runs of the same puzzle. We also measure how well its average guess counts agree with the human averages, both as continuous scores and as ordered difficulty categories. In addition, we describe how the playstyle personas behave during the debate, since a persona-based playtester is only meaningful when its personas actually shape the guesses.

## 1.2 Problem Statement

The background shows that game designers still lack an automated playtester whose outcomes can serve as evidence of game difficulty for human players. Existing LLM playtesters use a single agent with one playstyle [@xiao2025], while the difficulty that matters to a designer is the one experienced by a diverse player population. For a persona-based playtester to fill this gap, two conditions must hold before its outcomes can be used as difficulty data. First, the outcomes must be consistent across runs. Since LLM outputs vary between calls, the same puzzle can end differently on different runs, which leaves a designer with little to rely on. Xiao and Yang [@xiao2025] play each Wordle puzzle 20 times yet report only the average outcome, so this consistency is still unknown. Second, the outcomes must agree with human difficulty [@xiao2025], because a consistent playtester that finds every puzzle equally easy is still of no use. Moreover, the playtester is only persona-based in practice if its personas keep their playstyles during the debate. Debating LLM agents may conform to their peers instead of keeping their assigned personas [@baltaji2024], which would leave a single playstyle behind the outcomes. This research therefore examines whether the proposed playtester meets both conditions in Wordle while describing how its personas behave.

## 1.3 Research Questions

Based on the problem statement, this research addresses the following research questions:

- **RQ1.** How consistent are the Wordle playtest outcomes produced by the persona-based multi-agent debate playtester across repeated runs on the same puzzles?
- **RQ2.** To what extent do the Wordle difficulty estimates derived from the playtester's outcomes agree with human difficulty, measured by average guess scores and difficulty categories?
- **RQ3.** How do the playstyle personas behave during the debate, and how strongly do their suggestions shape the final guesses?

Answering RQ1 and RQ2 shows whether the playtester can be trusted as a source of difficulty data for Wordle, which is the first step toward solving the general problem. RQ3 shows whether the personas actually take part in producing that data.

## 1.4 Research Objectives

The objectives of this research are fourfold:

1. To implement a persona-based multi-agent LLM debate playtester for Wordle, in which agents with different playstyle personas reach consensus on each guess while every playthrough is logged as difficulty data.
2. To measure the consistency of the playtester's outcomes across repeated runs of the same puzzles, which answers RQ1.
3. To measure the agreement between the playtester's difficulty estimates and human performance baselines using both average guess scores and difficulty categories, which answers RQ2.
4. To describe how each playstyle persona behaves during the debate and how often its suggestions are adopted in the final guesses, which answers RQ3.

## 1.5 Scope and Limitations

This research focuses on Wordle as a single case study. The playtester plays past Wordle puzzles for which public human results are available, so that every outcome has a human counterpart to compare with. Game difficulty is limited to objective difficulty, which is measured from how many guesses the playtester needs to solve each puzzle [@constant2017]. The playtester is evaluated as a whole system, judged by how consistent its outcomes are and how closely they agree with human players. The behavior of the personas is described from the debate records rather than tested by removing or swapping personas.

This research also has several limitations. It does not compare the debate playtester with a single-agent playtester [@sreedhar2025]. Its persona analysis is also descriptive, so it shows how the personas take part in the debate without proving that any persona causes the outcomes. Moreover, the human baselines describe players as a group rather than as individuals, so the comparison can only be made for each puzzle as a whole. The difficulty perceived by players is not studied either [@constant2017], since no human participants are involved. Finally, the findings apply to Wordle and to the LLM used in this research, while other games such as Slay the Spire [@xiao2025] may behave differently.

## 1.6 Expected Contributions

This research is expected to contribute in four ways. First, it offers an automated playtester in which LLM agents with different playstyles decide together how to play a game. Second, it shows whether such a playtester gives similar results when it plays the same game again. Third, it shows how closely the difficulty found by the playtester follows the difficulty experienced by human players. Fourth, it shows how the playstyle personas take part in the debate, which reveals whether they actually shape the play.

For indie game developers, these results indicate whether an LLM playtester can provide difficulty data that reflects human players, which would reduce their reliance on manual playtesting [@prasetya2026; @zhao2025]. For researchers, this research extends earlier work on LLM playtesters [@xiao2025] from a single agent to several agents with different playstyles [@sreedhar2025].

## References

{{REFERENCES}}
