"""
客户端核心配置与查询工具
========================
仅包含客户端需要的代码：查询路径配置、索引加载、查询接口辅助。
"""
import json
import logging
import os
import threading

# 客户端项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 共享目录 = 父目录（与 admin/ 同级）
SHARED_DIR = os.path.dirname(BASE_DIR)
# 共享证书目录
CERT_DIR = os.path.join(SHARED_DIR, "certificates")
# 索引文件（管理端生成时同步写入，客户端优先使用以实现 O(1) 查询）
INDEX_FILE = os.path.join(CERT_DIR, "index.json")
# 支持的图片后缀
ALLOWED_IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
# 客户端端口
CLIENT_PORT = 5000

logger = logging.getLogger("client.core")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# 索引文件 mtime 缓存：避免每查一次都重读 index.json
_index_mtime: float = 0.0
_index_cache: dict = {}
_index_lock = threading.Lock()


def _is_safe_key(s: str) -> bool:
    """
    拒绝含路径分隔符、控制字符、'..' 的输入，防止上层拼接后访问到
    CERT_DIR 之外的文件。汉字/字母/数字/常见符号都允许。
    """
    if not s:
        return False
    bad = ('..', '/', '\\', '\x00', '\n', '\r')
    return not any(b in s for b in bad)


def _load_index() -> dict:
    """
    加载 index.json 并缓存。
    返回 {"<bib>_<name>": "<filename>", ...}；文件不存在/损坏时返回 {}。
    缓存基于 mtime：管理端更新索引后，客户端下次查询会自然失效。
    """
    global _index_mtime, _index_cache
    with _index_lock:
        try:
            mtime = os.path.getmtime(INDEX_FILE) if os.path.isfile(INDEX_FILE) else 0.0
        except OSError:
            mtime = 0.0
        if mtime == _index_mtime and _index_cache:
            return _index_cache
        if not os.path.isfile(INDEX_FILE):
            _index_mtime, _index_cache = 0.0, {}
            return _index_cache
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", {}) if isinstance(data, dict) else {}
            # 过滤指向不存在文件的死链
            items = {k: v for k, v in items.items()
                     if isinstance(v, str)
                     and os.path.isfile(os.path.join(CERT_DIR, v))}
            _index_mtime, _index_cache = mtime, items
            logger.info("加载证书索引，共 %d 条", len(items))
            return items
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("index.json 读取失败（将回退到目录扫描）: %s", e)
            _index_mtime, _index_cache = mtime, {}
            return _index_cache


def _find_by_scan(name: str, bib: str):
    """
    兜底方案：当 index.json 不可用时，遍历 CERT_DIR 全量匹配。
    复杂度 O(N)，仅在索引缺失的过渡期触发，正常情况不会走这里。
    """
    if not os.path.isdir(CERT_DIR):
        return None
    expected_prefix = f"{bib}_{name}_"
    for filename in os.listdir(CERT_DIR):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_IMG_EXTS:
            continue
        stem = os.path.splitext(filename)[0]
        if stem.startswith(expected_prefix) and "完赛证书" in stem:
            return os.path.join(CERT_DIR, filename)
    return None


def find_certificate(name: str, bib: str):
    """
    优先走 index.json（O(1)）；索引缺失/损坏时回退到目录扫描。
    返回证书的绝对路径或 None。
    """
    name = (name or "").strip()
    bib = (bib or "").strip()
    if not name or not bib:
        return None
    if not _is_safe_key(name) or not _is_safe_key(bib):
        return None

    items = _load_index()
    if items:
        filename = items.get(f"{bib}_{name}")
        if filename and os.path.isfile(os.path.join(CERT_DIR, filename)):
            return os.path.join(CERT_DIR, filename)
        # 索引里有但文件已被删 → 视为未找到
        if items:
            return None

    # 索引为空时回退扫描
    return _find_by_scan(name, bib)


def ensure_cert_dir():
    """确保共享证书目录存在"""
    os.makedirs(CERT_DIR, exist_ok=True)
