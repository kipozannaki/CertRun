"""
完赛证书批量生成器（CLI 工具）
=============================
读取本目录下的 coordinates.json + 参赛成绩.xlsx，
在 template.jpg 上批量生成完赛证书，输出到父目录的 certificates/（共享）。

使用（在 admin/ 目录下）：
    python inject.py
"""

import json
import os

import openpyxl
from PIL import Image, ImageDraw, ImageFont

# ============== 路径配置（基于本文件所在目录） ==============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.dirname(BASE_DIR)              # 父目录（与 client/ 同级）
CONFIG_FILE = os.path.join(BASE_DIR, "coordinates.json")
DATA_FILE = os.path.join(BASE_DIR, "参赛成绩.xlsx")
# 模板路径可由配置文件覆盖，默认取本目录
DEFAULT_TEMPLATE = os.path.join(BASE_DIR, "template.jpg")
OUTPUT_DIR = os.path.join(SHARED_DIR, "certificates")  # 共享目录
FONT_PATH = os.path.join(BASE_DIR, "msyhbd.ttc")

# ============== 文字样式 ==============
TEXT_COLOR = (28, 55, 131)
FONT_SIZE = 42
# 文字相对下划线起点的偏移
TEXT_OFFSET_X = 10
TEXT_OFFSET_Y = -32


def load_config():
    """加载坐标配置文件"""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        coords = config.get("coordinates", {})
        for key in ("name", "time", "bib"):
            if key not in coords:
                print(f"❌ 配置文件中缺少【{key}】坐标，请重新运行 pick_coords.py")
                return None
        return config
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件格式错误: {e}")
        return None


def load_data_from_xlsx(file_path):
    """从 xlsx 读取 (姓名, 参赛号, 成绩)"""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        name, bib, score = row[0], row[1], row[2]
        if not name or bib is None or not score:
            continue
        data.append((str(name), str(bib), str(score)))
    workbook.close()
    return data


def calc_text_pos(coord):
    """下划线坐标 → 文字实际写入坐标（应用偏移）"""
    return (coord[0] + TEXT_OFFSET_X, coord[1] + TEXT_OFFSET_Y)


def generate_certificates(template_path, records, coords, output_dir):
    """根据模板和数据生成所有证书"""
    os.makedirs(output_dir, exist_ok=True)
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except IOError:
        print(f"❌ 未找到字体文件 {FONT_PATH}")
        return 0, []

    name_pos = calc_text_pos(coords["name"])
    time_pos = calc_text_pos(coords["time"])
    bib_pos  = calc_text_pos(coords["bib"])

    output_files = []
    for name, bib, score in records:
        with Image.open(template_path) as img:
            draw = ImageDraw.Draw(img)
            draw.text(name_pos, name, fill=TEXT_COLOR, font=font)
            draw.text(time_pos, score, fill=TEXT_COLOR, font=font)
            draw.text(bib_pos,  bib,   fill=TEXT_COLOR, font=font)
            output_path = os.path.join(output_dir, f"{bib}_{name}_完赛证书.png")
            img.save(output_path, "PNG")
            output_files.append(output_path)
            print(f"  ✓ {bib}_{name}_完赛证书.png")
    return len(output_files), output_files


def main():
    print("=" * 56)
    print("  完赛证书批量生成器（管理端）")
    print("=" * 56)

    config = load_config()
    if not config:
        print(f"\n❌ 未找到或无效的配置文件: {CONFIG_FILE}")
        print("   请先运行 pick_coords.py 拾取 3 个字段的坐标。")
        return

    template = config.get("template_image", DEFAULT_TEMPLATE)
    coords = config["coordinates"]
    print(f"\n模板图片: {template}")
    print(f"  姓名   下划线起点: {tuple(coords['name'])} → 文字写入: {calc_text_pos(coords['name'])}")
    print(f"  成绩   下划线起点: {tuple(coords['time'])} → 文字写入: {calc_text_pos(coords['time'])}")
    print(f"  参赛号 下划线起点: {tuple(coords['bib'])}  → 文字写入: {calc_text_pos(coords['bib'])}")

    if not os.path.isfile(template):
        print(f"\n❌ 模板图片不存在: {template}")
        return

    try:
        records = load_data_from_xlsx(DATA_FILE)
    except FileNotFoundError:
        print(f"\n❌ 数据文件不存在: {DATA_FILE}")
        return

    print(f"\n共读取 {len(records)} 条参赛数据，开始生成证书...")
    print("-" * 56)

    count, _ = generate_certificates(template, records, coords, OUTPUT_DIR)

    print("-" * 56)
    print(f"\n✅ 完成！共生成 {count} 张证书，存放在 {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
