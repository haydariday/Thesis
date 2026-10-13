# Wordle Playstyle Personas (Bold vs Cautious)

Status: suggestion only. Not yet reflected in the app or in Chapter 1.

## 1. Why the current personas do not fit the objective

Chapter 1 motivates the research with playstyle diversity: "some take risks while others play safely". The current Wordle agents in `src/multi_agent_testing/agent/personas.py` are debate roles rather than playstyles.

| Agent | Current instruction | Playstyle? |
|---|---|---|
| Game Master | Proposes a guess and keeps or revises it after the advisors respond | No, it is the moderator |
| Negative Advisor | Challenges the GM's guess and suggests an alternative | No, it is a critic |
| Positive Advisor | Defends the GM's guess against the critique | No, it is a defender |

All three agents share the same model and the same goal. None of them plays riskily or safely, so the "diverse population" argument in the background has nothing in the app behind it.

## 2. Proposal: explore vs exploit advisors

Wordle has no randomness, but players still decide how to spend six guesses. That decision is a real trade-off between risk and safety.

| Persona | Strategy | Risk profile |
|---|---|---|
| **Bold** (exploiter) | Always guesses a word that could still be the answer and plays to win now | Risky: it can solve in 2–3 guesses, but it can also run out of guesses |
| **Cautious** (explorer) | Willing to spend a guess on a word that cannot be the answer, to rule out as many letters as possible | Safe: it rarely loses, but it seldom gets a very fast solve |

### Example (checked with the Wordle feedback rules)

The board shows `_ATCH`. The candidates are HATCH, LATCH, MATCH, PATCH and WATCH, with three guesses left.

- **Bold** plays HATCH, then LATCH, then MATCH. It covers only 3 of the 5 candidates and loses if the answer is PATCH or WATCH.
- **Cautious** plays CLAMP, which can never be the answer. CLAMP separates LATCH, MATCH and PATCH, leaving at most the pair HATCH/WATCH, so the solve is guaranteed within the two remaining guesses.

The two advisors disagree for a real reason, which gives the GM something to decide.

### Fit with the debate and with Slay the Spire

- The GM still proposes and decides. Only the two advisor instructions change, so the LangGraph debate flow stays the same.
- The pairing follows the opposing-roles structure of Liang et al. (affirmative vs negative), with each side tied to a playstyle.
- It mirrors the planned Slay the Spire advisors (Aggressive vs Defensive), so both games would use the same persona logic.

### Draft instructions (for `personas.py`, later)

- **Bold:** "You are the Bold advisor in a Wordle playtesting system. You prefer guesses that could still be the answer, so the game can be won as early as possible. Critique the GM's proposal from this view and suggest a better candidate answer if one exists. Accept the risk of using more guesses later."
- **Cautious:** "You are the Cautious advisor in a Wordle playtesting system. You prefer guesses that rule out the most remaining letters, even if the guess cannot be the answer. Critique the GM's proposal from this view and suggest a more informative guess if one exists. Your priority is never losing the game."

## 3. Supporting evidence

Every claim below was checked against the paper or its official record on 10 October 2026, except where marked.

### Argument chain

| Claim | Evidence | Supports |
|---|---|---|
| Players differ in playstyle | [a] Drachen et al. found four player types from the play data of 1,365 *Tomb Raider: Underworld* players | Using several personas at all |
| Personas are an established playtesting method | [b] Holmgård et al. used procedural personas with different goals as synthetic playtesters | Persona-based playtesting |
| Explore vs exploit is a core human decision trade-off | [c] Wilson et al.: people seek more information (directed exploration) when more choices remain (longer horizon) | Bold vs Cautious as a real human dimension. In Wordle, the "horizon" is the number of guesses left |
| Optimal Wordle play explores | [d] Bertsimas & Paskov's exact solution answers LIGHT with FERMS, which cannot be the answer, instead of TIGHT or MIGHT. Only 2,315 of 10,657 valid guesses can ever be the answer | The **Cautious** persona |
| Human Wordle players lean toward exploiting | [e] Liang et al. analyzed about 83,000 human games from r/Wordle: "humans underexplore compared to near-optimal" and stay close to previous guesses | The **Bold** persona, which reflects the typical human tendency |
| Persona prompts do not automatically produce the intended behavior | [f] Licato et al.: persona effects on LLM game performance appear "only when a mediator is used to translate personas into heuristic values" | A manipulation check: log each advisor's share of non-answer guesses |
| (Optional) Information-theory guessing solves about 99% of puzzles vs about 90% for frequent-letter guessing | [g] Aladaileh et al., 2026. **Seen only through press coverage (ScienceDaily); read the paper before citing** | Extra support for Cautious |

[d] and [e] point in opposite directions: optimal play explores while humans under-explore. That disagreement is what makes the debate meaningful. The playtester's outcome then depends on which side the GM accepts, and RQ2 measures where that lands relative to human performance.

### Draft justification paragraph (for the method chapter, in your style; passes the style checker)

