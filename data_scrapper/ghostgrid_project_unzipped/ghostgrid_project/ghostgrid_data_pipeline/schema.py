import uuid
from datetime import datetime

def create_record(source, commodity, location, text, price=None, signal_type="behavior", confidence=0.5):
    return {
        "id": str(uuid.uuid4()),
        "source": source,
        "commodity": commodity,
        "location": location.lower(),
        "price": price,
        "text": text,
        "timestamp": datetime.utcnow().isoformat(),
        "signal_type": signal_type,
        "confidence": confidence
    }
