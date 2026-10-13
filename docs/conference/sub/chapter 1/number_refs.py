"""Replace [@key; @key] citations with IEEE numbers in order of first appearance."""
import re
import sys

REFS = {
    "weber2020": 'M. Weber and P. Notargiacomo, "Dynamic difficulty adjustment in digital games using genetic algorithms," in *Proc. 19th Brazilian Symp. Computer Games and Digital Entertainment (SBGames)*, Recife, Brazil, Nov. 2020, pp. 62–70, doi: 10.1109/SBGames51465.2020.00019.',
    "karavidas2022": 'L. Karavidas, H. Apostolidis, and T. Tsiatsos, "Usability evaluation of an adaptive serious game prototype based on affective feedback," *Information*, vol. 13, no. 9, p. 425, Sep. 2022, doi: 10.3390/info13090425.',
    "romero2023": 'E. A. Romero-Mendez, P. C. Santana-Mancilla, M. Garcia-Ruiz, O. A. Montesinos-López, and L. E. Anido-Rifón, "The use of deep learning to improve player engagement in a video game through a dynamic difficulty adjustment based on skills classification," *Applied Sciences*, vol. 13, no. 14, p. 8249, Jul. 2023, doi: 10.3390/app13148249.',
    "alvarado2021": 'D. A. Alvarado Villa, O. A. Montesinos López, and P. C. Santana-Mancilla, "Training of an intelligent agent to improve the gaming experience for video gamers," *Avances en IHC*, vol. 6, no. 1, pp. 123–125, Nov. 2021, doi: 10.47756/aihc.y6i1.105.',
    "prasetya2026": 'I. S. W. B. Prasetya *et al.*, "Programming smart playtesting," *ACM Trans. Softw. Eng. Methodol.*, vol. 35, no. 3, pp. 1–47, Mar. 2026, doi: 10.1145/3742473.',
    "zhao2025": 'Y. Zhao and C. Tang, "Towards LLM-based automatic playtest," in *Proc. 33rd ACM Int. Conf. Foundations of Software Engineering (FSE Companion)*, Trondheim, Norway, Jun. 2025, pp. 1645–1651, doi: 10.1145/3696630.3728700.',
    "bateni2024": 'B. Bateni and J. Whitehead, "Language-driven play: Large language models as game-playing agents in Slay the Spire," in *Proc. 19th Int. Conf. Foundations of Digital Games*, Worcester, MA, USA, May 2024, pp. 1–10, doi: 10.1145/3649921.3650013.',
    "xiao2025": 'C. Xiao and Z. Yang, "LLMs may not be human-level players, but they can be testers: Measuring game difficulty with LLM agents," *Proc. ACM Hum.-Comput. Interact.*, vol. 9, no. 6, pp. 1097–1123, Oct. 2025, doi: 10.1145/3748634.',
    "sreedhar2025": 'K. Sreedhar and L. Chilton, "Simulating strategic reasoning: Comparing the ability of single LLMs and multi-agent systems to replicate human behavior," in *Proc. 58th Hawaii Int. Conf. System Sciences (HICSS)*, 2025, doi: 10.24251/HICSS.2025.100.',
    "constant2017": 'T. Constant, G. Levieux, A. Buendia, and S. Natkin, "From objective to subjective difficulty evaluation in video games," in *Human-Computer Interaction – INTERACT 2017*, Lecture Notes in Computer Science, vol. 10514. Cham, Switzerland: Springer, 2017, pp. 107–127, doi: 10.1007/978-3-319-67684-5_8.',
    "liang2024": 'T. Liang *et al.*, "Encouraging divergent thinking in large language models through multi-agent debate," in *Proc. 2024 Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Miami, FL, USA, 2024, pp. 17889–17904, doi: 10.18653/v1/2024.emnlp-main.992.',
    "du2024": 'Y. Du, S. Li, A. Torralba, J. B. Tenenbaum, and I. Mordatch, "Improving factuality and reasoning in language models through multiagent debate," in *Proc. 41st Int. Conf. Machine Learning (ICML)*, PMLR, vol. 235, 2024.',
    "smit2024": 'A. P. Smit, N. Grinsztajn, P. Duckworth, T. D. Barrett, and A. Pretorius, "Should we be going MAD? A look at multi-agent debate strategies for LLMs," in *Proc. 41st Int. Conf. Machine Learning (ICML)*, PMLR, vol. 235, 2024.',
    "gudmundsson2018": 'S. F. Gudmundsson *et al.*, "Human-like playtesting with deep learning," in *Proc. 2018 IEEE Conf. Computational Intelligence and Games (CIG)*, Maastricht, Netherlands, 2018, pp. 1–8.',
    "delfosse2025": 'Q. Delfosse *et al.*, "Deep reinforcement learning agents are not even close to human intelligence," 2025, *arXiv preprint*.',
    "francillette2025": 'Y. Francillette, H. Tremblay, B. Bouchard, and B.-A. Menelas, "A comprehensive model of automated evaluation of difficulty in platformer games," *ACM Games: Research and Practice*, vol. 3, no. 1, Jan. 2025, doi: 10.1145/3705013.',
    "feng2023": 'X. Feng *et al.*, "ChessGPT: Bridging policy learning and language modeling," in *Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track*, 2023.',
    "hu2024": 'S. Hu, T. Huang, and L. Liu, "PokeLLMon: A human-parity agent for Pokémon battles with large language models," 2024, *arXiv:2402.01118*.',
    "wang2023": 'G. Wang *et al.*, "Voyager: An open-ended embodied agent with large language models," 2023, *arXiv:2305.16291*, doi: 10.48550/arXiv.2305.16291.',
    "holmgard2019": 'C. Holmgård, M. C. Green, A. Liapis, and J. Togelius, "Automated playtesting with procedural personas through MCTS with evolved heuristics," *IEEE Trans. Games*, vol. 11, no. 4, pp. 352–362, Dec. 2019.',
    "chan2024": 'C.-M. Chan *et al.*, "ChatEval: Towards better LLM-based evaluators through multi-agent debate," in *Proc. 12th Int. Conf. Learning Representations (ICLR)*, 2024.',
    "engagingdata": 'Engaging Data, "Wordle guess distribution." [Online]. Available: https://engaging-data.com/wordle-guess-distribution/ (accessed [TODO: date]).',
    "stsdata": '[TODO: cite the source of the Slay the Spire run dataset released by Mega Crit (more than 75 million runs).]',
}

CITE = re.compile(r"\[(@[\w]+(?:;\s*@[\w]+)*)\]")


def main(src, dst):
    text = open(src, encoding="utf-8").read()
    order = {}

    def repl(m):
        keys = [k.strip().lstrip("@") for k in m.group(1).split(";")]
        nums = []
        for k in keys:
            if k not in REFS:
                sys.exit(f"unknown key: {k}")
            order.setdefault(k, len(order) + 1)
            nums.append(order[k])
        return ", ".join(f"[{n}]" for n in sorted(nums))

    body = CITE.sub(repl, text)
    unused = set(REFS) - set(order)
    if unused:
        print("unused:", sorted(unused))
    refs = "\n".join(f"[{n}] {REFS[k]}" + "  " for k, n in sorted(order.items(), key=lambda x: x[1]))
    body = body.replace("{{REFERENCES}}", refs.rstrip())
    open(dst, "w", encoding="utf-8").write(body)
    print(f"{len(order)} references")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
