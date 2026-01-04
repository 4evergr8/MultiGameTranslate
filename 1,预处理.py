import json
import re

# 日语字符范围
jp_pattern = re.compile(r'[\u3040-\u30FF\u4E00-\u9FFF]')

with open('ManualTransFile.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('其他文件/剔除.json', 'r', encoding='utf-8') as f:
    remove_data = json.load(f)

remove_keys = set(remove_data.keys())

def jp_ratio(text):
    jp_count = sum(1 for c in text if jp_pattern.match(c))
    return jp_count / len(text) if text else 0

filtered_items = [
    (k, v) for k, v in data.items()
    if jp_pattern.search(k) and k not in remove_keys
]

filtered_items.sort(key=lambda item: jp_ratio(item[0]), reverse=True)

sorted_data = dict(filtered_items)

with open('ManualTransFile.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_data, f, ensure_ascii=False, indent=4)
