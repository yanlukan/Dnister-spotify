# src/language/text_check.py
import logging

import fasttext
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load the glotlid model."""
    global _model
    if _model is None:
        model_path = hf_hub_download(
            repo_id="cis-lmu/glotlid",
            filename="model.bin",
        )
        _model = fasttext.load_model(model_path)
        logger.info("glotlid model loaded")
    return _model


def check_text_language(text: str) -> dict:
    """Detect language of text using glotlid.

    Returns {"language": "ukr"|"rus"|..., "confidence": 0.0-1.0}
    """
    if not text or len(text.strip()) < 2:
        return {"language": "unknown", "confidence": 0.0}

    model = _get_model()
    predictions = model.predict(text.replace("\n", " "), k=1)
    label = predictions[0][0].replace("__label__", "").split("_")[0]
    confidence = float(predictions[1][0])

    return {"language": label, "confidence": confidence}
