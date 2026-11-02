"""GM and persona statistics from pilot-02 run files (plan Section 2.3).

Reads the per-turn fields that ``play.turn_statistics`` writes
(``gm_retained``, ``adopted_from``, ``advisor_agreed``,
``advisor_suggestions`` with ``is_candidate``) from completed runs only.
Everything here is descriptive except two kinds of check, which use games
as the unit because turns within a game are not independent.  The pilot's
manipulation check is the Cautious minus Bold non-candidate share with a
bootstrap over games.  The final study tests instead of resampling
(:mod:`nonparametric`): each advisor gets a non-candidate share per game,
``cautious_vs_bold`` is a Wilcoxon signed-rank test on the per-game
differences, and ``advisor_difference`` is a Friedman test across all
advisors.  In a debate without personas (C3) the Friedman test is the
baseline of the persona check: advisors with one shared instruction should
not differ.

A single-agent game (C2) has no advisors.  Its GM fields are then trivially
true (the player always "retains" its own word), so retention is reported as
None rather than 1.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .analysis import CI_HIGH_FRACTION, CI_LOW_FRACTION, _normalise_puzzle_id, _percentile
from .nonparametric import friedman, wilcoxon_signed_rank


@dataclass(frozen=True)
class Game:
    puzzle_id: str
    repetition: int
    advisors: tuple[str, ...]
    turns: tuple[dict[str, Any], ...]


def load_games(runs_dir: Path) -> list[Game]:
    """Completed runs that carry the P7 turn fields, in plan order."""

    games: list[Game] = []
    for path in sorted(runs_dir.glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        turns = run.get("turns") or []
        if run.get("status") != "completed" or not turns or "gm_retained" not in turns[0]:
            continue

        metadata = run.get("metadata") or {}
        advisors = tuple((metadata.get("personas") or {}).get("advisors") or ())
        if not advisors:
            advisors = tuple(turns[0].get("advisor_agreed") or ())
        games.append(
            Game(
                puzzle_id=_normalise_puzzle_id(str(metadata.get("puzzle_id", ""))),
                repetition=int(metadata.get("repetition") or 1),
                advisors=advisors,
                turns=tuple(turns),
            )
        )
    games.sort(key=lambda g: (int(g.puzzle_id), g.repetition))
    return games


def _share(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def non_candidate_counts(games: Sequence[Game], advisor: str) -> tuple[int, int]:
    """(non-candidate suggestions, suggestions) for one advisor after turn 1.

    Turn 1 is left out: with no feedback yet every word is a candidate.
    """

    bad = total = 0
    for game in games:
        for turn in game.turns[1:]:
            for item in turn.get("advisor_suggestions") or []:
                if item.get("advisor") == advisor and not item.get("abstained"):
                    total += 1
                    bad += not item.get("is_candidate", True)
    return bad, total


def gap_bootstrap(
    games: Sequence[Game],
    higher: str,
    lower: str,
    seed: int,
    resamples: int,
) -> dict[str, Any] | None:
    """Non-candidate share of ``higher`` minus ``lower``, CI over games."""

    def gap(sample: Sequence[Game]) -> float | None:
        bad_h, total_h = non_candidate_counts(sample, higher)
        bad_l, total_l = non_candidate_counts(sample, lower)
        if not total_h or not total_l:
            return None
        return bad_h / total_h - bad_l / total_l

    point = gap(games)
    if point is None or len(games) < 2:
        return None

    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        value = gap([games[rng.randrange(len(games))] for _ in games])
        if value is not None:
            draws.append(value)
    draws.sort()
    return {
        "difference": f"{higher} minus {lower}",
        "point": point,
        "ci_low": _percentile(draws, CI_LOW_FRACTION),
        "ci_high": _percentile(draws, CI_HIGH_FRACTION),
        "unit": "game",
        "resamples": resamples,
        "seed": seed,
    }


def game_share(game: Game, advisor: str) -> float | None:
    """One advisor's non-candidate share after turn 1 in one game, or None."""

    bad, total = non_candidate_counts([game], advisor)
    return bad / total if total else None


def paired_game_shares(
    games: Sequence[Game],
    advisors: Sequence[str],
) -> list[list[float]]:
    """Per-game shares, one value per advisor, for games where all have one."""

    rows = []
    for game in games:
        row = [game_share(game, key) for key in advisors]
        if all(value is not None for value in row):
            rows.append([value for value in row if value is not None])
    return rows


