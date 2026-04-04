import uuid
from datetime import datetime

# ── Inline city-keyword map (no external imports) ─────────────────────────────
_CITY_KEYWORDS = {
    'new delhi': 'delhi', 'new york': 'new york',
    'calcutta': 'kolkata', 'bombay': 'mumbai', 'madras': 'chennai',
    'mumbai': 'mumbai', 'delhi': 'delhi', 'hyderabad': 'hyderabad',
    'karachi': 'karachi', 'dhaka': 'dhaka', 'nairobi': 'nairobi',
    'dubai': 'dubai', 'singapore': 'singapore', 'london': 'london',
    'shanghai': 'shanghai', 'cairo': 'cairo', 'lahore': 'lahore',
    'islamabad': 'islamabad', 'kolkata': 'kolkata', 'chennai': 'chennai',
    'bangkok': 'bangkok', 'jakarta': 'jakarta', 'tokyo': 'tokyo',
    'beijing': 'beijing', 'moscow': 'moscow', 'istanbul': 'istanbul',
    'lagos': 'lagos', 'paris': 'paris', 'nyc': 'new york',
    'uae': 'dubai', 'uk': 'london', 'egypt': 'cairo',
    'pakistan': 'karachi', 'india': 'delhi', 'kenya': 'nairobi',
    'bangladesh': 'dhaka', 'indonesia': 'jakarta', 'japan': 'tokyo',
    'china': 'beijing', 'russia': 'moscow', 'nigeria': 'lagos',
    'france': 'paris', 'turkey': 'istanbul',
}


def _extract_location_from_text(text: str) -> str | None:
    """Scan text for a known city keyword. Returns matched city or None."""
    if not text:
        return None
    lower = text.lower()
    for keyword in sorted(_CITY_KEYWORDS, key=len, reverse=True):
        if keyword in lower:
            return _CITY_KEYWORDS[keyword]
    return None


def create_record(
    source,
    commodity,
    location,
    text,
    price=None,
    signal_type="behavior",
    confidence=0.5
):
    valid_sources = ["telegram", "olx", "news", "shipping", "customs", "trends", "rss", "commodity_api"]
    valid_signal_types = ["behavior", "price", "logistics", "news"]

    if source not in valid_sources:
        raise Exception(f"Invalid source '{source}'. Must be one of: {valid_sources}")
    
    if signal_type not in valid_signal_types:
        raise Exception(f"Invalid signal_type '{signal_type}'. Must be one of: {valid_signal_types}")
        
    if not (0 <= confidence <= 1):
        raise Exception(f"Confidence must be between 0 and 1. Got: {confidence}")
        
    if price is not None and not isinstance(price, (float, int)):
        raise Exception(f"Price must be a float or None. Got: {type(price).__name__}")
        
    if price is not None:
        price = float(price)

    record_id = str(uuid.uuid4())
    location = location.lower()
    timestamp = datetime.utcnow().isoformat()

    record = {
        "id": record_id,
        "source": source,
        "commodity": commodity,
        "location": location,
        "price": price,
        "text": text,
        "timestamp": timestamp,
        "signal_type": signal_type,
        "confidence": confidence
    }

    # ── Location enrichment: replace 'unknown'/'global' via text scan ──────────
    if record["location"] in ("unknown", "global", ""):
        extracted = _extract_location_from_text(record.get("text", ""))
        if extracted:
            record["location"] = extracted

    return record

if __name__ == "__main__":
    test_record = create_record(
        source="telegram",
        commodity="fuel",
        location="India",
        text="fuel shortage reported",
        price=None,
        signal_type="behavior",
        confidence=1.5
    )
    print(test_record)
