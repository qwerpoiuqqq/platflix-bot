import json
from collections import defaultdict

def count_group_slots():
    with open("user_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    group_counts = defaultdict(int)
    for user in data:
        group = user.get("그룹")
        if group:
            group_counts[group] += 1
    result = []
    for group, count in group_counts.items():
        remaining = 5 - (count - 1)  # 마스터 제외
        result.append(f"{group} → 남은 자리: {remaining}명")
    return result
