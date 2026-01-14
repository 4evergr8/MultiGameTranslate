import json
import time
import itertools


# 封装核心逻辑为函数：参数1=ws连接对象，参数2=要输入的文本内容
def send(ws, input_text):
    # 生成唯一的消息ID
    msg_id = next(itertools.count(1))
    input_text = input_text.replace("\n", "\\n")

    # 定义要执行的JS代码（动态替换输入文本）
    js_code = f"""
    (() => {{
        const input = document.querySelector(
            'div[contenteditable="true"][aria-multiline="true"]'
        ) || document.querySelector('div[contenteditable="true"]');

        if (!input) {{
            console.log('未找到输入框');
            return;
        }}

        input.focus();

        // 清空原有内容
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);

        // 输入指定文本（动态替换）
        document.execCommand('insertText', false, "{input_text}");

        console.log('已向输入框输入：{input_text}');
    }})();
    """

    # 构造请求消息
    request_msg = json.dumps({
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js_code,
            "returnByValue": True
        }
    })

    # 发送请求
    ws.send(request_msg)
    while True:
        # 接收WebSocket消息（阻塞等待）
        data = ws.recv()
        msg = json.loads(data)

        # 检查是否是当前请求的响应（ID匹配）
        if "id" in msg and msg["id"] == msg_id:
            response = msg
            break  # 匹配到后立即退出循环

    # 返回响应结果
    return response


def enter(ws):
    # 生成唯一的消息ID
    msg_id = next(itertools.count(1))

    # 定义要执行的JS代码（修复语法错误 + 完善Enter事件）
    js_code = f"""
    (() => {{
        const input = document.querySelector(
            'div[contenteditable="true"][aria-multiline="true"]'
        ) || document.querySelector('div[contenteditable="true"]');

        if (!input) {{
            console.log('未找到输入框');
            return;
        }}

        input.focus();

        // 修复1：完整模拟Enter键的所有事件（keydown + keypress + keyup）
        // 仅keydown可能不生效，补充完整事件链
        const events = [
            new KeyboardEvent('keydown', {{
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            }}),
            new KeyboardEvent('keypress', {{
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            }}),
            new KeyboardEvent('keyup', {{
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            }})
        ];

        // 依次触发事件，模拟真实按Enter键
        events.forEach(evt => input.dispatchEvent(evt));

        console.log('已模拟按下Enter键');
    }})();
    """

    # 构造请求消息
    request_msg = json.dumps({
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js_code,
            "returnByValue": True
        }
    })

    # 发送请求
    ws.send(request_msg)
    while True:
        # 接收WebSocket消息（阻塞等待）
        data = ws.recv()
        msg = json.loads(data)

        # 检查是否是当前请求的响应（ID匹配）
        if "id" in msg and msg["id"] == msg_id:
            response = msg
            break  # 匹配到后立即退出循环

    # 返回响应结果
    return response



def wait(ws):
    """
    每100ms通过CDP获取整个页面HTML源码，在Python端检查是否包含指定文本"M0,1.600000023841858"
    :param ws: 已建立连接的WebSocket对象（CDP连接）
    :return: 布尔值 - 检测到文本时返回True，文本消失时返回False
    """
    # 初始化变量
    msg_id_iter = itertools.count(1)  # 唯一消息ID迭代器
    check_interval = 0.1  # 检查间隔：100ms

    # 核心循环：持续检查直到文本消失
    while True:
        # 每次循环前等待100ms
        time.sleep(check_interval)

        # ========== 第一步：通过CDP获取整个页面的完整HTML源码 ==========
        # 生成新的消息ID（获取文档根节点）
        get_doc_id = next(msg_id_iter)
        # 1. 发送获取文档根节点的请求（DOM.getDocument）
        get_doc_msg = json.dumps({
            "id": get_doc_id,
            "method": "DOM.getDocument",
            "params": {"depth": -1}  # 递归获取所有节点
        })
        ws.send(get_doc_msg)

        # 接收并解析根节点响应
        root_node_id = None
        while True:
            data = ws.recv()
            msg = json.loads(data)
            if "id" in msg and msg["id"] == get_doc_id:
                root_node_id = msg["result"]["root"]["nodeId"]
                break

        # 生成新的消息ID（获取根节点OuterHTML）
        get_html_id = next(msg_id_iter)
        # 2. 发送获取完整HTML的请求（DOM.getOuterHTML）
        get_html_msg = json.dumps({
            "id": get_html_id,
            "method": "DOM.getOuterHTML",
            "params": {"nodeId": root_node_id}
        })
        ws.send(get_html_msg)

        # 接收并解析完整HTML响应
        page_html = ""
        while True:
            data = ws.recv()
            msg = json.loads(data)
            if "id" in msg and msg["id"] == get_html_id:
                page_html = msg["result"].get("outerHTML", "")
                break

        # ========== 第二步：在Python端检查目标文本 ==========
        target_text = "停止模型响应"
        has_target_text = target_text in page_html

        # 打印检测状态（便于调试）
        status = "加载中" if has_target_text else "加载完成"
        print(f"检测状态：{status} | 页面源码长度：{len(page_html)} 字符")

        # 核心判定：未检测到文本则结束函数，反之继续循环
        if not has_target_text:
            return False
        # 检测到文本则继续下一次循环检查


