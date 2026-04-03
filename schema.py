import uuid
from datetime import datetime

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

    return {
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
