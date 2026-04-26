import pathlib
import json
from datetime import datetime
from typing import Optional, Union
from ..core.models import ChunkTrace, RetentionTrace


class RunManager:

    def __init__(self, base_dir: str = "runs", chapter_name: Optional[str] = None):
        self.base_dir = pathlib.Path(base_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{timestamp}_{chapter_name}" if chapter_name else timestamp
        self.run_dir = self.base_dir / folder_name
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def get_reader_dir(self, cluster: str, reader_name: str) -> pathlib.Path:
        reader_dir = self.run_dir / cluster / reader_name
        reader_dir.mkdir(parents=True, exist_ok=True)
        return reader_dir

    def save_structured(self, cluster: str, reader_name: str, structured: ChunkTrace, chunk_index: int, content: str):
        reader_dir = self.get_reader_dir(cluster, reader_name)
        data = structured.model_dump()
        data["raw_content"] = content
        (reader_dir / f"chunk_{chunk_index:03d}.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def save_retention(self, cluster: str, reader_name: str, structured: RetentionTrace, content: str):
        reader_dir = self.get_reader_dir(cluster, reader_name)
        data = structured.model_dump()
        data["raw_content"] = content
        (reader_dir / "retention.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def save_meta(self, meta: dict):
        (self.run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def __str__(self):
        return str(self.run_dir)
