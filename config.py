import os
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# FOMC SEP long-run r* estimate — update when FOMC revises neutral rate outlook
NEUTRAL_RATE = 2.5

PORTFOLIO = {
    "AVGO": {
        "name_kr": "브로드컴",
        "thesis": "AI Compute ASIC + AI Networking + VMware Private AI Infrastructure",
        "role": "Core AI Infrastructure / Offensive Survival",
        "note": (
            "FY26 Q3 이후 AVGO는 custom accelerator, AI networking, "
            "VMware private AI infrastructure까지 이어지는 AI stack exposure로 재정의. "
            "Thesis는 강화하지만 valuation 부담 때문에 grade를 억지로 올리지는 않음."
        ),
        "survival": 5,
        "growth": 5,
        "ticker": "AVGO",
    },
    "ABB": {
        "name_kr": "ABB",
        "thesis": "AI Power & Electrification",
        "role": "Defensive Core",
        "note": "전력화, 자동화, 산업 인프라 노출로 AI capex 둔화 시에도 방어력이 있는 core holding.",
        "survival": 5,
        "growth": 4,
        "ticker": "ABBN.SW",  # SIX Swiss Exchange (더 안정적)
    },
    "VRT": {
        "name_kr": "버티브",
        "thesis": "AI Data Center Power & Cooling",
        "role": "AI Infrastructure Growth",
        "note": "AI data center의 power와 cooling 병목에 직접 노출된 고성장 인프라 자산.",
        "survival": 5,
        "growth": 5,
        "ticker": "VRT",
    },
    "IREN": {
        "name_kr": "아이런",
        "thesis": "AI Data Center",
        "role": "High-Beta AI Optionality",
        "note": "AI data center thesis 성공 시 upside는 크지만 자본집약도와 사업구조상 survival risk가 높음.",
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
