import sys
import requests

# Uses your Ngrok URL if passed in the terminal, otherwise defaults to localhost
API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/v1/predict"

test_cases = [
    {
        "name": "Test Case A: Sarcasm/Slang", 
        "text": "Atta prices are flying to the moon, thanks for nothing!", 
        "commodity": "atta", 
        "source": "twitter"
    },
    {
        "name": "Test Case B: Code-Switching", 
        "text": "Market mein cheeni khatam ho gayi hai, urgent supply chahiye.", 
        "commodity": "sugar", 
        "source": "telegram"
    },
    {
        "name": "Test Case C: False Alarm", 
        "text": "I am selling my old car because I need fuel money.", 
        "commodity": "fuel", 
        "source": "olx"
    }
]

print(f"\n🚀 Firing DB-Aligned Stress Tests at: {API_URL}\n" + "━"*60)

for tc in test_cases:
    payload = {
        "normalized_text": tc["text"],
        "commodity": tc["commodity"],
        "source": tc["source"]
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        
        if not response.ok:
            print(f"❌ Error {response.status_code} on {tc['name']}: {response.text}\n")
            continue
            
        result = response.json()
        
        print(f"--- {tc['name']} ---")
        print(f"Text       : '{tc['text']}'")
        print(f"Prediction : {result.get('signal_type')} (Confidence: {result.get('confidence'):.2f})")
        print(f"DB Routing : Severity={result.get('severity').upper()} | Category={result.get('category').upper()}\n")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect. Is the Uvicorn server running?\n")
        break
    except Exception as e:
        print(f"❌ Unexpected Error: {e}\n")