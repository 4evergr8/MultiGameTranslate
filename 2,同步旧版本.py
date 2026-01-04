import json

with open('ManualTransFile.json', 'r', encoding='utf-8') as f:
    new_data = json.load(f)

with open('old.json', 'r', encoding='utf-8') as f:
    old_data = json.load(f)

matched = []
unmatched = []

for k, v in new_data.items():
    if k in old_data:
        matched.append((k, old_data[k]))
    else:
        unmatched.append((k, v))

# 写过的条目置底，其余保持原顺序
result = dict(unmatched + matched)

with open('ManualTransFile.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)