> Players do not share a single playstyle. Drachen et al. [a] identified four distinct player types from the gameplay data of 1,365 players. In automated playtesting, Holmgård et al. [b] showed that procedural personas with different goals expose different parts of a game during automated playtesting. In Wordle, the clearest difference between playstyles lies in how each guess is spent. A player may exploit by guessing a word that could still be the answer, or explore by guessing a word that mainly rules out letters. This trade-off is a classic problem in human decision making, where people seek more information when they have more choices left to make [c]. Optimal Wordle play leans toward exploration. For instance, the exact solution by Bertsimas and Paskov [d] answers the opening LIGHT with FERMS, which eliminates several candidates at once, instead of trying TIGHT or MIGHT. Human players, on the other hand, tend to underexplore by staying close to their previous guesses [e]. Thus, we assign one advisor to each side of this trade-off. The Bold Advisor argues for guesses that could win immediately, while the Cautious Advisor argues for guesses that narrow down the remaining words. However, the effect of a persona prompt on LLM game play depends on how the persona is translated into decisions [f]. For this reason, the share of non-answer guesses proposed by each advisor is logged to confirm that each persona behaves as intended.

### References (IEEE)

[a] A. Drachen, A. Canossa, and G. N. Yannakakis, "Player modeling using self-organization in Tomb Raider: Underworld," in *Proc. IEEE Symp. Computational Intelligence and Games (CIG)*, Milan, Italy, 2009, pp. 1–8, doi: 10.1109/CIG.2009.5286500.
[b] C. Holmgård, M. C. Green, A. Liapis, and J. Togelius, "Automated playtesting with procedural personas through MCTS with evolved heuristics," *IEEE Trans. Games*, vol. 11, no. 4, pp. 352–362, 2019. (arXiv:1802.06881)
[c] R. C. Wilson, A. Geana, J. M. White, E. A. Ludvig, and J. D. Cohen, "Humans use directed and random exploration to solve the explore–exploit dilemma," *J. Exp. Psychol.: General*, vol. 143, no. 6, pp. 2074–2081, 2014, doi: 10.1037/a0038199.
[d] D. Bertsimas and A. Paskov, "An exact solution to Wordle," *Operations Research*, vol. 73, no. 3, pp. 1384–1394, 2025, doi: 10.1287/opre.2022.0434.
[e] J. Liang, A. Kabbara, J. Liu, R. Luo, K. Kim, and M. Guerzhoy, "Semantic, orthographic, and phonological biases in humans' Wordle gameplay," in *Findings of the ACL: IJCNLP-AACL 2025*, 2025. (arXiv:2411.18634)
[f] J. Licato, S. Steinle, and B. Hollis, "Do persona-infused LLMs affect performance in a strategic reasoning game?" in *Proc. IJCNLP-AACL 2025*, 2025. (arXiv:2512.06867)
[g] T. Aladaileh, D. Stephens, M. Alqaisi, and C. Wu, "Solving Wordle using information theory," *Northeast J. Complex Systems*, vol. 8, no. 1, 2026, doi: 10.63562/2577-8439.1146. (Unverified, press coverage only.)

Note: the ", and" in the reference entries is IEEE citation format, not prose, so the style rule does not apply there.

### Sources consulted

- Bertsimas & Paskov record: https://ideas.repec.org/a/inm/oropre/v73y2025i3p1384-1394.html
- LIGHT/FERMS example: https://mitsloan.mit.edu/ideas-made-to-matter/how-algorithm-solves-wordle
- Liang et al.: https://arxiv.org/abs/2411.18634
- Wilson et al.: https://experts.arizona.edu/en/publications/humans-use-directed-and-random-exploration-to-solve-the-explore-e/
- Holmgård et al.: https://arxiv.org/abs/1802.06881
- Drachen et al.: https://www.um.edu.mt/library/oar/handle/123456789/22900
- Licato et al.: https://arxiv.org/abs/2512.06867
- Aladaileh et al. (press): https://www.sciencedaily.com/releases/2026/06/260619020508.htm

## 4. Optional third persona: Casual player

- **What it does:** plays like an everyday player, using common words and a habitual starting word.
- **Why:** human Wordle difficulty depends heavily on how familiar the answer word is. Pilot-01 solved every game and used about 0.49 fewer guesses than humans, so a human-like persona could reduce that gap.
- **Caveat:** LLMs are bad at pretending not to know a word, so this persona is less reliable than Bold or Cautious. Treat it as an experiment, not as the main design.

## 5. Consequences if adopted

1. **Code:** replace the Negative/Positive instructions in `agent/personas.py`, and rename `AgentRole.NEGATIVE` / `POSITIVE` if the roles change name. The debate graph stays the same.
2. **Experiments:** pilot-01 used the Negative/Positive configuration, so its results do not carry over. Run a new pilot before freezing the final configuration (see the roadmap's "Freeze the experimental configuration" milestone).
3. **Chapter 1:** no change needed. The background already uses generic playstyle wording ("some take risks while others play safely"), and the agent roles are deferred to the research method.
4. **Research method chapter:** describe Bold/Cautious with the `_ATCH` example and the justification paragraph in Section 3. This also answers Supervisor II's question about why the debate is set up as a competition.
