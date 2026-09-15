"""
The conversation endpoint (Phase 5). The turn contract is in docs/CONVERSATION.md.
"""

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, model_validator

from api.rate_limit import limiter
from dialogue.critiques import CRITIQUES

router = APIRouter(tags=["conversation"])


class Answer(BaseModel):
    question: str = Field(max_length=40)
    value: str = Field(max_length=60)


class ChatTurn(BaseModel):
    """One turn: exactly one of text, answer, critique or skip."""

    text: Optional[str] = Field(default=None, min_length=1, max_length=500)
    answer: Optional[Answer] = None
    critique: Optional[str] = None
    skip: bool = False

    @model_validator(mode="after")
    def exactly_one(self) -> "ChatTurn":
        given = [
            self.text is not None,
            self.answer is not None,
            self.critique is not None,
            self.skip,
        ]
        if sum(given) != 1:
            raise ValueError("send exactly one of: text, answer, critique, skip")
        if self.critique is not None and self.critique not in CRITIQUES:
            raise ValueError(f"critique must be one of {list(CRITIQUES)}")
        return self


@router.post("/chat")
@limiter.limit("30/minute")
def chat(request: Request, turn: ChatTurn):
    """
    One conversation turn. New text starts a request (and is the only turn that runs
    the intent extractor); an answer, a critique or a skip works on the candidates that
    request found. Replies with a question to answer, or a recommendation to refine.
    """
    from dialogue.manager import handle

    return handle(request, turn)
