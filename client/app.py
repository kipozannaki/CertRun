"""
完赛证书查询系统 · 客户端
=========================
仅实现：姓名 + 参赛号 → 查询/下载完赛证书。
仅依赖：Flask、PIL（核心查询逻辑只读文件系统，不依赖 PIL）。

启动：python app.py
访问：http://127.0.0.1:5000
"""

import os

from flask import Flask, jsonify, render_template, request, send_file

from core import (
    ALLOWED_IMG_EXTS,
    CERT_DIR,
    CLIENT_PORT,
    ensure_cert_dir,
    find_certificate,
)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
)


@app.route("/")
def index():
    """渲染查询首页"""
    return render_template("index.html")


@app.route("/api/certificate")
def api_certificate():
    """
    公开查询接口：/api/certificate?name=姓名&bib=参赛号
    找到则直接返回图片，否则返回 404 + JSON 错误。
    """
    name = request.args.get("name", "").strip()
    bib = request.args.get("bib", "").strip()
    if not name or not bib:
        return jsonify({"ok": False, "msg": "请填写姓名和参赛号"}), 400

    file_path = find_certificate(name, bib)
    if not file_path:
        return jsonify({
            "ok": False,
            "msg": f"未找到 姓名「{name}」 参赛号「{bib}」 的完赛证书，请检查输入是否正确",
        }), 404

    ext = os.path.splitext(file_path)[1].lower()
    mime = {
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    return send_file(file_path, mimetype=mime)


if __name__ == "__main__":
    ensure_cert_dir()
    print("=" * 60)
    print("  完赛证书查询系统 · 客户端")
    print("=" * 60)
    print(f"  共享证书目录: {CERT_DIR}")
    print(f"  端口:         {CLIENT_PORT}")
    print(f"  访问地址:     http://127.0.0.1:{CLIENT_PORT}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)
    app.run(host="0.0.0.0", port=CLIENT_PORT, debug=False)
