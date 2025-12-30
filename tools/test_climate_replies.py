import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import Api


def main():
    api = Api()

    samples = [
        # Same place, different phrasings -> should pick different variants
        "Khí hậu Hà Nội như thế nào?",
        "Mô tả khí hậu Hà Nội giúp mình",
        "Hà Nội có khí hậu ra sao?",

        "Cho mình hỏi khí hậu Lào Cai có lạnh không?",
        "Khí hậu Lào Cai có sương muối không?",
        "Lào Cai khí hậu thế nào vào mùa đông?",

        "Khí hậu Miền Tây có đặc trưng gì?",
        "Miền Tây (ĐBSCL) khí hậu ra sao?",
        "Khí hậu đồng bằng sông Cửu Long có gì nổi bật?",

        "Khí hậu Tây Nguyên mùa khô ra sao?",
        "Tây Nguyên có mấy mùa, mùa mưa thế nào?",

        # Weather (realtime) should still route to API weather, not dataset
        "Thời tiết Hà Nội hôm nay thế nào?"
    ]

    print("=== Climate replies smoke test ===")
    for s in samples:
        target = api._extract_weather_location_target(s)
        is_climate = api._is_climate_question(s)
        reply = None
        if target and is_climate:
            reply = api._get_climate_reply_for_target(target, message=s)

        print("\nQ:", s)
        print("target:", target)
        print("is_climate:", is_climate)
        print("reply:")
        print(reply or "<None>")

    # Validate dataset loads
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "machine learning", "dataset", "climate_replies.json")
    dataset_path = os.path.abspath(dataset_path)
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "region_templates" in data and "province_overrides" in data
    print("\nDataset OK:", dataset_path)


if __name__ == "__main__":
    main()
