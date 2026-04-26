from gramswarm.core.prompts import PromptBuilder


class TestPromptBuilder:
    def test_chunk_prompt_includes_profile_content(self):
        prompt = PromptBuilder.build_system_prompt("I love thrillers", is_final=False)
        assert "I love thrillers" in prompt

    def test_chunk_prompt_references_chunk_tool(self):
        prompt = PromptBuilder.build_system_prompt("profile", is_final=False)
        assert "record_chunk_trace" in prompt

    def test_retention_prompt_references_retention_tool(self):
        prompt = PromptBuilder.build_system_prompt("profile", is_final=True)
        assert "record_retention_trace" in prompt

    def test_chunk_prompt_asks_for_first_person_narrative(self):
        prompt = PromptBuilder.build_system_prompt("profile", is_final=False)
        assert "first-person" in prompt

    def test_chunk_and_retention_prompts_differ(self):
        chunk = PromptBuilder.build_system_prompt("profile", is_final=False)
        retention = PromptBuilder.build_system_prompt("profile", is_final=True)
        assert chunk != retention

    def test_profile_comes_before_instructions(self):
        prompt = PromptBuilder.build_system_prompt("MY_PROFILE", is_final=False)
        profile_pos = prompt.index("MY_PROFILE")
        tool_pos = prompt.index("record_chunk_trace")
        assert profile_pos < tool_pos
