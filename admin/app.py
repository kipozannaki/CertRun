"""
完赛证书生成系统 · 管理端
=========================
三分步坐标拾取 + 批量生成证书。生成的证书直接写入共享 certificates/ 目录，
客户端可立即查询。

启动：python app.py
访问：http://127.0.0.1:5001
"""

import io
import os
import shutil
import tempfile
import zipfile

from flask import Flask, abort, jsonify, render_template, request, send_file

from core import (
    ADMIN_PORT,
    CERT_DIR,
    FONT_PATH,
    ensure_cert_dir,
    generate_certificates,
    read_xlsx_records,
)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 单次上传最大 50MB


@app.route("/")
def admin():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    批量生成证书接口（multipart/form-data）：
      - template:  模板图片
      - xlsx:      成绩 Excel
      - name_x, name_y: 姓名下划线起点
      - time_x, time_y: 成绩下划线起点
      - bib_x,  bib_y:  参赛号下划线起点
    返回 JSON: {ok, count, zip_url, files:[{name,url,size}]}
    """
    if "template" not in request.files or "xlsx" not in request.files:
        return jsonify({"ok": False, "msg": "请上传模板和 Excel"}), 400
    try:
        coords = {
            "name": [int(request.form["name_x"]), int(request.form["name_y"])],
            "time": [int(request.form["time_x"]), int(request.form["time_y"])],
            "bib":  [int(request.form["bib_x"]),  int(request.form["bib_y"])],
        }
    except (KeyError, ValueError):
        return jsonify({"ok": False, "msg": "坐标参数不完整或不是数字"}), 400

    template_file = request.files["template"]
    xlsx_file = request.files["xlsx"]

    # 模板存到临时目录，避免污染证书目录
    temp_dir = tempfile.mkdtemp(prefix="cert_gen_")
    try:
        ext = os.path.splitext(template_file.filename)[1].lower() or ".jpg"
        template_path = os.path.join(temp_dir, "template" + ext)
        template_file.save(template_path)

        try:
            records = read_xlsx_records(xlsx_file)
        except Exception as e:
            return jsonify({"ok": False, "msg": f"读取 Excel 失败: {e}"}), 400
        if not records:
            return jsonify({"ok": False, "msg": "Excel 中没有有效数据"}), 400

        try:
            outputs = generate_certificates(template_path, records, coords, CERT_DIR)
        except Exception as e:
            return jsonify({"ok": False, "msg": f"生成失败: {e}"}), 500

        files = []
        for path in outputs:
            name = os.path.basename(path)
            files.append({
                "name": name,
                "url":  f"/api/cert/{name}",
                "size": os.path.getsize(path),
            })
        return jsonify({
            "ok": True,
            "count": len(files),
            "zip_url": "/api/zip",
            "files": files,
        })
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route("/api/cert/<filename>")
def api_cert(filename):
    """下载单张证书（从共享目录）"""
    if "/" in filename or "\\" in filename or ".." in filename:
        abort(400)
    file_path = os.path.join(CERT_DIR, filename)
    if not os.path.isfile(file_path):
        abort(404)
    return send_file(file_path, mimetype="image/png", as_attachment=True,
                     download_name=filename)


@app.route("/api/zip")
def api_zip():
    """把共享证书目录下所有证书打成 zip 下载"""
    if not os.path.isdir(CERT_DIR):
        abort(404)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in os.listdir(CERT_DIR):
            full = os.path.join(CERT_DIR, filename)
            if os.path.isfile(full) and filename.lower().endswith((".png", ".jpg", ".jpeg")):
                zf.write(full, filename)
    memory_file.seek(0)
    return send_file(memory_file, mimetype="application/zip", as_attachment=True,
                     download_name="certificates.zip")


if __name__ == "__main__":
    ensure_cert_dir()
    print("=" * 60)
    print("  完赛证书生成系统 · 管理端")
    print("=" * 60)
    print(f"  共享证书目录: {CERT_DIR}  （生成的证书会写入这里）")
    print(f"  字体文件:     {FONT_PATH}")
    print(f"  端口:         {ADMIN_PORT}")
    print(f"  访问地址:     http://127.0.0.1:{ADMIN_PORT}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)
    app.run(host="0.0.0.0", port=ADMIN_PORT, debug=False)
