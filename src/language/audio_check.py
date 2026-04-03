# src/language/audio_check.py
import logging
import tempfile

import requests
import torch
import torchaudio
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

logger = logging.getLogger(__name__)

_model = None
_extractor = None
_MODEL_ID = "facebook/mms-lid-4017"


def _load_model():
    global _model, _extractor
    if _model is None:
        logger.info(f"Loading {_MODEL_ID}...")
        _extractor = AutoFeatureExtractor.from_pretrained(_MODEL_ID)
        _model = AutoModelForAudioClassification.from_pretrained(_MODEL_ID)
        _model.eval()
        logger.info("MMS-LID model loaded")
    return _model, _extractor


def _classify_audio(audio_url: str) -> dict[str, float]:
    """Download audio and classify language. Returns {lang_code: probability}."""
    model, extractor = _load_model()

    resp = requests.get(audio_url, timeout=15)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as f:
        f.write(resp.content)
        f.flush()
        waveform, sample_rate = torchaudio.load(f.name)

    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        waveform = resampler(waveform)

    waveform = waveform[0][:16000 * 30]

    inputs = extractor(waveform.numpy(), sampling_rate=16000, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.softmax(outputs.logits, dim=-1)[0]
    id2label = model.config.id2label

    top_indices = torch.topk(probs, k=5).indices
    results = {}
    for idx in top_indices:
        label = id2label[idx.item()]
        results[label] = float(probs[idx])

    return results


def check_audio_language(preview_url: str | None) -> dict:
    """Check what language a song is sung in.

    Returns {"language": "ukr"|"rus"|..., "confidence": 0.0-1.0}
    """
    if not preview_url:
        return {"language": "unknown", "confidence": 0.0}

    try:
        scores = _classify_audio(preview_url)
        top_lang = max(scores, key=scores.get)
        return {"language": top_lang, "confidence": scores[top_lang]}
    except Exception as e:
        logger.warning(f"Audio language check failed: {e}")
        return {"language": "unknown", "confidence": 0.0}
