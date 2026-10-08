import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


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

        self.data = {
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
