# CHAPTER 1 INTRODUCTION

## 1.1 Background

"Is the game hard enough for the intended player?" is one of the key questions that game designers keep asking during development [1]. A game that is too hard drives players away while one that is too easy soon becomes stale, both of which risk losing players and receiving a negative reception [2]. That is why difficulty can be an indicator of player engagement and experience [3], [4]. Designers measure this difficulty through playtesting. However, manual playtesting is resource-intensive since it needs many testers over many sessions and has to be repeated after every significant design change [1], [5], [6]. For indie game developers with limited budgets, this cost is often prohibitive. Thus, they need a cheaper way to obtain difficulty data that still reflects human players.

Automatic playtesting has gained popularity among industry and academic researchers alike. The methods explored so far fall into two groups. Hand-crafted methods, such as programmed test agents [5] and mathematical difficulty models [7], require heavy engineering effort for each game or genre. Learning-based methods such as deep reinforcement learning need large training resources while also tending to play in ways that humans would not [8]. Large Language Models (LLMs) provide an alternative, as LLM agents can play games ranging from chess [9] to Pokémon battles [10] and Minecraft [11] using only a text description of the rules. Xiao and Yang [12] show that the difficulty LLM agents experience in Wordle and Slay the Spire follows that of human players, even though the agents play worse. However, these LLM playtesters rely on a single agent that plays with only one playstyle. Human players are more diverse, as some take risks while others play safely. The difficulty that matters to a designer is the one experienced by this diverse population. Moreover, single LLMs replicate human strategic behavior less closely than multi-agent systems do [13]. Thus, it remains unclear whether an LLM playtester can produce difficulty data that is both consistent and aligned with human players once multiple playstyles are considered.

To accommodate this gap, we establish a persona-based multi-agent LLM debate framework that acts as an automated playtester. Such a playtester plays a game through the same actions available to a human player while recording the outcome of each playthrough. Game difficulty here refers to objective difficulty, which is the part of difficulty measured from play outcomes rather than the difficulty perceived by individual players [14]. In this framework, several LLM agents with different playstyle personas debate each in-game decision until they reach consensus on the action to play. In other words, the agents reach consensus on what to play rather than on how hard the game is. The difficulty data comes from the outcome of each playthrough, such as the number of guesses used. These outcomes are then compared with human performance baselines, which are the average results of real players on the same puzzles. The exact agent roles and debate protocol are defined later in the research method.

