---
name: thesis-writing-style
description: The user's (Muhammad Haydar Maulana) academic writing style for their thesis, proposal, and conference paper (multi-agent LLM debate playtester, Wordle, game difficulty). Use whenever drafting, rewriting, or polishing thesis/paper prose, chapters, abstracts, or proposal text for this user, or when they ask for "my style" / "my wording".
---

# Thesis writing style

Write the way the user writes in their thesis proposal: plain, formal academic English with a steady, medium sentence rhythm. Do not use stylistic habits that make the text read as LLM-generated, because their grading rubric penalizes "any indication of LLM use".

## Hard rules

1. **Never write ", and".** This applies both to joining clauses ("X happens, and Y happens") and to the Oxford comma in lists ("chess, Pokémon, and Minecraft"). Write lists as "A, B and C" or "A to B and C".
2. **No choppy runs.** Two or three short sentences in a row read as "an ugly structure". Merge related ideas into one sentence with a linking word:
   - "while" for contrast or parallel ideas
   - "since" or "because" for reasons
   - ", which" or ", both of which" to add information
   - "as" for explanation
   - "yet" for contrast
   - "after which" for sequence
   - "rather than" for alternatives
3. **No long sentences either.** Aim for 15–28 words. Split anything over about 30 words, citations excluded. Use one main idea per sentence, plus at most one subordinate clause.
4. **No em dashes (—).** Use a comma, a relative clause, or a new sentence instead.
5. **Avoid LLM-marker vocabulary:** delve, crucial, pivotal, landscape, tapestry, seamless, leverage (as a verb), robust (unless statistical), notably, furthermore (use "Moreover"), "it is worth noting", "plays a vital role", "in the realm of". Do not write three-adjective lists.
6. **No stacked clauses or tacked-on definitions.** Do not chain "X, which …, that is, …" in one sentence, and do not use vague nouns like "game content" when a concrete one exists ("the same puzzles"). Give a definition its own plain sentence, or use "such as" with a concrete example.

## Voice

- **Sentence openers:** "However,", "Thus,", "Moreover,", "That is why", "In other words,", "In addition,", "First, … Second, … Third, …".
- **First person plural:** "We employ Wordle as the case study…", "To accommodate this gap, we establish…", "This paper develops…".
- **Passive voice is fine for process steps:** "playtesting is conducted", "the agreed action is then executed".
- **Vocabulary they use:** resource-intensive, prohibitive, indie game developers, playtester, playstyle, persona-based, human performance baselines, objective difficulty, consensus.
- **Formatting:** IEEE numeric citations at the end of the claim ("… negative reception [1], [2].") and American spelling (behavior, analyze).

## Before and after

| Avoid | Write |
|---|---|
| Designers normally measure it through playtesting, but manual playtesting needs many testers and many sessions, and it has to be repeated after each change. | Designers measure this difficulty through playtesting. However, manual playtesting is resource-intensive since it needs many testers over many sessions and has to be repeated after every significant design change. |
| A game that is too hard pushes players away. A game that is too easy quickly becomes stale. Both risk losing player retention. | A game that is too hard drives players away while one that is too easy soon becomes stale, both of which risk losing players and receiving a negative reception. |
| Difficulty data instead comes from the outcomes of complete playthroughs, which are compared with human performance baselines, that is, aggregate results of real players on the same game content. | The difficulty data comes from the outcome of each playthrough, such as the number of guesses used. These outcomes are then compared with human performance baselines, which are the average results of real players on the same puzzles. |
| LLM outputs vary between calls. As a result, the same puzzle can end differently. A playtester whose results change tells a designer little. | Since LLM outputs vary between calls, the same puzzle can end differently on different runs, which leaves a designer with little to rely on. |

## Check before delivering

Run the checker on every file you wrote or edited:

```bash
python3 .agents/skills/thesis-writing-style/check_style.py <file.md>
```

It flags ", and", em dashes, marker words, sentences over 30 words, and runs of three or more sentences under 12 words. Fix every flag, or tell the user why one was kept. Then read the paragraph once more for rhythm, since the script cannot judge flow.
