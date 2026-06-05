"""
三分步坐标拾取工具（管理端 GUI）
================================
按顺序点击图片上的 3 个位置：① 姓名  ② 成绩  ③ 参赛号
完成后保存到 coordinates.json，供 inject.py / Web 管理端使用。

使用（在 admin/ 目录下）：
    python pick_coords.py [图片路径]
不传参数时弹出文件选择对话框，默认从 template.jpg 加载。

快捷键：
    Ctrl+S  保存配置
    R       重新开始
    Q       退出
"""

import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# ============== 路径 ==============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(BASE_DIR, "template.jpg")
CONFIG_FILE = os.path.join(BASE_DIR, "coordinates.json")

# 三个字段：key 是配置 JSON 里用的键，label 是界面上显示的中文名
FIELDS = [
    ("name", "姓名"),
    ("time", "成绩"),
    ("bib",  "参赛号"),
]
# 每个字段对应的标记颜色
FIELD_COLORS = ["#e74c3c", "#f39c12", "#27ae60"]


class ThreeStepCoordPicker:
    """三分步坐标拾取器"""

    def __init__(self, root, image_path):
        self.root = root
        self.image_path = image_path
        self.root.title(f"三分步坐标拾取 - {os.path.basename(image_path)}")

        self.original_image = Image.open(image_path)
        self.img_w, self.img_h = self.original_image.size

        self._build_ui()
        self._layout_canvas()
        self._bind_events()

        self.current_step = 0
        self.coordinates = {}  # {key: (x, y)}
        self.marker_ids = []

        self.banner_id = self.canvas.create_text(
            self.display_w / 2, 24,
            text=self._banner_text(), fill="red",
            font=("Microsoft YaHei", 18, "bold"),
        )
        self._refresh_ui()

        if os.path.exists(CONFIG_FILE):
            self._load_existing(silent=True)

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        panel = tk.Frame(self.root, width=280, bg="#f8f9fb")
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        tk.Label(panel, text="三分步坐标拾取", font=("Microsoft YaHei", 14, "bold"),
                 bg="#f8f9fb", fg="#1c3783").pack(pady=(12, 4))
        tk.Label(panel, text="依次点击 3 个下划线位置：\n1) 姓 名\n2) 成 绩\n3) 参赛号",
                 font=("Microsoft YaHei", 10), bg="#f8f9fb",
                 justify=tk.LEFT).pack(padx=12, pady=4, anchor=tk.W)

        self.progress_var = tk.StringVar()
        tk.Label(panel, textvariable=self.progress_var, font=("Consolas", 10),
                 bg="#ffffff", relief=tk.SUNKEN, justify=tk.LEFT,
                 anchor=tk.NW).pack(padx=12, pady=6, fill=tk.X, ipady=6)

        tk.Label(panel, text="已采集坐标:", font=("Microsoft YaHei", 10, "bold"),
                 bg="#f8f9fb").pack(anchor=tk.W, padx=12, pady=(8, 2))
        self.coord_listbox = tk.Listbox(panel, font=("Consolas", 10), height=6)
        self.coord_listbox.pack(padx=12, fill=tk.X)

        btn_frame = tk.Frame(panel, bg="#f8f9fb")
        btn_frame.pack(fill=tk.X, padx=12, pady=12)
        for text, cmd in [
            ("保存配置 (Ctrl+S)", self.save_config),
            ("重新开始 (R)",     self.reset),
            ("加载已有配置",     self._load_existing),
        ]:
            b = tk.Button(btn_frame, text=text, command=cmd, height=2)
            b.pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="退出 (Q)", command=self.root.destroy,
                  height=2).pack(fill=tk.X, pady=(8, 0))

        self.status_var = tk.StringVar()
        self.status_var.set("按顺序点击 3 个下划线起点 | Ctrl+S 保存 | R 重置 | Q 退出")
        tk.Label(self.root, textvariable=self.status_var, bd=1,
                 relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def _layout_canvas(self):
        container = tk.Frame(self.root)
        container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.vbar = tk.Scrollbar(container, orient=tk.VERTICAL)
        self.hbar = tk.Scrollbar(container, orient=tk.HORIZONTAL)
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(
            container, cursor="crosshair", bg="#cccccc",
            xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.vbar.config(command=self.canvas.yview)
        self.hbar.config(command=self.canvas.xview)

        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        max_w = max(int(screen_w * 0.85) - 280, 400)
        max_h = max(int(screen_h * 0.85) - 80, 300)

        scale = min(max_w / self.img_w, max_h / self.img_h, 1.0)
        self.scale = scale
        if scale < 1.0:
            self.display_w = int(self.img_w * scale)
            self.display_h = int(self.img_h * scale)
            display_image = self.original_image.resize(
                (self.display_w, self.display_h), Image.LANCZOS
            )
        else:
            self.display_w, self.display_h = self.img_w, self.img_h
            display_image = self.original_image

        self.tk_image = ImageTk.PhotoImage(display_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.config(scrollregion=(0, 0, self.display_w, self.display_h))
        self.canvas.config(
            width=min(self.display_w, max_w),
            height=min(self.display_h, max_h),
        )

        win_w = min(self.display_w, max_w) + 280
        win_h = min(self.display_h, max_h) + 60
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.geometry(f"+{max((screen_w - win_w) // 2, 0)}+{max((screen_h - win_h) // 2, 0)}")

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.root.bind("<Control-s>", lambda e: self.save_config())
        self.root.bind("<Control-S>", lambda e: self.save_config())
        self.root.bind("<Key-r>", lambda e: self.reset())
        self.root.bind("<Key-R>", lambda e: self.reset())
        self.root.bind("<Key-q>", lambda e: self.root.destroy())
        self.root.bind("<Key-Q>", lambda e: self.root.destroy())

    # ---------------- 事件处理 ----------------
    def on_click(self, event):
        if self.current_step >= len(FIELDS):
            return
        display_x = self.canvas.canvasx(event.x)
        display_y = self.canvas.canvasy(event.y)
        orig_x = int(round(display_x / self.scale))
        orig_y = int(round(display_y / self.scale))

        key, name = FIELDS[self.current_step]
        color = FIELD_COLORS[self.current_step]
        r = 8
        dot = self.canvas.create_oval(
            display_x - r, display_y - r, display_x + r, display_y + r,
            outline=color, width=3,
        )
        label = self.canvas.create_text(
            display_x + 12, display_y - 12,
            text=f"{self.current_step+1}.{name}({orig_x},{orig_y})",
            fill=color, font=("Microsoft YaHei", 11, "bold"), anchor=tk.SW,
        )
        self.marker_ids.extend([dot, label])

        self.coordinates[key] = (orig_x, orig_y)
        self.current_step += 1
        self.canvas.itemconfig(self.banner_id, text=self._banner_text())
        self._refresh_ui()

        if self.current_step >= len(FIELDS):
            self.status_var.set("✓ 3 个位置已采集完成！按 Ctrl+S 保存到 coordinates.json")
        else:
            self.status_var.set(f"已采集【{name}】({orig_x}, {orig_y})，请继续点击下一个位置")

    def reset(self):
        for item_id in self.marker_ids:
            self.canvas.delete(item_id)
        self.marker_ids.clear()
        self.coordinates.clear()
        self.current_step = 0
        self.canvas.itemconfig(self.banner_id, text=self._banner_text())
        self._refresh_ui()
        self.status_var.set("已重置，请重新点击 3 个位置")

    def save_config(self):
        if len(self.coordinates) < len(FIELDS):
            if not messagebox.askyesno(
                "未完成", f"仅采集了 {len(self.coordinates)}/{len(FIELDS)} 个位置，确定保存？"
            ):
                return

        fields_dict = {}
        coords_simple = {}
        for key, name in FIELDS:
            if key in self.coordinates:
                x, y = self.coordinates[key]
                fields_dict[name] = {"key": key, "x": x, "y": y}
                coords_simple[key] = [x, y]

        config = {
            "template_image": os.path.abspath(self.image_path),
            "image_size": [self.img_w, self.img_h],
            "fields": fields_dict,
            "coordinates": coords_simple,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        self.status_var.set(f"✓ 已保存到 {CONFIG_FILE}")
        messagebox.showinfo(
            "保存成功",
            f"坐标配置已保存到：\n{CONFIG_FILE}\n\n"
            f"姓名:   {coords_simple.get('name')}\n"
            f"成绩:   {coords_simple.get('time')}\n"
            f"参赛号: {coords_simple.get('bib')}\n\n"
            "可运行 inject.py 批量生成证书。",
        )

    def _load_existing(self, silent=False):
        if not os.path.exists(CONFIG_FILE):
            if not silent:
                messagebox.showwarning("未找到", f"配置文件 {CONFIG_FILE} 不存在")
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            for item_id in self.marker_ids:
                self.canvas.delete(item_id)
            self.marker_ids.clear()
            self.coordinates.clear()

            coords = config.get("coordinates", {})
            for key, _ in FIELDS:
                if key in coords:
                    self.coordinates[key] = tuple(coords[key])
            self.current_step = sum(1 for k, _ in FIELDS if k in self.coordinates)

            for i, (key, name) in enumerate(FIELDS):
                if key in self.coordinates:
                    x, y = self.coordinates[key]
                    display_x = x * self.scale
                    display_y = y * self.scale
                    color = FIELD_COLORS[i]
                    r = 8
                    self.marker_ids.append(self.canvas.create_oval(
                        display_x - r, display_y - r, display_x + r, display_y + r,
                        outline=color, width=3,
                    ))
                    self.marker_ids.append(self.canvas.create_text(
                        display_x + 12, display_y - 12,
                        text=f"{i+1}.{name}({x},{y})",
                        fill=color, font=("Microsoft YaHei", 11, "bold"), anchor=tk.SW,
                    ))

            self.canvas.itemconfig(self.banner_id, text=self._banner_text())
            self._refresh_ui()
            if not silent:
                self.status_var.set("已加载现有配置")
        except Exception as e:
            if not silent:
                messagebox.showerror("加载失败", str(e))

    # ---------------- 工具方法 ----------------
    def _banner_text(self):
        if self.current_step < len(FIELDS):
            _, name = FIELDS[self.current_step]
            return f"第 {self.current_step + 1} 步：请在图片上点击【{name}】的下划线起点"
        return "✓ 3 个位置已采集完成，按 Ctrl+S 保存到 coordinates.json"

    def _make_progress_text(self):
        lines = [
            f"图片: {os.path.basename(self.image_path)}",
            f"尺寸: {self.img_w} x {self.img_h}",
        ]
        if self.scale < 1.0:
            lines.append(f"显示缩放: {self.scale:.2f}x")
        lines.append("-" * 24)
        for i, (key, name) in enumerate(FIELDS):
            if key in self.coordinates:
                x, y = self.coordinates[key]
                lines.append(f"  {i+1}. {name}: ({x}, {y})")
            else:
                lines.append(f"  {i+1}. {name}:  ·")
        return "\n".join(lines)

    def _refresh_ui(self):
        self.progress_var.set(self._make_progress_text())
        self.coord_listbox.delete(0, tk.END)
        for key, name in FIELDS:
            if key in self.coordinates:
                x, y = self.coordinates[key]
                self.coord_listbox.insert(tk.END, f"{name}: ({x}, {y})")
            else:
                self.coord_listbox.insert(tk.END, f"{name}: 未设置")

    def _on_mousewheel(self, event):
        delta = -1 if event.delta > 0 else 1
        if abs(event.delta) >= 120:
            delta = -int(event.delta / 120)
        self.canvas.yview_scroll(delta, "units")

    def _on_shift_mousewheel(self, event):
        delta = -1 if event.delta > 0 else 1
        if abs(event.delta) >= 120:
            delta = -int(event.delta / 120)
        self.canvas.xview_scroll(delta, "units")


def main():
    if len(sys.argv) >= 2:
        image_path = sys.argv[1]
        if not os.path.isfile(image_path):
            print(f"找不到文件: {image_path}")
            sys.exit(1)
    elif os.path.isfile(DEFAULT_TEMPLATE):
        image_path = DEFAULT_TEMPLATE
    else:
        root = tk.Tk()
        root.withdraw()
        image_path = filedialog.askopenfilename(
            title="选择证书模板图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp"),
                       ("所有文件", "*.*")],
        )
        root.destroy()
        if not image_path:
            print("未选择图片，程序退出。")
            sys.exit(0)

    print(f"打开图片: {image_path}")
    root = tk.Tk()
    ThreeStepCoordPicker(root, image_path)
    root.mainloop()


if __name__ == "__main__":
    main()
