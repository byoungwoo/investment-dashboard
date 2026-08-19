import os
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

PORTFOLIO = {
    "AVGO": {
        "name_kr": "브로드컴",
        "thesis": "AI Networking / ASIC",
        "survival": 5,
        "growth": 5,
        "ticker": "AVGO",
    },
    "ABB": {
        "name_kr": "ABB",
        "thesis": "AI Power & Electrification",
        "survival": 5,
        "growth": 4,
        "ticker": "ABBN.SW",  # SIX Swiss Exchange (더 안정적)
    },
    "STX": {
        "name_kr": "씨게이트",
        "thesis": "AI Storage / HAMR",
        "survival": 4,
        "growth": 4,
        "ticker": "STX",
    },
    "ISC": {
        "name_kr": "아이에스씨",
        "thesis": "AI Test Socket",
        "survival": 4,
        "growth": 4,
        "ticker": "095340.KQ",  # KOSDAQ
    },
    "COHR": {
        "name_kr": "코히런트",
        "thesis": "Optical / Photonics",
        "survival": 4,
        "growth": 5,
        "ticker": "COHR",
    },
    "PLTR": {
        "name_kr": "팔란티어",
        "thesis": "AI Software",
        "survival": 5,
        "growth": 5,
        "ticker": "PLTR",
    },
    "IREN": {
        "name_kr": "아이런",
        "thesis": "AI Data Center",
        "survival": 3,
        "growth": 5,
        "ticker": "IREN",
    },
}

WEIGHTS = {
    "valuation": 0.50,
    "technical": 0.30,
    "macro": 0.20,
}

# Score → Grade thresholds
GRADE_THRESHOLDS = [
    (88, "S", "Strong Accumulate"),
    (78, "A", "Accumulate"),
    (65, "B", "Watch / Accumulate"),
    (50, "C", "Hold / Wait"),
    (0,  "D", "No Chase / Reduce"),
]
