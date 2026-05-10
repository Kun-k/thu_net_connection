# -*- coding: utf-8 -*-
"""浏览器查看与管理模块 (Flask)。

提供与 manage.py 等价的功能：
  - 状态查看
  - 凭证 CRUD
  - 服务启动 / 停止

注意: 服务启停涉及 sudo 时, 终端 (运行 manage.py 的窗口) 可能弹出密码提示。
"""

import hmac
import os
import shlex
import socket
import subprocess

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    session,
    redirect,
    url_for,
)


def _read_log_tail(path, n=200):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            block = 4096
            data = b""
            while size > 0 and data.count(b"\n") <= n:
                step = min(block, size)
                size -= step
                f.seek(size)
                data = f.read(step) + data
            lines = data.decode("utf-8", errors="replace").splitlines()
            return "\n".join(lines[-n:])
    except Exception as e:
        return f"(读取日志失败: {e})"


def _local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def _public_ip():
    for cmd in ("curl -s --max-time 3 ifconfig.me", "curl -s --max-time 3 ip.cn"):
        try:
            r = subprocess.run(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4,
            )
            if r.returncode == 0:
                txt = r.stdout.strip()
                if txt:
                    return txt
        except Exception:
            continue
    return ""


def create_app(access_key, project_dir, get_state, ops):
    app = Flask(
        __name__,
        template_folder=os.path.join(project_dir, "templates"),
        static_folder=os.path.join(project_dir, "static"),
    )
    app.secret_key = os.urandom(32)

    def authed():
        return session.get("ok") is True

    def require_auth():
        if not authed():
            return jsonify({"error": "unauthorized"}), 401
        return None

    @app.route("/", methods=["GET"])
    def index():
        if not authed():
            return redirect(url_for("login"))
        return render_template("index.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            given = (request.form.get("key") or "").strip()
            if hmac.compare_digest(given, access_key):
                session["ok"] = True
                return redirect(url_for("index"))
            error = "密钥错误."
        return render_template("login.html", error=error)

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---- API ----
    @app.route("/api/status")
    def api_status():
        if (r := require_auth()):
            return r
        state, encrypt = get_state()
        log_path = os.path.join(project_dir, "auto_login.log")
        return jsonify({
            "service_state": state,
            "encrypt": encrypt,
            "local_ip": _local_ip(),
            "public_ip": _public_ip(),
            "log_tail": _read_log_tail(log_path, 200),
        })

    @app.route("/api/creds", methods=["GET"])
    def api_creds_list():
        if (r := require_auth()):
            return r
        return jsonify(ops["list_creds"]())

    @app.route("/api/creds/<name>", methods=["GET"])
    def api_cred_view(name):
        if (r := require_auth()):
            return r
        cfg = ops["view_cred"](name)
        if cfg is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(cfg)

    @app.route("/api/creds", methods=["POST"])
    def api_cred_create():
        if (r := require_auth()):
            return r
        data = request.get_json(silent=True) or {}
        try:
            fname = ops["create_cred"](data)
        except Exception as e:
            return jsonify({"error": "create_failed", "detail": str(e)}), 400
        return jsonify({"ok": True, "filename": fname})

    @app.route("/api/creds/<name>", methods=["PUT"])
    def api_cred_update(name):
        if (r := require_auth()):
            return r
        body = request.get_json(silent=True) or {}
        action = (body.pop("_action", None) or "default")
        ok, msg = ops["update_cred"](name, body, action=action)
        status = 200 if ok else (409 if msg == "in_use" else 400)
        return jsonify({"ok": ok, "msg": msg}), status

    @app.route("/api/creds/<name>", methods=["DELETE"])
    def api_cred_delete(name):
        if (r := require_auth()):
            return r
        action = request.args.get("action", "default")
        ok, msg = ops["delete_cred"](name, action=action)
        status = 200 if ok else (409 if msg == "in_use" else 400)
        return jsonify({"ok": ok, "msg": msg}), status

    @app.route("/api/service/start", methods=["POST"])
    def api_service_start():
        if (r := require_auth()):
            return r
        body = request.get_json(silent=True) or {}
        cred = (body.get("cred_name") or "").strip()
        if not cred:
            return jsonify({"ok": False, "msg": "missing_cred"}), 400
        ok, msg = ops["start_service"](cred)
        return jsonify({"ok": ok, "msg": msg}), (200 if ok else 400)

    @app.route("/api/service/stop", methods=["POST"])
    def api_service_stop():
        if (r := require_auth()):
            return r
        ok, msg = ops["stop_service"]()
        return jsonify({"ok": ok, "msg": msg}), (200 if ok else 400)

    return app
