"""Shared fakes: a scripted LLM (no Gemini key needed) and a switch that routes settings.get_llm() to it."""
from types import SimpleNamespace

import pytest

from config.settings import Settings


class FakeLLM:
    """responder(prompt) -> text. Supports the three call styles the agents use: ainvoke, invoke and astream."""

    def __init__(self, responder, chunks=("Answer ", "text [Article 5].")):
        self.responder, self.chunks, self.prompts = responder, chunks, []

    def _msg(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(content=self.responder(prompt))

    async def ainvoke(self, prompt):
        return self._msg(prompt)

    def invoke(self, prompt):
        return self._msg(prompt)

    async def astream(self, prompt):
        self.prompts.append(prompt)
        for c in self.chunks:
            yield SimpleNamespace(content=c)


@pytest.fixture
def fake_llm(monkeypatch):
    """Returns a holder: set holder.responder = lambda prompt: '...'; holder.llm is the FakeLLM in use."""
    holder = SimpleNamespace(responder=lambda p: "{}")
    holder.llm = FakeLLM(lambda p: holder.responder(p))
    monkeypatch.setattr(Settings, "get_llm", lambda self, streaming=False: holder.llm)
    return holder
