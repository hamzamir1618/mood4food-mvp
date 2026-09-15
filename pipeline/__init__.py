"""
Phase 1 data pipeline: builds the v2 dish dataset from the handoff CSV and the
data-sourcing project, then seeds Neo4j from it.

Every output lives under data/ and data_review/, which are git-ignored so the
dataset stays out of the public repository (see ATTRIBUTIONS.md).
"""
