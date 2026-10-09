import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class CallRecord:
    """One model call attempt, including repairs and failures."""

    role: str
    attempt: int
    rejected: bool
    error_type: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    elapsed_seconds: float
    model: str | None = None


class CallRecorder:
    """Collect per-call records for a single game run."""

    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def record(
        self,
        *,
        role: str,
        attempt: int,
        rejected: bool,
        error_type: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int | None,
        elapsed_seconds: float,
        model: str | None = None,
    ) -> None:
        self.records.append(
            CallRecord(
                role=role,
                attempt=attempt,
                rejected=rejected,
                error_type=error_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                elapsed_seconds=elapsed_seconds,
                model=model,
            )
        )

    def as_dicts(self) -> list[dict]:
        return [asdict(record) for record in self.records]

    def counters(self) -> dict:
        return {
            "agent_calls": len(self.records),
            "rejected_responses": sum(
                1 for record in self.records if record.rejected
            ),
            "backend_errors": sum(
                1
                for record in self.records
                if record.error_type is not None and not record.rejected
            ),
        }

    def token_usage(self) -> dict | None:
        """Token totals, or unknown when any call lacks usage metadata."""

        if not self.records:
            return None

        with_usage = [
            record
            for record in self.records
            if (
                record.prompt_tokens is not None
                and record.completion_tokens is not None
                and record.total_tokens is not None
            )
        ]
        missing = len(self.records) - len(with_usage)

        def total(attribute: str) -> int | None:
            if missing:
                return None

            return sum(
                getattr(record, attribute) for record in with_usage
            )

        return {
            "prompt_tokens": total("prompt_tokens"),
            "completion_tokens": total("completion_tokens"),
            "total_tokens": total("total_tokens"),
            "calls": len(self.records),
            "calls_with_usage": len(with_usage),
            "calls_missing_usage": missing,
        }


class RunLog:
    """Local JSON checkpoints for a single playthrough."""

    def __init__(
        self,
        metadata: dict,
        path: Path | None = None,
    ):
        run_id = uuid4().hex

        self.path = (
            Path(path)
            if path is not None
            else Path("runs") / f"wordle-{run_id}.json"
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.data: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "metadata": metadata,
            "turns": [],
            "outcome": None,
            "error": None,
            "elapsed_seconds": None,
            "token_usage": None,
            "calls": [],
            "counters": None,
        }

        # Never overwrite a previous run.
        with self.path.open("x", encoding="utf-8") as file:
            json.dump(
                self.data,
                file,
                indent=2,
                ensure_ascii=False,
            )

    def save(self) -> None:
        """Replace this run's checkpoint atomically."""

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temp_path = Path(file.name)

                json.dump(
                    self.data,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            os.replace(temp_path, self.path)

        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
