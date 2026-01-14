import json
import requests
import websocket
from utils.grok import send, enter, receive, wait
import os
import subprocess
import time

# -------------------------- 配置项 --------------------------
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = os.path.abspath("其他文件/userdata")
DEBUG_PORT = 9222
FILE = 'ManualTransFile.json'
BATCH = 20


# -------------------------- 工具函数 --------------------------
def load_json():
    """加载JSON文件，添加异常处理"""
    try:
        with open(FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：未找到文件 {FILE}")
        return {}
    except json.JSONDecodeError:
        print(f"错误：{FILE} 不是有效的JSON文件")
        return {}


def save_json(data):
    """保存JSON文件，添加异常处理"""
    try:
        with open(FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"已成功保存数据到 {FILE}")
    except Exception as e:
        print(f"保存文件失败：{e}")


def get_websocket_url(port=9222):
    """获取Chrome调试页面的WebSocket地址"""
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=10)
        resp.raise_for_status()  # 抛出HTTP错误
        targets = resp.json()
        page = next(t for t in targets if t["type"] == "page")
        return page["webSocketDebuggerUrl"]
    except requests.exceptions.RequestException as e:
        print(f"获取调试页面失败：{e}")
        print("请确认Chrome已启动并开启远程调试")
        return None
    except StopIteration:
        print("未找到有效的页面调试目标")
        return None


# -------------------------- 主流程 --------------------------
if __name__ == "__main__":
    # 1. 启动Chrome（可选，注释掉则手动启动）
    """
    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--remote-allow-origins=*",
        "--new-window"
    ]
    subprocess.Popen(cmd)
    input("请登录Grok后按回车继续...")
    """

    # 2. 建立WebSocket连接
    ws_url = get_websocket_url(DEBUG_PORT)
    if not ws_url:
        exit(1)

    ws = websocket.WebSocket()
    try:
        ws.connect(ws_url)
        print(f"成功连接到WebSocket：{ws_url}")
    except Exception as e:
        print(f"WebSocket连接失败：{e}")
        exit(1)

    # 3. 批量处理翻译任务
    try:
        while True:
            data = load_json()
            if not data:
                print("JSON文件中无数据，退出")
                break

            items = list(data.items())
            batch = items[:BATCH]  # 取前BATCH条
            stop = any(k != v for k, v in batch)  # 检查是否有已翻译条目
            untranslated = [(k, v) for k, v in batch if k == v]  # 筛选未翻译条目

            if not untranslated:
                if stop:
                    print("当前批次无未翻译条目且包含已翻译条目，退出")
                    break
                continue

            # 处理待翻译文本（替换换行符，拼接成字符串）
            processed_keys = [k.replace('\n', '#') for k, _ in untranslated]
            last_text = '\n'.join(processed_keys)
            print(f"\n待翻译内容：\n{last_text}")

            # 4. 发送到Grok并获取翻译结果
            try:
                # 清空之前的响应（可选，根据grok工具函数特性调整）
                receive(ws)
                # 发送待翻译内容并回车
                send(ws, last_text)
                enter(ws)
                wait(ws)  # 等待Grok响应
                # 获取翻译结果
                response = receive(ws)
                print(f"\nGrok返回结果：\n{response}")

                # 5. 处理返回结果（按行拆分，还原换行符）
                # 按换行拆分，过滤空行
                user_lines = [line.replace('#', '\n').strip() for line in response.split('\n') if line.strip()]

                # 校验行数是否匹配
                if len(user_lines) != len(untranslated):
                    print(f"错误：返回行数({len(user_lines)})与待翻译行数({len(untranslated)})不匹配")
                    print("重新发送待翻译内容...")
                    continue

                # 6. 更新翻译结果（删除原条目，添加到末尾）
                for (k, _), v in zip(untranslated, user_lines):
                    data.pop(k, None)
                    data[k] = v

                # 7. 保存更新后的数据
                save_json(data)

                # 8. 检查是否需要停止循环
                if stop:
                    print("当前批次包含已翻译条目，停止处理")
                    break

            except Exception as e:
                print(f"处理当前批次失败：{e}")
                continue

    finally:
        # 关闭WebSocket连接
        ws.close()
        print("WebSocket连接已关闭")

    # 4. 输出剩余未翻译条目
    data = load_json()
    remaining_untranslated = {k: v for k, v in data.items() if k == v}
    if remaining_untranslated:
        print("\n以下条目仍未翻译：")
        for k in remaining_untranslated:
            print(k)
    else:
        print("\n所有条目已翻译完成！")