#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ICP 反查备案工具 · 历史版
- 左侧历史栏，点击回显
- 自动持久化 history.json
- 柔和 UI，灰蓝渐变
- 双击行标红 + 滚动条
"""
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

import requests
from bs4 import BeautifulSoup
import 域名反查
import re


# ---------- 工具 ----------
def has_chinese(keyword: str) -> bool:
    """只要出现任意一个汉字就返回 True"""
    pattern = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
    return bool(pattern.search(keyword))


# ---------- 抓取 ----------
def get_icp(keyword):
    if has_chinese(keyword):
        keyword = keyword
    else:
        keyword = 域名反查.get_ICP(keyword)

    url = f'https://icp.aizhan.com/reverse-icp/?q={keyword}&t=company'
    headers = {
        'Host': 'icp.aizhan.com',
        'Cookie': '',
        'Sec-Ch-Ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://icp.aizhan.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Priority': 'u=0, i',
        'Connection': 'keep-alive',
    }
    response = requests.get(url, headers=headers)
    return response.text


def extract(html):
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.table-company-list")
    if not table:
        print("未找到备案表")
        return []

    rows = []
    for tr in table.select("tbody tr"):
        tds = [td.get_text(strip=True) for td in tr.select("td")]
        if len(tds) < 7:
            continue
        license_, name, domain, company, _type, audit, update = tds[:7]
        if company:
            rows.append([license_, name or "-", domain, company, _type, audit, update])
    return rows


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ICP 备案结果 · 历史版")
        self.geometry("1000x500")
        self.minsize(900, 400)

        # ---------- 样式 ----------
        self.tk_setPalette(background="#f5f7fa", foreground="#2c3e50")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f7fa")
        style.configure("TLabelframe", background="#f5f7fa", foreground="#2c3e50")
        style.configure("Treeview.Heading", background="#d1d9e6", relief="flat")
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff",
                        foreground="#2c3e50", rowheight=24, relief="flat", borderwidth=0)
        style.map("Treeview", background=[("selected", "#a8c6fa")])
        style.configure("TButton", relief="flat", background="#4a8eff", foreground="white",
                        borderwidth=0, focuscolor="none", padding=(6, 4))
        style.map("TButton", background=[("active", "#3a7eff")])

        # ---------- 历史数据 ----------
        self.history_file = "history.json"
        self.history = self.load_history()  # dict{ keyword : { "rows": [..], "red": [id, ..] } }
        self.current_kw = None

        # ---------------- 整体布局 ----------------
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ---- 左：历史栏 ----
        left = ttk.LabelFrame(paned, text="历史查询", width=200)
        paned.add(left, weight=0)
        self.his_lb = tk.Listbox(left, activestyle="none", bd=0, highlightthickness=0,
                                 bg="#ffffff", fg="#2c3e50", selectbackground="#a8c6fa",
                                 selectforeground="#ffffff", font=tkfont.Font(size=10))
        self.his_lb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.his_lb.bind("<<ListboxSelect>>", self.on_history_pick)

        # ---- 右：主内容 ----
        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self.build_main(right)

        # ---- 启动时填充历史 ----
        self.refresh_history_list()

    # ---------- 构建右侧 ----------
    def build_main(self, master):
        top = ttk.Frame(master)
        top.pack(fill=tk.X, pady=8)
        ttk.Label(top, text="企业名称/主域：").pack(side=tk.LEFT)
        self.entry = ttk.Entry(top, width=30)
        self.entry.pack(side=tk.LEFT, padx=5)
        self.entry.bind("<Return>", lambda e: self.query())
        ttk.Button(top, text="查询", command=self.query).pack(side=tk.LEFT, padx=10)

        # 表格 + 滚动条
        cols = ["备案号", "网站名称", "域名", "主办单位", "类型", "审核时间", "更新时间"]
        frame = ttk.Frame(master)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tv = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse", height=15)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for c in cols:
            self.tv.heading(c, text=c)
            self.tv.column(c, width=120, anchor="w")
        # 双击事件
        self.tv.bind("<Double-1>", self.on_row_double)
        self.tv.bind("<Control-c>", self.copy_cell)

    # ---------- 持久化 ----------
    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_history(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    # ---------- 列表刷新 ----------
    def refresh_history_list(self):
        self.his_lb.delete(0, tk.END)
        for kw in sorted(self.history.keys(), key=lambda x: x.lower()):
            self.his_lb.insert(tk.END, kw)

    # ---------- 点击历史 ----------
    def on_history_pick(self, _event=None):
        if not self.his_lb.curselection():
            return
        kw = self.his_lb.get(self.his_lb.curselection()[0])
        self.current_kw = kw
        for i in self.tv.get_children():
            self.tv.delete(i)
        data = self.history[kw]["rows"]
        red_set = set(self.history[kw].get("red", []))
        for rid, row in enumerate(data):
            iid = self.tv.insert("", tk.END, values=row)
            if str(rid) in red_set:
                self.tv.item(iid, tags=("red",))
        self.tv.tag_configure("red", background="#ff4d4f", foreground="white")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, kw)

    # ---------- 查询 ----------
    def query(self):
        kw = self.entry.get().strip()
        if not kw:
            return
        for i in self.tv.get_children():
            self.tv.delete(i)
        threading.Thread(target=self._do, args=(kw,), daemon=True).start()

    def _do(self, kw):
        try:
            html = get_icp(kw)
            data = extract(html)
        except Exception as e:
            print("抓取失败：", e)
            data = []
        for row in data:
            self.tv.insert("", tk.END, values=row)
        if data:
            self.history[kw] = {"rows": data, "red": []}
            self.save_history()
            self.refresh_history_list()

    # ---------- 双击标红 ----------
    def on_row_double(self, event):
        if not self.current_kw:
            return
        item = self.tv.identify_row(event.y)
        if not item:
            return
        # 切换红/白
        tags = list(self.tv.item(item, "tags"))
        if "red" in tags:
            tags.remove("red")
            new_color = ("",)
        else:
            tags = ["red"]
            new_color = ("red",)
        self.tv.item(item, tags=new_color)

        # 同步到 history
        rid = self.tv.index(item)
        red_list = self.history[self.current_kw].setdefault("red", [])
        rid_str = str(rid)
        if "red" in new_color:
            if rid_str not in red_list:
                red_list.append(rid_str)
        else:
            if rid_str in red_list:
                red_list.remove(rid_str)
        self.save_history()

    # ---------- 复制 + 标红 ----------
    def copy_cell(self, event=None):
        """复制当前单元格内容，并把整行标红"""
        region = self.tv.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tv.identify_column(event.x)  # #1 #2 ...
        item = self.tv.identify_row(event.y)
        if not item:
            return

        # 1. 复制到剪贴板
        value = self.tv.set(item, col)
        self.clipboard_clear()
        self.clipboard_append(value)

        # 2. 立即视觉标红
        self.tv.item(item, tags=("red",))

        # 3. 持久化到 history
        if self.current_kw:
            rid = str(self.tv.index(item))
            red_list = self.history[self.current_kw].setdefault("red", [])
            if rid not in red_list:
                red_list.append(rid)
            self.save_history()


# ---------- main ----------
if __name__ == "__main__":
    try:
        import requests, bs4
    except ImportError:
        messagebox.showerror("缺少依赖", "pip install requests beautifulsoup4 lxml")
        raise SystemExit(1)
    App().mainloop()