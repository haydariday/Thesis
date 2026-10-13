# CHAPTER 1 INTRODUCTION

## 1.1 Background

"Is the game hard enough for the intended player?" is one of the key questions that game designers keep asking during development. A game that is too hard drives players away while one that is too easy soon becomes stale, both of which risk losing players and receiving a negative reception [1], [2]. That is why difficulty can be an indicator of player engagement and experience [3], [4]. Designers measure this difficulty through playtesting. However, manual playtesting is resource-intensive since it needs many testers over many sessions and has to be repeated after every significant design change [1], [5], [6]. For indie game developers with limited budgets, this cost is often prohibitive. Thus, they need a cheaper way to obtain difficulty data that still reflects human players.

Automatic playtesting has gained popularity among industry and academic researchers alike. The methods explored so far fall into two groups. Hand-crafted methods, such as programmed test agents [5] and mathematical difficulty models [7], require heavy engineering effort for each game or genre. Learning-based methods such as deep reinforcement learning need large training resources while also tending to play in ways that humans would not [8]. Large Language Models (LLMs) provide an alternative, as LLM agents can play games ranging from chess [9] to Pokémon battles [10] and Minecraft [11] using only a text description of the rules. Xiao and Yang [12] show that the difficulty LLM agents experience in Wordle and Slay the Spire follows that of human players, even though the agents play worse. However, these LLM playtesters rely on a single agent that plays with only one playstyle. Human players are more diverse, as some take risks while others play safely. The difficulty that matters to a designer is the one experienced by this diverse population. Moreover, single LLMs replicate human strategic behavior less closely than multi-agent systems do [13]. Thus, it remains unclear whether an LLM playtester can produce difficulty data that is both consistent and aligned with human players once multiple playstyles are considered.

To accommodate this gap, we establish a persona-based multi-agent LLM debate framework that acts as an automated playtester. Such a playtester plays a game through the same actions available to a human player while recording the outcome of each playthrough. Game difficulty here refers to objective difficulty, which is the part of difficulty measured from play outcomes rather than the difficulty perceived by individual players [14]. In this framework, several LLM agents with different playstyle personas debate each in-game decision until they reach consensus on the action to play. In other words, the agents reach consensus on what to play rather than on how hard the game is. The difficulty data comes from the outcome of each playthrough, such as the number of guesses used. These outcomes are then compared with human performance baselines, which are the average results of real players on the same puzzles. The exact agent roles and debate protocol are defined later in the research method.

We employ Wordle as the case study for three reasons. First, its games are short with deterministic feedback. Second, it was studied by Xiao and Yang [12], so our results can be related to prior single-agent work. Third, Wordle has public per-puzzle human results [15] that express the difficulty of each puzzle as the average number of guesses human players needed. The playtester plays a random sample of historical puzzles several times each. We measure how much its outcomes vary across repeated runs of the same puzzle. We also measure how well its average guess counts agree with the human averages, both as continuous scores and as ordered difficulty categories. In addition, token usage and run time are recorded to describe the cost of the debate. This study validates the playtester as a system rather than testing whether debate outperforms a single agent. The contribution of this study is a persona-based debate playtester for game difficulty evaluation, along with evidence of how consistent its outcomes are and how closely they follow human difficulty.

## 1.2 Problem Identification

The background shows that game designers still lack an automated playtester whose outcomes can serve as evidence of game difficulty for human players. For the proposed playtester, two conditions must hold before its outcomes can be used this way. First, the outcomes must be consistent across runs. Since LLM outputs vary between calls, the same puzzle can end differently on different runs, which leaves a designer with little to rely on. Second, the outcomes must agree with human difficulty, because a consistent playtester that finds every puzzle equally easy is still of no use. These two conditions lead to the following research questions:

- **RQ1.** How consistent are the Wordle playtest outcomes produced by the persona-based multi-agent debate playtester across repeated runs on the same puzzles?
- **RQ2.** To what extent do the Wordle difficulty estimates derived from the playtester's outcomes agree with human difficulty, measured by average guess scores and difficulty categories?

Answering both questions shows whether the playtester can be trusted as a source of difficulty data for Wordle, which is the first step toward solving the general problem.

## 1.3 Objective and Hypotheses

The objectives of this research are threefold:

1. To implement a persona-based multi-agent LLM debate playtester for Wordle, in which agents with different playstyle personas reach consensus on each guess while every playthrough is logged as difficulty data.
2. To measure the consistency of the playtester's outcomes across repeated runs of the same puzzles.
3. To measure the agreement between the playtester's difficulty estimates and human performance baselines, using both average guess scores and difficulty categories.

The hypotheses based on the RQs are:

- **H1.** The playtester produces consistent outcomes across repeated runs, with low variation in guess scores within each puzzle.
- **H2.** The playtester's average guess scores correlate positively with human average guess scores, while it assigns puzzles to the same difficulty categories as humans more often than a majority-class baseline.

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
[15] Engaging Data, "Wordle guess distribution." [Online]. Available: https://engaging-data.com/wordle-guess-distribution/ (accessed [TODO: date]).
