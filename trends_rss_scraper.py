import requests
import json
from schema import create_record

def fetch_trends():
    url = "https://trends.google.com/trends/api/dailytrends?hl=en-US&geo=IN"

    try:
        response = requests.get(url, timeout=10)

        # Google returns weird prefix → remove it
        text = response.text.replace(")]}',", "")

        data = json.loads(text)

        trends = []

        for day in data["default"]["trendingSearchesDays"]:
            for trend in day["trendingSearches"]:
                trends.append(trend["title"]["query"])

        return trends[:10]

    except Exception as e:
        print("Error fetching trends:", e)
        return []

def main():
    trends = fetch_trends()

    if not trends:
        print("Using fallback trends")
        trends = ["fuel shortage", "rice price"]

    with open("data/trends_data.json", "a", encoding="utf-8") as f:
        for trend in trends:
            record = create_record(
                source="trends",
                commodity="unknown",
                location="global",
                text=trend,
                price=None,
                signal_type="behavior",
                confidence=0.8
            )

            f.write(json.dumps(record) + "\n")
            print("[OK]", trend)

if __name__ == "__main__":
    main()