def cautious_vs_bold(games: Sequence[Game], higher: str = "cautious", lower: str = "bold") -> dict[str, Any]:
    """Wilcoxon signed-rank test on per-game ``higher`` minus ``lower`` shares."""

    rows = paired_game_shares(games, (higher, lower))
    return {
        "difference": f"{higher} minus {lower}",
        "unit": "game",
        **wilcoxon_signed_rank([a - b for a, b in rows]),
    }


def advisor_difference(games: Sequence[Game], advisors: Sequence[str]) -> dict[str, Any] | None:
    """Friedman test that all advisors share one per-game non-candidate share."""

    if len(advisors) < 2:
        return None
    rows = paired_game_shares(games, advisors)
    shares = {
        key: sum(row[j] for row in rows) / len(rows) if rows else None
        for j, key in enumerate(advisors)
    }
    return {"unit": "game", "mean_shares": shares, **friedman(rows, advisors)}


def persona_statistics(
    games: Sequence[Game],
    seed: int,
    resamples: int,
) -> dict[str, Any]:
    turns = [turn for game in games for turn in game.turns]
    later = [turn for game in games for turn in game.turns[1:]]
    advisors = list(dict.fromkeys(key for game in games for key in game.advisors))
    terminations = Counter(str(turn.get("termination")) for turn in turns)

    per_advisor = {}
    for key in advisors:
        adopted = sum(key in (turn.get("adopted_from") or []) for turn in turns)
        agreed = sum(bool((turn.get("advisor_agreed") or {}).get(key)) for turn in turns)
        bad, total = non_candidate_counts(games, key)
        abstained = sum(
            1
            for turn in turns
            for item in turn.get("advisor_suggestions") or []
            if item.get("advisor") == key and item.get("abstained")
        )
        per_advisor[key] = {
            "abstained": abstained,
            "turns": len(turns),
            "adopted": adopted,
            "adoption_rate": _share(adopted, len(turns)),
            "agreed": agreed,
            "agreement_rate": _share(agreed, len(turns)),
            "suggestions_after_turn_1": total,
            "non_candidate": bad,
            "non_candidate_share": _share(bad, total),
        }

    solo = not advisors
    retained = sum(bool(turn.get("gm_retained")) for turn in turns)
    final_bad = sum(not (turn.get("is_candidate") or {}).get("final_action", True) for turn in later)
    initial_bad = sum(not (turn.get("is_candidate") or {}).get("initial_proposal", True) for turn in later)

    return {
        "games": len(games),
        "turns": len(turns),
        "solo": solo,
        "gm_retained": None if solo else retained,
        "gm_retention_rate": None if solo else _share(retained, len(turns)),
        "termination": dict(sorted(terminations.items())),
        "mean_debate_rounds": (
            sum(int(turn.get("debate_rounds") or 0) for turn in turns) / len(turns)
            if turns
            else None
        ),
        "turns_after_turn_1": len(later),
        "final_non_candidate_share": _share(final_bad, len(later)),
        "initial_proposal_non_candidate_share": _share(initial_bad, len(later)),
        "advisors": per_advisor,
        "manipulation_check": (
            gap_bootstrap(games, "cautious", "bold", seed, resamples)
            if {"cautious", "bold"} <= set(advisors)
            else None
        ),
        "cautious_vs_bold": (
            cautious_vs_bold(games) if {"cautious", "bold"} <= set(advisors) else None
        ),
        "advisor_difference": advisor_difference(games, advisors),
    }


def opener_source(turn: dict[str, Any]) -> str:
    """Who the played word came from: the GM, the adopting advisors, or a GM revision."""

    if turn.get("gm_retained"):
        return "gm"
    adopted = turn.get("adopted_from") or []
    return "+".join(adopted) if adopted else "gm_revised"


def opener_rows(experiment: str, games: Sequence[Game]) -> list[dict[str, Any]]:
    """Counts of played words on turn 1 (all puzzles) and turn 2 (per puzzle).

    Turn 1 has no feedback, so it is pooled over puzzles; turn 2 depends on
    the puzzle's first feedback, so it is counted per puzzle.
    """

    counts: Counter[tuple[int, str, str, str]] = Counter()
    for game in games:
        for number, turn in enumerate(game.turns[:2], start=1):
            puzzle = "all" if number == 1 else game.puzzle_id
            counts[(number, puzzle, str(turn.get("final_action")), opener_source(turn))] += 1

    return [
        {
            "experiment": experiment,
            "turn": number,
            "puzzle_id": puzzle,
            "word": word,
            "source": source,
            "count": count,
        }
        for (number, puzzle, word, source), count in sorted(
            counts.items(),
            key=lambda item: (
                item[0][0],
                -1 if item[0][1] == "all" else int(item[0][1]),
                -item[1],
                item[0][2],
            ),
        )
    ]
