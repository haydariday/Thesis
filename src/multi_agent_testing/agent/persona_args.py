"""Shared command-line flags for choosing the debate line-up."""

import argparse

from .backend import ModelBackend
from .personas import PERSONAS, PRESETS, Lineup, create_lineup
from .persona_spec import Slot


def add_persona_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_preset: str | None = None,
) -> None:
    """Add ``--persona-preset``, ``--advisors`` and ``--gm``.

    Without ``default_preset`` the caller must choose a line-up explicitly.
    """

    advisors = [key for key, spec in PERSONAS.items() if spec.slot == Slot.ADVISOR]
    gms = [key for key, spec in PERSONAS.items() if spec.slot == Slot.GM]

    group = parser.add_mutually_exclusive_group(required=default_preset is None)
    group.add_argument(
        "--persona-preset",
        choices=list(PRESETS),
        default=default_preset,
        help="Named line-up from the persona registry.",
    )
    group.add_argument(
        "--advisors",
        help=f"Comma-separated advisor keys in speaking order ({', '.join(advisors)}).",
    )
    parser.add_argument(
        "--gm",
        choices=gms,
        help="GM persona; overrides the preset's GM (default with --advisors: neutral_gm).",
    )


def lineup_from_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    backend: ModelBackend | None = None,
) -> Lineup:
    """Build the line-up chosen on the command line, or exit with a usage error."""

    advisors = None
    preset = args.persona_preset
    if args.advisors is not None:
        advisors = [key.strip() for key in args.advisors.split(",") if key.strip()]
        preset = None

    try:
        return create_lineup(backend, preset=preset, gm=args.gm, advisors=advisors)
    except ValueError as error:
        parser.error(str(error))
