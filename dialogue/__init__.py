"""
The conversational layer (Phase 5): a turn contract over the recommendation pipeline
that asks a question only when the answer would change the pick, and refines a
recommendation against the candidates it already holds. No LLM calls beyond the first
message's intent extraction. See docs/CONVERSATION.md.
"""
