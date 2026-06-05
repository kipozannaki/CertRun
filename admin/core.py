"""
管理端核心配置与生成工具
========================
仅包含管理端需要的代码：生成路径、字体、xlsx 读取、生成证书、索引维护。
"""
import io
import json
import logging
import os
from datetime import datetime, timezone

import openpyxl
from PIL import Image, ImageDraw, ImageFont

# 管理端项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 共享目录 = 父目录（与 client/ 同级）
SHARED_DIR = os.path.dirname(BASE_DIR)
# 共享证书目录（生成的证书写入这里，客户端从这里读取）
CERT_DIR = os.path.join(SHARED_DIR, "certificates")
# 索引文件名（与证书同目录，客户端读取以实现 O(1) 查询）
INDEX_FILE = os.path.join(CERT_DIR, "index.json")
# 字体文件（管理端专用）
FONT_PATH = os.path.join(BASE_DIR, "msyhbd.ttc")
# 支持的图片后缀
ALLOWED_IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# 文字样式
TEXT_COLOR = (28, 55, 131)
FONT_SIZE = 42
# 文字相对下划线起点的偏移：x+10 留空白，y-32 让 42 号字垂直居中
TEXT_OFFSET_X = 10
TEXT_OFFSET_Y = -32

# 管理端端口
ADMIN_PORT = 5001

# 单次 xlsx 解析的最大有效记录数（防 OOM / 防误传巨型表）
MAX_XLSX_ROWS = 10000

# 标准日志：替代散落的 print
logger = logging.getLogger("admin.core")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def ensure_cert_dir():
    """确保共享证书目录存在"""
    os.makedirs(CERT_DIR, exist_ok=True)


# ============== 索引 ==============
def _load_index() -> dict:
    """
    读取 index.json。返回 {"version": 1, "items": {"<bib>_<name>": "<filename>", ...}}。
    文件不存在或损坏时返回空索引，不抛异常（保证服务可用性）。
    """
    if not os.path.isfile(INDEX_FILE):
        return {"version": 1, "items": {}}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "items" not in data:
            return {"version": 1, "items": {}}
        # 过滤掉指向已不存在文件的死链
        items = data.get("items", {})
        items = {k: v for k, v in items.items()
                 if isinstance(v, str) and os.path.isfile(os.path.join(CERT_DIR, v))}
        return {"version": 1, "items": items}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("index.json 读取失败（将重建）: %s", e)
        return {"version": 1, "items": {}}


def _save_index(index: dict) -> None:
    """原子写 index.json：先写临时文件再 rename，避免半写状态被客户端读取"""
    index = dict(index)
    index["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tmp_path = INDEX_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp_path, INDEX_FILE)


# ============== 数据读取 ==============
def read_xlsx_records(file_storage, max_rows: int = MAX_XLSX_ROWS) -> list:
    """
    从 werkzeug FileStorage 读取 (姓名, 参赛号, 成绩) 记录。
    期望列：姓名 | 参赛号 | 成绩（首行表头）。

    限制：最多读取 max_rows 条有效记录，超出抛 ValueError 提示用户。
    """
    in_memory = io.BytesIO(file_storage.read())
    workbook = openpyxl.load_workbook(in_memory, read_only=True, data_only=True)
    sheet = workbook.active
    records = []
    try:
        for row in sheet.iter_rows(min_row=2, max_col=3, values_only=True):
            if len(records) >= max_rows:
                raise ValueError(f"Excel 数据超过 {max_rows} 条上限，请拆分后再上传")
            name, bib, score = row[0], row[1], row[2]
            # 严格过滤：None / 空字符串 / 数字 0（成绩为 0 不合理）
            if name is None or bib is None or score in (None, "", 0):
                continue
            records.append((str(name).strip(), str(bib).strip(), str(score).strip()))
    finally:
        workbook.close()
    return records


# ============== 证书生成 ==============
def generate_certificates(template_path, records, coords, output_dir,
                          font_path: str = FONT_PATH,
                          font_size: int = FONT_SIZE) -> list:
    """
    根据模板和数据生成证书到指定目录。
    coords: {"name":[x,y], "time":[x,y], "bib":[x,y]}  （下划线起点坐标）
    返回生成的 PNG 文件路径列表，并同步更新共享 index.json。

    性能优化：模板 Image.open 仅执行一次（之前在循环内每条记录 open 一次，
    500 条记录浪费 25~40 秒），每条记录基于 base.copy() 绘制后保存。
    """
    os.makedirs(output_dir, exist_ok=True)
    if not records:
        return []

    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        raise RuntimeError(f"未找到字体文件 {font_path}")

    name_pos = (coords["name"][0] + TEXT_OFFSET_X, coords["name"][1] + TEXT_OFFSET_Y)
    time_pos = (coords["time"][0] + TEXT_OFFSET_X, coords["time"][1] + TEXT_OFFSET_Y)
    bib_pos  = (coords["bib"][0]  + TEXT_OFFSET_X, coords["bib"][1]  + TEXT_OFFSET_Y)

    # 模板只 decode 一次；PIL 在 save() 后 base 仍可继续 copy()
    with Image.open(template_path) as base:
        # 一些 JPG 不支持 RGBA 复制，统一转为 RGB 提升 copy/save 稳定性
        if base.mode not in ("RGB", "RGBA"):
            base = base.convert("RGB")
        # 预先把字体绑到 Draw 工厂里省一次属性查找（每条记录都创建 Draw）
        outputs = []
        for name, bib, score in records:
            img = base.copy()
            draw = ImageDraw.Draw(img)
            draw.text(name_pos, name, fill=TEXT_COLOR, font=font)
            draw.text(time_pos, score, fill=TEXT_COLOR, font=font)
            draw.text(bib_pos,  bib,   fill=TEXT_COLOR, font=font)
            out_path = os.path.join(output_dir, f"{bib}_{name}_完赛证书.png")
            img.save(out_path, "PNG")
            outputs.append(out_path)

    # 同步更新索引（不抛异常：索引失败不影响证书生成结果）
    try:
        index = _load_index()
        for name, bib, _score in records:
            index["items"][f"{bib}_{name}"] = f"{bib}_{name}_完赛证书.png"
        _save_index(index)
    except Exception as e:
        logger.warning("更新 index.json 失败（不影响证书本身）: %s", e)

    return outputs
