import logging
from pathlib import Path

from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

_clip_model = None
_clip_processor = None


def _get_clip_model():
    global _clip_model, _clip_processor
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor

        log.info("loading CLIP model...")
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        log.info("CLIP model loaded ✓")
    return _clip_model, _clip_processor


def classify_dish(image_path: str, candidate_labels: list[str]) -> str:
    """
    Runs zero-shot classification against a list of dish/ingredient names.
    Returns the top classification result.
    """
    path = Path(image_path)
    if not path.exists():
        log.warning("image file not found: %s", image_path)
        return ""

    if not candidate_labels:
        log.warning("no candidate labels provided")
        return ""

    import torch

    model, processor = _get_clip_model()
    image = Image.open(path)

    # Prepend "a photo of " to labels for better CLIP performance
    text_inputs = [f"a photo of {label}" for label in candidate_labels]

    inputs = processor(text=text_inputs, images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1)

    best_idx = probs.argmax().item()
    best_label = candidate_labels[best_idx]

    log.info(
        "📷 vision | classified %s as '%s' (prob: %.2f)",
        path.name,
        best_label,
        probs[0, best_idx].item(),
    )
    return best_label
