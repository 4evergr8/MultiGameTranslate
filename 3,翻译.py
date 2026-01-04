import json

FILE = 'ManualTransFile.json'
BATCH = 10

def load_json():
    with open(FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data):
    with open(FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

while True:
    data = load_json()
    items = list(data.items())

    if not items:
        break

    # 从头部获取 BATCH 行
    batch = items[:BATCH]
    keys = [k for k, _ in batch]

    # 检查 batch 中是否存在键值不等于键名
    stop = any(k != v for k, v in batch)

    # 取 batch 中未翻译的行
    untranslated = [(k, v) for k, v in batch if k == v]
    if not untranslated:
        # 当前 batch 没有可翻译行，如果 stop=True 则直接退出
        if stop:
            break
        else:
            continue

    # 输出未翻译的键名
    for k, _ in untranslated:
        print(k.replace('\n', '#'))

    user_lines = []
    while True:
        line = input()
        if line == '':
            break
        # 用户输入中 # 转回 \n
        user_lines.append(line.replace('#', '\n'))

    # 用户输入行数不等于输出行数，重新输出
    if len(user_lines) != len(untranslated):
        for k, _ in untranslated:
            print(k.replace('\n', '#'))
        continue

    # 将翻译写入底部
    for (k, _), v in zip(untranslated, user_lines):
        data.pop(k, None)
        data[k] = v

    save_json(data)

    # 如果 batch 中存在已翻译行，退出循环
    if stop:
        break

# 打印所有键名键值相等的条目
data = load_json()
remaining_untranslated = {k: v for k, v in data.items() if k == v}

if remaining_untranslated:
    print("\n以下条目仍未翻译（键名=键值）：")
    for k, v in remaining_untranslated.items():
        print(k)
else:
    print("\n所有条目已翻译完成")
