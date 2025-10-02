#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ICP 反查备案工具 · 全功能版
- 左侧历史栏，点击回显
- 自动持久化 history.json
- 复制后整行标色（用户自选颜色）
- 使用说明 / GitHub 链接
- 历史清理（单条/一键）
- CSV 导出
"""
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont, colorchooser
import webbrowser
import tkinter.filedialog
import csv

import requests
from bs4 import BeautifulSoup
import 域名反查
import re


# ---------- 工具 ----------
def has_chinese(keyword: str) -> bool:
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
        self.title("ICP 备案结果 · 全功能版")
        self.geometry("1100x550")
        self.minsize(950, 450)

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

        # ---------- 配置 ----------
        self.history_file = "history.json"
        self.history = self.load_history()
        self.current_kw = None
        self.copy_color = "#ff4d4f"
        self.github_url = "https://github.com/star-zeddm/ICP_Search"   # ← 换成你的地址



        # ---------------- 下部主区域 ----------------
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
        self.his_lb.bind("<Delete>", self.on_del_single_history)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="一键清空", command=self.on_clear_all_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="选色", command=self.choose_color).pack(side=tk.LEFT, padx=2)

        # ---- 右：主内容 ----
        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self.build_main(right)

        self.refresh_history_list()

    # ---------- 构建主内容 ----------
    def build_main(self, master):
        top = ttk.Frame(master)
        top.pack(fill=tk.X, pady=8)
        left_top = ttk.Frame(top)
        left_top.pack(side=tk.LEFT)
        ttk.Label(left_top, text="企业名称/主域：").pack(side=tk.LEFT)
        self.entry = ttk.Entry(left_top, width=30)
        self.entry.pack(side=tk.LEFT, padx=5)
        self.entry.bind("<Return>", lambda e: self.query())
        ttk.Button(left_top, text="查询", command=self.query).pack(side=tk.LEFT, padx=10)
        ttk.Button(left_top, text="导出CSV", command=self.export_csv).pack(side=tk.LEFT, padx=10)

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
        self.tv.bind("<Control-c>", self.copy_cell)

    # ---------- 原功能（未改动） ----------
    def load_history(self):
        if not os.path.exists(self.history_file):
            return {}
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            fixed = {}
            for k, v in raw.items():
                if isinstance(v, list):
                    fixed[k] = {"rows": v, "red": []}
                else:
                    fixed[k] = v
            return fixed
        except Exception:
            return {}

    def save_history(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def refresh_history_list(self):
        self.his_lb.delete(0, tk.END)
        for kw in sorted(self.history.keys(), key=lambda x: x.lower()):
            self.his_lb.insert(tk.END, kw)

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.copy_color, title="选择复制后标色")[1]
        if color:
            self.copy_color = color
            self.tv.tag_configure("red", background=color, foreground="white")
            messagebox.showinfo("提示", f"已设置复制标色为 {color}")

    def on_del_single_history(self, event=None):
        if not self.his_lb.curselection():
            return
        kw = self.his_lb.get(self.his_lb.curselection()[0])
        if messagebox.askyesno("确认", f"删除历史记录【{kw}】？"):
            self.history.pop(kw, None)
            self.save_history()
            self.refresh_history_list()
            if self.current_kw == kw:
                self.current_kw = None
                self.tv.delete(*self.tv.get_children())

    def on_clear_all_history(self):
        if messagebox.askyesno("确认", "清空全部历史记录？"):
            self.history.clear()
            self.save_history()
            self.refresh_history_list()
            self.current_kw = None
            self.tv.delete(*self.tv.get_children())

    def on_history_pick(self, _event=None):
        if not self.his_lb.curselection():
            return
        kw = self.his_lb.get(self.his_lb.curselection()[0])
        self.current_kw = kw
        self.tv.delete(*self.tv.get_children())
        data = self.history[kw]["rows"]
        red_set = set(self.history[kw].get("red", []))
        for rid, row in enumerate(data):
            iid = self.tv.insert("", tk.END, values=row)
            if str(rid) in red_set:
                self.tv.item(iid, tags=("red",))
        self.tv.tag_configure("red", background=self.copy_color, foreground="white")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, kw)

    def query(self):
        kw = self.entry.get().strip()
        if not kw:
            return
        self.tv.delete(*self.tv.get_children())
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

    def copy_cell(self, event=None):
        region = self.tv.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tv.identify_column(event.x)
        item = self.tv.identify_row(event.y)
        if not item:
            return
        value = self.tv.set(item, col)
        self.clipboard_clear()
        self.clipboard_append(value)
        self.tv.item(item, tags=("red",))
        if self.current_kw:
            rid = str(self.tv.index(item))
            red_list = self.history[self.current_kw].setdefault("red", [])
            if rid not in red_list:
                red_list.append(rid)
            self.save_history()

    def export_csv(self):
        if not self.current_kw:
            messagebox.showwarning("提示", "请先查询或选择历史记录")
            return
        rows = [self.tv.item(iid, "values") for iid in self.tv.get_children()]
        if not rows:
            messagebox.showwarning("提示", "无数据可导出")
            return
        file = tk.filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                               title="导出CSV", initialfile=f"{self.current_kw}_icp.csv")
        if not file:
            return
        try:
            with open(file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["备案号", "网站名称", "域名", "主办单位", "类型", "审核时间", "更新时间"])
                writer.writerows(rows)
            messagebox.showinfo("成功", f"已导出 {os.path.basename(file)}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{e}")


# ---------- main ----------
if __name__ == "__main__":
    try:
        import requests, bs4
    except ImportError:
        messagebox.showerror("缺少依赖", "pip install requests beautifulsoup4 lxml")
        raise SystemExit(1)
    App().mainloop()