We employ Wordle as the case study for three reasons. First, its games are short with deterministic feedback. Second, it was studied by Xiao and Yang [12], so our results can be related to prior single-agent work. Third, Wordle has public per-puzzle human results^[Engaging Data, "Wordle Guess Distribution," <https://engaging-data.com/wordle-guess-distribution/>.] that express the difficulty of each puzzle as the average number of guesses human players needed. The playtester plays a sample of historical puzzles several times each, after which we measure how much its outcomes vary across repeated runs of the same puzzle. We also measure how well its average guess counts agree with the human averages, both as continuous scores and as ordered difficulty categories. In addition, we describe how the playstyle personas behave during the debate, since a persona-based playtester is only meaningful when its personas actually shape the guesses.

## 1.2 Problem Statement

The background shows that game designers still lack an automated playtester whose outcomes can serve as evidence of game difficulty for human players. Existing LLM playtesters use a single agent with one playstyle [12], while the difficulty that matters to a designer is the one experienced by a diverse player population. For a persona-based playtester to fill this gap, two conditions must hold before its outcomes can be used as difficulty data. First, the outcomes must be consistent across runs. Since LLM outputs vary between calls, the same puzzle can end differently on different runs, which leaves a designer with little to rely on. Xiao and Yang [12] play each Wordle puzzle 20 times yet report only the average outcome, so this consistency is still unknown. Second, the outcomes must agree with human difficulty [12], because a consistent playtester that finds every puzzle equally easy is still of no use. Moreover, the playtester is only persona-based in practice if its personas keep their playstyles during the debate. Debating LLM agents may conform to their peers instead of keeping their assigned personas [15], which would leave a single playstyle behind the outcomes. This research therefore examines whether the proposed playtester meets both conditions in Wordle while describing how its personas behave.

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

This research focuses on Wordle as a single case study. The playtester plays past Wordle puzzles for which public human results are available, so that every outcome has a human counterpart to compare with. Game difficulty is limited to objective difficulty, which is measured from how many guesses the playtester needs to solve each puzzle [14]. The playtester is evaluated as a whole system, judged by how consistent its outcomes are and how closely they agree with human players. The behavior of the personas is described from the debate records rather than tested by removing or swapping personas.

This research also has several limitations. It does not compare the debate playtester with a single-agent playtester [13]. Its persona analysis is also descriptive, so it shows how the personas take part in the debate without proving that any persona causes the outcomes. Moreover, the human baselines describe players as a group rather than as individuals, so the comparison can only be made for each puzzle as a whole. The difficulty perceived by players is not studied either [14], since no human participants are involved. Finally, the findings apply to Wordle and to the LLM used in this research, while other games such as Slay the Spire [12] may behave differently.

## 1.6 Expected Contributions

This research is expected to contribute in four ways. First, it offers an automated playtester in which LLM agents with different playstyles decide together how to play a game. Second, it shows whether such a playtester gives similar results when it plays the same game again. Third, it shows how closely the difficulty found by the playtester follows the difficulty experienced by human players. Fourth, it shows how the playstyle personas take part in the debate, which reveals whether they actually shape the play.

For indie game developers, these results indicate whether an LLM playtester can provide difficulty data that reflects human players, which would reduce their reliance on manual playtesting [5], [6]. For researchers, this research extends earlier work on LLM playtesters [12] from a single agent to several agents with different playstyles [13].

## References

[1] M. Weber and P. Notargiacomo, "Dynamic difficulty adjustment in digital games using genetic algorithms," in *Proc. 19th Brazilian Symp. Computer Games and Digital Entertainment (SBGames)*, Recife, Brazil, Nov. 2020, pp. 62–70, doi: 10.1109/SBGames51465.2020.00019.  
[2] L. Karavidas, H. Apostolidis, and T. Tsiatsos, "Usability evaluation of an adaptive serious game prototype based on affective feedback," *Information*, vol. 13, no. 9, p. 425, Sep. 2022, doi: 10.3390/info13090425.  
[3] E. A. Romero-Mendez, P. C. Santana-Mancilla, M. Garcia-Ruiz, O. A. Montesinos-López, and L. E. Anido-Rifón, "The use of deep learning to improve player engagement in a video game through a dynamic difficulty adjustment based on skills classification," *Applied Sciences*, vol. 13, no. 14, p. 8249, Jul. 2023, doi: 10.3390/app13148249.  
[4] D. A. Alvarado Villa, O. A. Montesinos López, and P. C. Santana-Mancilla, "Training of an intelligent agent to improve the gaming experience for video gamers," *Avances en IHC*, vol. 6, no. 1, pp. 123–125, Nov. 2021, doi: 10.47756/aihc.y6i1.105.  
[5] I. S. W. B. Prasetya *et al.*, "Programming smart playtesting," *ACM Trans. Softw. Eng. Methodol.*, vol. 35, no. 3, pp. 1–47, Mar. 2026, doi: 10.1145/3742473.  
[6] Y. Zhao and C. Tang, "Towards LLM-based automatic playtest," in *Proc. 33rd ACM Int. Conf. Foundations of Software Engineering (FSE Companion)*, Trondheim, Norway, Jun. 2025, pp. 1645–1651, doi: 10.1145/3696630.3728700.  
[7] Y. Francillette, H. Tremblay, B. Bouchard, and B.-A. Menelas, "A comprehensive model of automated evaluation of difficulty in platformer games," *ACM Games: Research and Practice*, vol. 3, no. 1, Jan. 2025, doi: 10.1145/3705013.  
[8] Q. Delfosse *et al.*, "Deep reinforcement learning agents are not even close to human intelligence," 2025, *arXiv preprint*.  
[9] X. Feng *et al.*, "ChessGPT: Bridging policy learning and language modeling," in *Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track*, 2023.  
[10] S. Hu, T. Huang, and L. Liu, "PokeLLMon: A human-parity agent for Pokémon battles with large language models," 2024, *arXiv:2402.01118*.  
[11] G. Wang *et al.*, "Voyager: An open-ended embodied agent with large language models," 2023, *arXiv:2305.16291*, doi: 10.48550/arXiv.2305.16291.  
[12] C. Xiao and Z. Yang, "LLMs may not be human-level players, but they can be testers: Measuring game difficulty with LLM agents," *Proc. ACM Hum.-Comput. Interact.*, vol. 9, no. 6, pp. 1097–1123, Oct. 2025, doi: 10.1145/3748634.  
[13] K. Sreedhar and L. Chilton, "Simulating strategic reasoning: Comparing the ability of single LLMs and multi-agent systems to replicate human behavior," in *Proc. 58th Hawaii Int. Conf. System Sciences (HICSS)*, 2025, doi: 10.24251/HICSS.2025.100.  
[14] T. Constant, G. Levieux, A. Buendia, and S. Natkin, "From objective to subjective difficulty evaluation in video games," in *Human-Computer Interaction – INTERACT 2017*, Lecture Notes in Computer Science, vol. 10514. Cham, Switzerland: Springer, 2017, pp. 107–127, doi: 10.1007/978-3-319-67684-5_8.  
[15] R. Baltaji, B. Hemmatian, and L. R. Varshney, "Persona inconstancy in multi-agent LLM collaboration: Conformity, confabulation, and impersonation," in *Proc. 2nd Workshop on Cross-Cultural Considerations in NLP (C3NLP)*, 2024, *arXiv:2405.03862*.
