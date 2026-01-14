import time

import requests
import websocket
from utils.grok import send, enter, receive, wait
import os
import subprocess

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

user_data_dir = os.path.join("其他文件/userdata")
user_data_dir = os.path.abspath(user_data_dir)
cmd = [
    chrome_path,
    "--remote-debugging-port=9222",
    f"--user-data-dir={user_data_dir}",
    "--remote-allow-origins=*",
    "--new-window"

]

subprocess.Popen(cmd)

input("请登录Grok后按回车")


# 1. 获取当前可用页面的 WebSocket 地址
resp = requests.get("http://127.0.0.1:9222/json")
targets = resp.json()

page = next(t for t in targets if t["type"] == "page")
ws_url = page["webSocketDebuggerUrl"]
ws = websocket.WebSocket()
ws.connect(ws_url)

while True:
    last_text = input("你说:")
    response = receive(ws)
    send(ws, last_text)
    enter(ws)
    wait(ws)
    response=receive(ws, response)
    print(f"Grok说:{response}")