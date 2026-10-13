import argparse
import hashlib
import os
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv

from ..agent.backend import (
    ChatCompletionsBackend,
    ModelBackend,
    ResponsesBackend,
    ScriptedBackend,
)
from ..agent.persona_args import add_persona_arguments, lineup_from_args
from ..agent.providers import (
    PROVIDERS,
    THINKING_MODES,
    default_api_key_env,
    endpoint_error,
    extra_body,
    request_options_error,
    settings_error,
)
from ..games.wordle.bridge import WordleBridge
from ..games.wordle.dataset import load_allowed_guesses, load_puzzle
from ..games.wordle.engine import WordleGame
from ..orchestra.debate import create_debate_graph
from ..orchestra.debate_context import new_debate_state
from ..orchestra.flow.sequential import recursion_limit
from ..play import play_wordle_game
from ..run_log import RunLog


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]

    load_dotenv(
        dotenv_path=project_root / ".env",
        override=False,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        help="Exact local Ollama model ID; omit for a scripted test.",
    )
    parser.add_argument(
        "--base-url",
        help="Ollama's OpenAI-compatible endpoint.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Sampling temperature for the model call.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Print the response incrementally.",
    )
    parser.add_argument(
        "--backend",
        choices=["scripted", "ollama", *PROVIDERS],
        default="scripted",
        help="Which backend to use.",
    )
    parser.add_argument(
        "--protocol",
        choices=["chat", "responses"],
        default="chat",
        help="OpenAI-compatible protocol for the model backend.",
    )
    parser.add_argument(
        "--api-key-env",
        help="Key variable (default: OPENCODE_API_KEY for zen, DEEPSEEK_API_KEY for deepseek).",
    )
    parser.add_argument(
        "--thinking",
        choices=THINKING_MODES,
        help="DeepSeek reasoning mode; temperature only applies when disabled.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Reply cap per call; a cut-off reply gets the repair re-ask.",
    )
    parser.add_argument(
        "--json-mode",
        action="store_true",
        help="Ask the provider for a well-formed JSON object (response_format).",
    )
    parser.add_argument(
        "--debate",
        action="store_true",
        help="Run the complete agent debate instead of one advisor.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Maximum advisor/review cycles.",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play a complete Wordle puzzle using debate.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        help="Path to the puzzle JSON.",
    )
    parser.add_argument(
        "--puzzle-id",
        help="Exact puzzle key in the dataset.",
    )
    parser.add_argument(
        "--guess-list",
        type=Path,
        help="Path to the allowed-guess vocabulary.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=90.0,
        help="SDK request timeout in seconds.",
    )
    parser.add_argument(
        "--api-retries",
        type=int,
        choices=[0, 1, 2],
        default=0,
        help="Maximum SDK retries for eligible request failures.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="New JSON output path; otherwise generate one under runs/.",
    )
    parser.add_argument(
        "--max-repairs",
        type=int,
        choices=[0, 1, 2],
        default=1,
        help="Maximum corrective responses per agent decision.",
    )

    add_persona_arguments(parser, default_preset="pilot-02")

    args = parser.parse_args()
    # Fail on bad persona flags before any API-key prompt.
    lineup_from_args(parser, args)

    if args.play:
        if args.debate:
            parser.error(
                "Use --play alone; it already includes debate."
            )

        if args.backend == "scripted":
            parser.error(
                "The current scripted fixture cannot play a full game."
            )

        if (
            args.dataset is None
            or args.puzzle_id is None
            or args.guess_list is None
        ):
            parser.error(
                "--play requires --dataset, --puzzle-id, and --guess-list"
            )

        if not 1 <= args.max_rounds <= 10:
            parser.error("--max-rounds must be between 1 and 10.")

    backend: ModelBackend

    if args.backend == "scripted":
        if any(
            value is not None
            for value in (
                args.model,
                args.base_url,
                args.temperature,
                args.thinking,
                args.max_tokens,
            )
        ):
            parser.error(
                "Select a model backend when supplying "
                "model connection settings."
            )

        backend = ScriptedBackend(
            response=(
                '{"action":"CRANE",'
                '"reason":"Scripted response for backend testing.",'
                '"stop":false}'
            )
        )

        print("Backend: scripted test, no LLM")

    else:
        if not args.model or not args.base_url:
            parser.error(
                f"--backend {args.backend} requires --model and --base-url"
            )

        error = settings_error(
            args.backend, args.protocol, args.temperature, args.thinking
        ) or endpoint_error(args.backend, args.base_url) or request_options_error(
            args.protocol, args.max_tokens, args.json_mode
        )
        if error is not None:
            parser.error(error)

        if args.stream and args.protocol == "responses":
            parser.error(
                "--stream is not supported with --protocol responses"
            )

        if args.backend in PROVIDERS:
            key_env = args.api_key_env or default_api_key_env(args.backend)
            api_key = os.environ.get(key_env or "", "").strip()

            if not api_key:
                api_key = getpass(
                    f"{key_env} (input hidden): "
                ).strip()

            if not api_key:
                parser.error("The API key cannot be empty.")

        else:
            # Local Ollama's SDK placeholder, not a real secret.
            api_key = "ollama"

        if args.protocol == "responses":
            backend = ResponsesBackend(
                model=args.model,
                base_url=args.base_url,
                api_key=api_key,
                temperature=args.temperature,
                request_timeout=args.request_timeout,
                api_retries=args.api_retries,
            )
        else:
            backend = ChatCompletionsBackend(
                model=args.model,
                base_url=args.base_url,
                temperature=args.temperature,
                api_key=api_key,
                request_timeout=args.request_timeout,
                api_retries=args.api_retries,
                extra_body=extra_body(args.thinking),
                max_tokens=args.max_tokens,
                json_mode=args.json_mode,
            )

        print(
            f"Backend: {args.backend} | model: {args.model}"
        )

    lineup = lineup_from_args(parser, args, backend)
    if args.play:
        puzzle = load_puzzle(
            path=args.dataset,
            puzzle_id=args.puzzle_id,
        )

        allowed_guesses = load_allowed_guesses(
            args.guess_list
        )

        game = WordleGame(
            puzzle,
            allowed_guesses=allowed_guesses,
        )

        bridge = WordleBridge(game)

        run = RunLog(
            metadata={
                "backend": args.backend,
                "protocol": args.protocol,
                "model_requested": args.model,
                "base_url": args.base_url,
                "temperature": args.temperature,
                "thinking": args.thinking,
                "max_tokens": args.max_tokens,
                "json_mode": args.json_mode,
                "stream": args.stream,
                "max_rounds": args.max_rounds,
                "max_repairs": args.max_repairs,
                "request_timeout": args.request_timeout,
                "api_retries": args.api_retries,
                "puzzle_id": puzzle.puzzle_id,
                "target_answer": puzzle.answer,
                "guess_policy": game.observation()["guess_policy"],
                "vocabulary_size": len(allowed_guesses),
                "dataset_sha256": hashlib.sha256(
                    args.dataset.read_bytes()
                ).hexdigest(),
                "guess_list_sha256": hashlib.sha256(
                    args.guess_list.read_bytes()
                ).hexdigest(),
                "agent_instructions": lineup.instructions(),
                "personas": lineup.config(),
            },
            path=args.output,
        )

        play_wordle_game(
            game=game,
            bridge=bridge,
            lineup=lineup,
            run=run,
            max_rounds=args.max_rounds,
            max_repairs=args.max_repairs,
            stream=args.stream,
            echo=True,
        )

        print("\nGame finished")
        print(f"Won: {game.won}")
        print(f"Guesses used: {len(game.observation()['history'])}")

        return

    if args.debate:
        if args.backend == "scripted":
            parser.error(
                "The current scripted backend is a single-response "
                "fixture, not a complete debate simulator. "
                "Use a model backend for this test."
            )

        if not 1 <= args.max_rounds <= 10:
            parser.error("--max-rounds must be between 1 and 10.")

        graph = create_debate_graph(
            lineup,
            stream=args.stream,
        )
        debate_state = new_debate_state(
            (
                "A new Wordle game has started. "
                "No guesses have been submitted. "
                "Six attempts remain. "
                "Propose uppercase five-letter guesses. "
                "No target word or feedback is available. "
                "Do not invent feedback."
            ),
            args.max_rounds,
        )
        result = graph.invoke(
            debate_state,
            {
                "recursion_limit": recursion_limit(
                    args.max_rounds, len(lineup.advisors)
                ),
            },
        )

        print("\nDebate finished")
        print(f"Final action: {result['final_action']}")
        print(f"Completed rounds: {result['round']}")
        print(f"Termination: {result['termination']}")

        return
    negative = lineup.advisors[0]

    context = (
        "A new Wordle game has started. "
        "No guesses have been submitted. "
        "Six attempts remain. "
        "The GM proposes APPLE. "
        "Challenge the proposal and suggest an alternative. "
        "Give a concise justification without inventing feedback."
    )

    print(f"\nAgent: {negative.name}")

    if args.stream:
        def display_chunk(chunk: str) -> None:
            print(chunk, end="", flush=True)

        decision = negative.decide(
            context,
            on_chunk=display_chunk,
        )
        print()
    else:
        decision = negative.decide(context)

    print("\nValidated decision:")
    print(decision.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
