# Persona Ablation Study (neutral advisors)

Status: suggestion only. Not in the app, the pilot-02 plan or the chapters yet. Decide before the final experiment is frozen.

## 1. Why

RQ3 is descriptive. It reads the debate logs (GM retention, advisor adoption, agreement, the Cautious−Bold non-candidate gap, openers) to show how the personas take part. It cannot show that the personas change the outcome. A reviewer can still ask: "Would neutral advisors give the same results?"

Chapter 1, 1.5 currently states this as a limitation: "Its persona analysis is also descriptive, so it shows how the personas take part in the debate without proving that any persona causes the outcomes."

## 2. Proposal: one ablation condition

Keep the debate structure (GM + three advisors, same rounds and repairs). Replace Bold, Cautious and Casual with three neutral advisors that have no playstyle instruction.

| | Main condition | Ablation condition |
|---|---|---|
| Advisors | Bold, Cautious, Casual | 3 × neutral advisor |
| Puzzles × runs | same manifest | same manifest |
| Everything else | frozen config | identical |

This is not a single-agent comparison, because the debate stays the same. Only the personas are removed.

## 3. What it answers

- RQ1: is consistency different with or without personas?
- RQ2: does agreement with human difficulty (MAE, correlation, D1–D4 kappa) change?
- RQ3 becomes comparative: do adoption and non-candidate shares differ from neutral advisors?

## 4. Cost (from the P8 measurements: about 57 s and $0.007 per game off-peak)

| Design | Games | Time | Cost off-peak / peak |
|---|---|---|---|
| One neutral condition on the wide manifest (48 × 3) | 144 | ~2.3 h | ~$1 / ~$2 |
| Leave-one-out (remove each persona in turn) | 432 | ~7 h | ~$3 / ~$6 |

One neutral condition is enough for the conference paper. Leave-one-out is not needed.

## 5. Constraints

- **Same code for both conditions.** The code has changed since `pilot-02-wide` ran (P8b plus uncommitted `src/` changes). Do not compare an ablation run on new code against the existing wide data. Run the main and ablation conditions together in the final experiment, fixed in advance.
- **New persona in the registry.** It needs a `neutral` advisor `PersonaSpec` and a preset in `agent/personas.py`. This is a new configuration under the README pooling rules.
- **Chapter changes.** RQ3 is rewritten as a comparison. Then 1.3, 1.4 and 1.5 are updated, and the descriptive-only limitation is removed.
- **Supervisor approval** is needed, as with the RQ3 scope change.
