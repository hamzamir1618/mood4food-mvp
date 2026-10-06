"""
GET /dataset: the label for the whole collection — what is in it, how each part came to be
known, and what the build changed (ui/dataset_label.py).

It is the dish panel's counterpart: that one accounts for the plate in front of you, this one
for the shelves it was picked from. Composed on the server, so the screen draws what it is
given; counted from the live graph and cached there, so it is never a figure typed by hand.
"""

import logging

from fastapi import APIRouter, HTTPException

log = logging.getLogger(__name__)
router = APIRouter(tags=["dataset"])


@router.get("/dataset")
def dataset_label():
    """What the app knows, counted. 503 when the graph can't be reached — never a guess."""
    from ui.dataset_label import label

    composed = label()
    if not composed:
        raise HTTPException(503, "The dataset couldn't be counted. Please try again.")
    return composed
