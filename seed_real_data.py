"""
Seed Neo4j with the real dish dataset.

Kept as the familiar entry point; the work now happens in the Phase 1 pipeline:

    python -m pipeline.build_dataset    # build data/dishes_v2.csv
    python seed_real_data.py --reset    # wipe the graph and load the v2 dataset

See pipeline/seed.py for what is written, and docs/PHASE1_DATA_DECISIONS.md for the rules.
"""

from pipeline.seed import main

if __name__ == "__main__":
    main()
