"""
A conversation's state, kept with the session in Redis for as long as the session's
other contracts.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field

from tier_1.contracts import session_store

CONTRACT = "conversation"
LOWEST = ("ceiling", "price_below", "calories_below", "spice_below")  # tighter means lower
HIGHEST = ("calories_above", "spice_above", "health_above")  # tighter means higher


class Adjustments(BaseModel):
    """
    What the conversation has added to the query. They are applied to the candidates
    Tier 1 already returned, so answering a question or refining needs no new query.

    ceiling      a budget the user gave: a filter, and the budget term's limit
    price_below  "cheaper than this": a filter only
    """

    ceiling: Optional[float] = None
    price_below: Optional[float] = None
    party_size: Optional[int] = None
    craved: dict[str, float] = Field(default_factory=dict)
    category: Optional[str] = None
    exclude_categories: list[str] = Field(default_factory=list)
    goal: Optional[str] = None
    calories_below: Optional[float] = None
    calories_above: Optional[float] = None
    spice_above: Optional[float] = None
    spice_below: Optional[float] = None
    health_above: Optional[float] = None

    def merged(self, change: dict) -> "Adjustments":
        """These adjustments plus a change. Limits only ever tighten."""
        data = self.model_dump()
        for key, value in change.items():
            if value is None:
                continue
            if key in LOWEST:
                data[key] = value if data[key] is None else min(data[key], value)
            elif key in HIGHEST:
                data[key] = value if data[key] is None else max(data[key], value)
            elif key == "exclude_categories":
                data[key] = sorted({*data[key], *value})
            elif key == "craved":
                data[key] = {**data[key], **value}
            else:
                data[key] = value
        return Adjustments(**data)


class Question(BaseModel):
    slot: str  # "taste", "cuisine", "budget" or "party"
    text: str
    why: str = ""
    chips: dict[str, dict]  # value -> {"label": ..., "adjust": {...}}


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    turn: int = 0
    asked: list[str] = Field(default_factory=list)
    pending: Optional[Question] = None
    adjustments: Adjustments = Field(default_factory=Adjustments)
    stated: dict[str, dict] = Field(default_factory=dict)  # slot -> the answer chosen
    closed: bool = False  # no more questions: the limit was reached, or "just pick for me"


def load(session_id: str) -> Conversation | None:
    raw = session_store.load_contract(session_id, CONTRACT)
    return Conversation(**raw) if raw else None


def save(session_id: str, conversation: Conversation) -> None:
    session_store.save_contract(session_id, CONTRACT, conversation)
