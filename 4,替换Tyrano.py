import os
import json
import shutil
from pathlib import Path
import re

# ==================== 配置区 ====================
TRANSLATION_FILE = "ManualTransFile.json"       # 翻译对文件
SOURCE_FOLDER = "1游戏"                          # 源文件夹
TARGET_FOLDER = "2翻译"                          # 复制目标文件夹
FILE_EXTENSIONS = (".json", ".ks", ".js", ".csv")  # 要处理的文件类型
# ================================================

def load_translations(file_path):
    """加载翻译对，并过滤掉键值和键名相同的条目"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{file_path} 必须是一个 JSON 对象（键值对）")

    # 过滤掉键值和键名相同的条目
    filtered_data = {k: v for k, v in data.items() if k != v}

    print(f"✓ 加载了 {len(filtered_data)} 条翻译对（已过滤掉键值等于键名的条目）")
    return filtered_data


def clone_files(src_folder, dst_folder):
    """清空目标文件夹并将源文件夹内指定扩展名文件完整复制过去"""
    dst_path = Path(dst_folder)
    if dst_path.exists():
        shutil.rmtree(dst_path)
    for src_file in Path(src_folder).rglob("*"):
        if src_file.is_file() and src_file.suffix in FILE_EXTENSIONS:
            rel_path = src_file.relative_to(src_folder)
            target_file = dst_path / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, target_file)
    print(f"✓ 已将 {src_folder} 内目标文件复制到 {dst_folder}")

def find_all_files(root_folder):
    """遍历文件夹，找出所有指定扩展名的文件"""
    files = []
    for ext in FILE_EXTENSIONS:
        files.extend(Path(root_folder).rglob(f"*{ext}"))
    print(f"✓ 找到 {len(files)} 个目标文件")
    return files

def count_occurrences_in_files(files, text):
    """统计文本在文件中出现次数及位置信息"""
    occurrences = []
    escaped = re.escape(text)

    for file_path in files:
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            matches = list(re.finditer(escaped, content))
            for match in matches:
                line_no = content[:match.start()].count('\n') + 1
                context_start = max(0, match.start() - 30)
                context_end = match.end() + 30
                occurrences.append({
                    'file': str(file_path),
                    'line': line_no,
                    'context': content[context_start:context_end].replace('\n', '\\n')
                })
        except Exception as e:
            print(f"⚠️ 读取文件失败 {file_path}: {e}")
    return occurrences

def replace_in_file(file_path, original, translation):
    """在文件中将所有精确匹配的 original 替换为 translation"""
    try:
        content = file_path.read_text(encoding='utf-8')
        escaped = re.escape(original)
        new_content = re.sub(escaped, translation, content)
        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"⚠️ 写入文件失败 {file_path}: {e}")
        return False

def main():
    # 先清空并克隆文件
    clone_files(SOURCE_FOLDER, TARGET_FOLDER)

    translations = load_translations(TRANSLATION_FILE)
    files = find_all_files(TARGET_FOLDER)

    if not files:
        print("❌ 未找到任何目标文件")
        return

    unreplaced = []  # 记录未处理的条目
    to_process_unique = []
    to_process_multiple = []

    print("\n第一阶段：扫描所有翻译对，分类处理...\n")

    # 第一步：扫描并分类（只寻找键名，不再找键值）
    for original, translation in translations.items():
        occurrences = count_occurrences_in_files(files, original)

        if len(occurrences) == 0:
            unreplaced.append({
                'original': original,
                'translation': translation,
                'reason': '原文未出现'
            })
        elif len(occurrences) == 1:
            to_process_unique.append((original, translation, occurrences[0]))
        else:
            to_process_multiple.append((original, translation, len(occurrences)))

    # 第二步：处理唯一出现
    print(f"\n第二阶段：处理 {len(to_process_unique)} 条唯一出现的翻译...\n")
    for original, translation, loc in to_process_unique:
        print(f"处理唯一匹配: {original[:40]}{'...' if len(original)>40 else ''}")
        file_path = Path(loc['file'])
        if replace_in_file(file_path, original, translation):
            print(f"   → 已替换: {file_path.name} 第 {loc['line']} 行")
        else:
            print(f"   → 替换失败: {file_path}")
            unreplaced.append({
                'original': original,
                'translation': translation,
                'reason': '唯一匹配但替换失败',
                'location': loc
            })

    # 第三步：处理重复出现的，按长度降序
    if to_process_multiple:
        print(f"\n第三阶段：处理 {len(to_process_multiple)} 条重复出现的翻译（按长度从长到短）...\n")
        to_process_multiple.sort(key=lambda x: len(x[0]), reverse=True)

        for original, translation, count in to_process_multiple:
            print(f"处理重复({count}次) 长句优先: {original[:40]}{'...' if len(original)>40 else ''}")
            current_occ = count_occurrences_in_files(files, original)
            if len(current_occ) == 0:
                print("   → 已被更长句替换覆盖，跳过")
                continue
            replaced_any = False
            for loc in current_occ:
                file_path = Path(loc['file'])
                if replace_in_file(file_path, original, translation):
                    replaced_any = True
            if replaced_any:
                print(f"   → 已替换所有 {len(current_occ)} 处剩余出现")
            else:
                print("   → 替换失败")
                unreplaced.append({
                    'original': original,
                    'translation': translation,
                    'reason': f'重复出现 {count} 次，替换失败',
                    'locations': current_occ[:3]
                })

    # 输出最终未替换列表
    print("\n" + "=" * 80)
    print("全部处理完成！以下是真正未处理的翻译对：")
    print("=" * 80)
    if not unreplaced:
        print("🎉 完美！所有翻译都已成功处理（替换或已存在）")
    else:
        for item in unreplaced:
            print(f"\n原文: {item['original']}")
            print(f"译文: {item['translation']}")
            print(f"原因: {item['reason']}")
            if 'locations' in item:
                print("   出现位置（前3个）：")
                for loc in item['locations']:
                    print(f"     文件: {loc['file']}")
                    print(f"     行号: {loc['line']}")
                    print(f"     上下文: ...{loc['context']}...")
            elif 'location' in item:
                loc = item['location']
                print(f"   位置: {loc['file']} 第 {loc['line']} 行")

    total = len(translations)
    processed = total - len(unreplaced)
    print(f"\n总结：共 {total} 条翻译对，已成功处理 {processed} 条，需手动关注 {len(unreplaced)} 条")

if __name__ == "__main__":
    main()
