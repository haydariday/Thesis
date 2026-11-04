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

### 1.3 Persona papers (chapter 2 rationale)

Suggested on 4 November 2026 for the rationale of why personas could improve the playtester (chapter 2, Section 2.3). Both are cited from memory, not from reading the papers. Check the authors, venue, year and the claim before citing either.

| Claim used | Source to check | Side |
|---|---|---|
| LLMs conditioned on persona backstories reproduce the response distributions of human subgroups | Argyle et al., "Out of One, Many: Using Language Models to Simulate Human Samples", *Political Analysis*, 2023 | For: diverse personas could bring the aggregate closer to a human population |
| Personas in system prompts do not reliably improve performance on objective tasks | Zheng et al., "Is 'A Helpful Assistant' the Best Role for Large Language Models? A Systematic Evaluation of Social Roles in System Prompts", Findings of EMNLP, 2024 | Against: the benefit of personas is not guaranteed |

The chapter 2 evidence already in the reference list is indirect: [chen2025] (personas give more diverse solutions with higher test coverage) and [chan2024] (diverse roles matter in a debate). Neither concerns difficulty measurement, so the rationale says that no study has yet shown personas improve agreement with human difficulty.