def receive(ws, last: str = ""):
    """
    循环检测AI回复内容，直到连续两次提取的内容相同（视为回复完毕）
    :param ws: 已建立连接的WebSocket对象
    :param last: 纯文本，若最终结果与该文本相等则报错
    :return: 最终的AI回复文本（无结果返回"未找到 Grok 回复"）
    :raises ValueError: 当最终current_value与last参数相等时触发
    """
    # 初始化变量：记录上一次的value和当前的value
    last_value = None
    current_value = None
    # 生成唯一的消息ID迭代器（每次请求用新ID）
    msg_id_iter = itertools.count(1)
    # 轮询间隔（可根据需求调整）
    poll_interval = 0.5

    # 核心循环：直到连续两次value相同
    while True:
        # 每次循环前短暂等待
        time.sleep(poll_interval)

        # 生成新的消息ID
        msg_id = next(msg_id_iter)

        # 核心JS代码（提取文本）
        js_code = """
        (() => {
            // 所有可见文本容器
            const all = Array.from(document.querySelectorAll('div, article, section'))
                .filter(el => {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                    if (el.offsetHeight < 40) return false;
                    if (el.querySelector('textarea, input, button')) return false;
                    return true;
                });

            // 提取文本并筛选像“回复”的内容
            const texts = all
                .map(el => el.innerText?.trim())
                .filter(t => t && t.length > 20 && t.includes('\\n'));

            if (texts.length === 0) {
                console.log('未找到 Grok 回复');
                return '未找到 Grok 回复'; // 返回明确的无结果标识
            }

            // 最新的一条通常在最后，作为返回值
            const finalReply = texts[texts.length - 1];
            console.log(finalReply);
            return finalReply; // 核心：将提取的文本作为返回值
        })();
        """

        # 构造WebSocket请求消息
        request_msg = json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "returnByValue": True,  # 关键：让返回值能被Python捕获
                "awaitPromise": False  # 非异步逻辑，无需等待Promise
            }
        })

        # 发送请求
        ws.send(request_msg)
        response = None
        while True:
            data = ws.recv()
            msg = json.loads(data)
            # 匹配当前请求的ID，拿到响应后退出循环
            if "id" in msg and msg["id"] == msg_id:
                response = msg
                break

        # 安全提取value（避免字段缺失报错）
        current_value = response.get('result', {}).get('result', {}).get('value', '未找到 Grok 回复')

        # 判定：连续两次提取的内容相同，视为回复完毕
        if current_value == last_value:
            # 检查是否与last参数相等，相等则报错
            if last and current_value.strip() == last.strip():
                raise ValueError(
                    f"错误：最终提取的AI回复与指定文本相等！\n"
                    f"指定文本（last）：{last[:50]}...\n"
                    f"最终回复内容：{current_value[:50]}..."
                )
            # 不相等则正常返回结果
            return current_value

        # 更新上一次的值，继续循环
        last_value = current_value

