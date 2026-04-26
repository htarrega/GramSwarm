class PromptBuilder:

    CHUNK_INSTRUCTIONS = """
Read the chunk and react as this reader.

First, write a first-person internal monologue of your experience reading it: what you noticed, what you felt, what surprised or bored you, whether the voice fits your taste, and whether you'd keep reading. Be specific to the text — quote it if useful.

Then call `record_chunk_trace` with your structured metrics.
"""

    RETENTION_INSTRUCTIONS = """
You have finished the chapter. React as this reader.

First, write a first-person account of what stayed with you: what you remember, which lines stuck, what you're still wondering about, and how the tension moved through the chapter.

Then call `record_retention_trace` with your structured metrics.
"""

    @classmethod
    def build_system_prompt(cls, profile_content: str, is_final: bool = False) -> str:
        instructions = cls.RETENTION_INSTRUCTIONS if is_final else cls.CHUNK_INSTRUCTIONS
        return f"READER PROFILE:\n{profile_content}\n\n{instructions}"
