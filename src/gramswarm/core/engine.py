import pathlib
from typing import List
from loguru import logger
from .models import TraceResponse, ChunkTrace, RetentionTrace
from .base import LLMProvider, Message
from .reader import ReaderProfile
from .prompts import PromptBuilder
from ..services.io import RunManager


class SimulationEngine:

    def __init__(self, provider: LLMProvider, run_manager: RunManager, chunk_size: int = 500):
        self.provider = provider
        self.run_manager = run_manager
        self.chunk_size = chunk_size

    def _chunk_text(self, text: str) -> List[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_word_count = 0

        for para in paragraphs:
            para_len = len(para.split())
            if current_word_count + para_len > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_word_count = 0
            current_chunk.append(para)
            current_word_count += para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        return chunks

    def simulate_reader(self, reader: ReaderProfile, chunks: List[str]) -> bool:
        messages: List[Message] = []
        system_prompt = PromptBuilder.build_system_prompt(reader.content, is_final=False)

        for i, chunk in enumerate(chunks):
            messages.append({"role": "user", "content": f"Chunk {i+1}:\n\n{chunk}"})
            try:
                response: TraceResponse = self.provider.generate_trace(
                    system_prompt=system_prompt,
                    messages=messages,
                )
                self.run_manager.save_structured(reader.cluster, reader.name, response.structured_data, i, response.content)
                messages.append({"role": "assistant", "content": response.content})
            except Exception as e:
                logger.error(f"Error processing reader {reader.name} at chunk {i}: {e}")
                return False

        messages.append({
            "role": "user",
            "content": "Chapter complete. Provide your end-of-chapter retention trace now.",
        })
        system_prompt_final = PromptBuilder.build_system_prompt(reader.content, is_final=True)
        try:
            final_response: TraceResponse = self.provider.generate_trace(
                system_prompt=system_prompt_final,
                messages=messages,
                is_final=True,
            )
            self.run_manager.save_retention(reader.cluster, reader.name, final_response.structured_data, final_response.content)
        except Exception as e:
            logger.error(f"Error generating final trace for {reader.name}: {e}")
            return False

        return True

    def run(self, chapter_path: pathlib.Path, readers: List[ReaderProfile]):
        text = chapter_path.read_text(encoding="utf-8")
        chunks = self._chunk_text(text)

        results = []
        for reader in readers:
            logger.info(f"Simulating reader: {reader.name} [{reader.cluster}]...")
            results.append(self.simulate_reader(reader, chunks))

        if not any(results):
            raise RuntimeError(f"All {len(readers)} readers failed — check model name and API key")
