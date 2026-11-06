# Final Study: Suggestions and Cautions

Status: open notes for the final study (`final-plan.md`). Each item says what to check and before which step.

## 1. Citations to verify before they enter the thesis

### 1.1 Order and conformity papers (debate protocol justification)

These support the choice of the parallel debate protocol (`final-plan.md` Section 2.0): order effects and conformity in LLM debates. They came from web-search summaries on 2 November 2026, not from reading the papers. Read the relevant sections and check the claims, authors, venue and year before citing any of them.

| Claim used | Source to check |
|---|---|
| Speaking order had a significant effect; all six orders of three agents were tested, then one order was fixed | Revealing Political Bias in LLMs through Structured Multi-Agent Debate, [arXiv 2506.11825](https://arxiv.org/pdf/2506.11825) |
| Placing the most reliable agent last raises accuracy ("Truth Last", MADC) | Summary only: [emergentmind 2511.11040](https://api.emergentmind.com/papers/2511.11040). Find the original paper first. |
| Strong order effects and conformity under round-robin speaking | Deliberative Dynamics and Value Alignment in LLM Debates, [arXiv 2510.10002](https://arxiv.org/html/2510.10002v1) |
| Neutral agents align with the majority (conformity) | An Empirical Study of Group Conformity in Multi-Agent Systems, [arXiv 2506.01332](https://arxiv.org/html/2506.01332v1) |
| Debate order as a controllable factor | Can LLM Agents Really Debate? A Controlled Study, [arXiv 2511.07784](https://arxiv.org/pdf/2511.07784) |
| Voting and consensus behave differently in multi-agent debate | Voting or Consensus? Decision-Making in Multi-Agent Debate, [arXiv 2502.19130](https://arxiv.org/pdf/2502.19130) |

Already in the reference list of the progress report, so no new check is needed: [16] Liang et al. (managing agent, adaptive stop), [21] Du et al. (agents see each other's answers from the previous round), [22] Baltaji et al. (persona inconstancy, conformity).

Do not claim that the parallel protocol is best in general. The claim is that it meets the requirements of this study (`final-plan.md` Section 2.0).

### 1.2 Sample-size and statistics references

Cited from memory in `final-plan.md` Sections 5 and 7. Check them before they enter the thesis.

| Reference | Used for |
|---|---|
| Walter, Eliasziw and Donner (*Statistics in Medicine*, 1998) | More subjects improve a reliability study more than more repeats |
| Bonett and Wright (*Psychometrika*, 2000) | Sample sizes for correlations |
| Koo and Li (*Journal of Chiropractic Medicine*, 2016) | At least 30 subjects for an ICC study |
| Thompson (1987) | Margin of the 7-bin shares at 10 runs |
| Shrout and Fleiss (1979) | ICC(1,1), ICC(1,k) and their F-distribution intervals |

### 1.3 Persona prompting and performance (chapter 2 rationale, discussion)

Found by web search on 4 November 2026, not yet read in full. Read the relevant sections and verify the claims, authors, venue and year before citing.

| Claim used | Source to check | Side |
|---|---|---|
| Role-play prompting acts as an implicit CoT trigger and improves zero-shot reasoning across 12 benchmarks | Kong et al., "Better Zero-Shot Reasoning with Role-Play Prompting", NAACL 2024, [arXiv 2308.07702](https://arxiv.org/abs/2308.07702) | For: task-relevant personas can help reasoning |
| Personas and social roles in system prompts do not reliably improve performance on objective tasks over a no-persona control | Zheng et al., "When 'A Helpful Assistant' Is Not Really Helpful: Personas in System Prompts Do Not Improve Performances of Large Language Models", Findings of EMNLP 2024, [arXiv 2311.10054](https://arxiv.org/abs/2311.10054) | Against: personas do not guarantee higher accuracy |
| Textual personas change strategic behavior in a game without uniformly improving win rate | Licato and Steinle, "Do Persona-Infused LLMs Affect Performance in a Strategic Reasoning Game?", IJCNLP-AACL 2025, [arXiv 2512.06867](https://arxiv.org/abs/2512.06867) | Both: personas alter play behavior without necessarily improving outcomes |

The chapter 2 evidence already in the reference list is indirect: [chen2025] (personas give more diverse solutions with higher test coverage) and [chan2024] (diverse roles matter in a debate). Neither concerns difficulty measurement, so the rationale says that no study has yet shown personas improve agreement with human difficulty.

### 1.4 Simulating diverse human populations (RQ2 persona-diversity argument)

Found by web search on 4 November 2026, not yet read in full.

| Claim used | Source to check | Side |
|---|---|---|
| LLMs conditioned on persona backstories reproduce the response distributions of human subgroups ("silicon sampling") | Argyle et al., "Out of One, Many: Using Language Models to Simulate Human Samples", *Political Analysis* 31(3), 2023, [arXiv 2209.06899](https://arxiv.org/abs/2209.06899) | For: diverse personas could bring the aggregate closer to a human population |
| LLMs can replicate aggregate human-subject trends across multiple simulated participants ("Turing Experiments"), though with hyper-accuracy distortions | Aher, Arriaga and Kalai, "Using Large Language Models to Simulate Multiple Humans and Replicate Human Subject Studies", ICML 2023 (PMLR 202), [arXiv 2208.10264](https://arxiv.org/abs/2208.10264) | For (with caveat): supports population simulation while noting reduced human variance |
| Persona-prompted LLMs flatten group differences and homogenize within-group variance | Wang, Morgenstern and Dickerson, "Large Language Models Cannot Replace Human Participants Because They Cannot Portray Identity Groups", *Nature Machine Intelligence* / 2024, [arXiv 2402.01908](https://arxiv.org/abs/2402.01908) | Against: explains why persona diversity may not match real human spread |

### 1.5 Where debate gains come from: debate vs. voting and self-consistency (discussion of the debate effect)

Found by web search on 4 November 2026, not yet read in full. Supports the discussion of why C3 improved consistency (RQ1) without improving accuracy (RQ2), and addresses why C2 is a single call rather than a self-consistency baseline.

| Claim used | Source to check |
|---|---|
| Sampling multiple reasoning paths from one model and taking a majority vote substantially improves consistency and accuracy | Wang et al., "Self-Consistency Improves Chain of Thought Reasoning in Language Models", ICLR 2023, [arXiv 2203.11171](https://arxiv.org/abs/2203.11171) |
| Multi-agent debate often fails to beat simpler ensembling or self-consistency once compute is matched | Smit et al., "Should We Be Going MAD? A Look at Multi-Agent Debate Strategies for LLMs", ICML 2024, [arXiv 2311.17371](https://arxiv.org/abs/2311.17371) (already cited) |
| Homogeneous-model multi-agent debate rarely outperforms single-agent CoT and self-consistency baselines | Zhang et al., "Stop Overvaluing Multi-Agent Debate — We Must Rethink Evaluation and Embrace Model Heterogeneity", 2025, [arXiv 2502.08788](https://arxiv.org/abs/2502.08788) |
| Most gains attributed to multi-agent debate come from majority voting rather than multi-round deliberation | Choi et al., "Debate or Vote: Which Yields Better Decisions in Multi-Agent Large Language Models?", Findings of NeurIPS / 2025, [arXiv 2508.17536](https://arxiv.org/abs/2508.17536) (verify exact ID and venue before citing) |

### 1.6 Run-to-run variability of LLMs (RQ1 justification)

Found by web search on 4 November 2026, not yet read in full. Supports evaluating repeated runs per puzzle rather than single runs as in Xiao and Yang.

| Claim used | Source to check |
|---|---|
| Even under deterministic settings, hosted LLM APIs show run-to-run output and accuracy variance across repeated runs | Atil et al., "Non-Determinism of 'Deterministic' LLM Settings", 2024, [arXiv 2408.04667](https://arxiv.org/abs/2408.04667) |

### 1.7 Reasoning mode and overthinking (C3's long replies, non-reasoning configuration)

Found by web search on 4 November 2026, not yet read in full. Supports the discussion of long reasoning traces in neutral agents and the trade-off between thinking and non-thinking configurations.

| Claim used | Source to check |
|---|---|
| Reasoning models generate redundant reasoning chains ("overthinking") on simple or constrained tasks, spending many extra tokens without accuracy gains | Chen et al., "Do NOT Think That Much for 2+3=? On the Overthinking of o1-Like LLMs", ICML 2025 / 2024, [arXiv 2412.21187](https://arxiv.org/abs/2412.21187) |

### 1.8 LLM playtesting and difficulty, 2024–2026 (chapter 2 currency and novelty check)

Found by web search on 4 November 2026, not yet read in full. Confirms that no prior study combines persona-based multi-agent debate with human difficulty validation on Wordle.

| Claim used | Source to check |
|---|---|
| Single-agent LLMs correlate with human difficulty on Wordle and Slay the Spire without matching absolute human skill | Xiao and Yang, "LLMs May Not Be Human-Level Players, But They Can Be Testers: Measuring Game Difficulty with LLM Agents", 2024, [arXiv 2410.02829](https://arxiv.org/abs/2410.02829) (already cited) |
| Persona-distilled LLM virtual playtester simulates diverse subjective player feedback for board games (no multi-agent debate or Wordle difficulty scoring) | Li et al., "MeepleLM: A Virtual Playtester Simulating Diverse Subjective Experiences", ACL 2026 / Jan 2026, [arXiv 2601.07251](https://arxiv.org/abs/2601.07251) |

### 1.9 Agents playing easier than humans (the negative signed bias)

Found by web search on 4 November 2026, not yet read in full. Supports explaining why LLM agents solve Wordle in fewer guesses on average than human players (full vocabulary access vs. human memory limits).

| Claim used | Source to check |
|---|---|
| Aligning AI play with human behavior across skill levels differs from optimizing for strongest play | Tang et al., "Maia-2: A Unified Model for Human-AI Alignment in Chess", NeurIPS 2024, [arXiv 2409.20553](https://arxiv.org/abs/2409.20553) |

