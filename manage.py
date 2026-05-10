# -*- coding: utf-8 -*-
"""
校园网自动登陆 一键管理工具

菜单：
    0  自动执行（首次运行时复制 auth-client / .auth-setting 到 ~ 并赋权）
    1  管理凭证 (encrypt) 增/删/改/查
    2  查看服务状态
    3  启动服务 (并开机自启动)
    4  关闭服务 (并取消开机自启动)
    5  在浏览器查看
    6  退出
"""

import getpass
import os
import secrets
import shutil
import socket
import stat
import subprocess
import sys

from encrypt_cred import EncryptCred, CRED_DIR


PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
SERVICE_NAME = "auto_login.service"
SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}"
AUTH_CLIENT_SRC = os.path.join(PROJECT_DIR, "TunetZRRZ2025_linux", "Tunet_linux2025", "auth-client")
AUTH_SETTING_SRC = os.path.join(PROJECT_DIR, "TunetZRRZ2025_linux", "Tunet_linux2025", ".auth-setting")
AUTOSTART_NAME_FILE = os.path.join(CRED_DIR, ".ConfigNameAutoStart")
ACCESS_KEY_FILE = os.path.join(CRED_DIR, ".access_key")
AUTOSTART_SH = os.path.join(PROJECT_DIR, "sh_run_auto_login_autostart.sh")


# ---------- 工具函数 ----------
def is_linux():
    return sys.platform.startswith("linux")


def clear_screen():
    """清空当前终端，使每次功能显示更清爽。"""
    os.system("cls" if os.name == "nt" else "clear")


def pause(msg="按回车返回菜单..."):
    try:
        input(f"\n{msg}")
    except (EOFError, KeyboardInterrupt):
        pass


def try_copy_to_clipboard(text):
    """尝试将文本复制到系统剪贴板, 返回是否成功。"""
    candidates = []
    if sys.platform == "darwin":
        candidates.append(["pbcopy"])
    elif os.name == "nt":
        candidates.append(["clip"])
    else:
        candidates.append(["xclip", "-selection", "clipboard"])
        candidates.append(["xsel", "--clipboard", "--input"])
        candidates.append(["wl-copy"])
    for cmd in candidates:
        try:
            p = subprocess.run(cmd, input=text, text=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if p.returncode == 0:
                return True, cmd[0]
        except FileNotFoundError:
            continue
    return False, None


def run_sudo(args, input_text=None, capture=False):
    """执行需要 sudo 的命令；如果用户已经是 root 则直接执行。"""
    if os.geteuid() == 0 if hasattr(os, "geteuid") else False:
        cmd = list(args)
    else:
        cmd = ["sudo"] + list(args)
    try:
        if capture:
            return subprocess.run(
                cmd, input=input_text, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        return subprocess.run(cmd, input=input_text, text=True)
    except FileNotFoundError as e:
        print(f"命令执行失败: {e}")
        return None


def sudo_write_file(path, content):
    """以 sudo 身份写入文件内容（通过 tee）。"""
    proc = run_sudo(["tee", path], input_text=content, capture=True)
    if proc is None or proc.returncode != 0:
        print(f"写入 {path} 失败.")
        return False
    return True


def systemctl(*args, capture=False):
    return run_sudo(["systemctl", *args], capture=capture)


# ---------- 步骤 0 ----------
def step0_done():
    home = os.path.expanduser("~")
    client = os.path.join(home, "auth-client")
    setting = os.path.join(home, ".auth-setting")
    return (
        os.path.exists(client)
        and os.path.exists(setting)
        and os.access(client, os.X_OK)
    )


def step0_setup():
    if step0_done():
        return
    print("[步骤0] 复制 auth-client 与 .auth-setting 到用户目录并赋予执行权限...")
    home = os.path.expanduser("~")
    if not os.path.exists(AUTH_CLIENT_SRC) or not os.path.exists(AUTH_SETTING_SRC):
        print(f"  缺少源文件: {AUTH_CLIENT_SRC} 或 {AUTH_SETTING_SRC}")
        return
    shutil.copy2(AUTH_CLIENT_SRC, os.path.join(home, "auth-client"))
    shutil.copy2(AUTH_SETTING_SRC, os.path.join(home, ".auth-setting"))
    client = os.path.join(home, "auth-client")
    st = os.stat(client)
    os.chmod(client, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("[步骤0] 完成.")


# ---------- 服务状态 ----------
def get_service_state():
    """返回 (state, encrypt_filename)
    state ∈ {"not-installed", "active", "inactive", "failed", ...}
    """
    if not os.path.exists(SERVICE_PATH):
        return "not-installed", None
    encrypt = None
    if os.path.exists(AUTOSTART_NAME_FILE):
        with open(AUTOSTART_NAME_FILE) as f:
            encrypt = f.read().strip()
    if not is_linux():
        return "unknown", encrypt
    try:
        r = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        return (r.stdout.strip() or "unknown"), encrypt
    except Exception:
        return "unknown", encrypt


def is_service_active():
    state, _ = get_service_state()
    return state == "active"


# ---------- 凭证管理 ----------
def _select_cred(prompt="请选择凭证(序号): "):
    creds = EncryptCred.list_creds()
    if not creds:
        print("没有已保存的凭证.")
        return None
    if len(creds) == 1:
        print(f"仅有一个凭证: {creds[0]}")
        return creds[0]
    for i, c in enumerate(creds, 1):
        print(f"  {i}. {c}")
    while True:
        try:
            idx = int(input(prompt).strip())
            if 1 <= idx <= len(creds):
                return creds[idx - 1]
        except Exception:
            pass
        print("输入无效.")


def add_encrypt():
    EncryptCred().save_cred()


def view_encrypt():
    cred = _select_cred("请选择要查看的凭证: ")
    if not cred:
        return
    confirm = input(
        f"查看 {cred} 将显示账户/邮箱等敏感信息, 确认查看? (y/N): "
    ).strip().lower()
    if confirm != "y":
        print("已取消.")
        return
    ok, cfg = EncryptCred.load_cred(cred)
    if not ok:
        return
    print("-" * 40)
    for k, v in cfg.items():
        print(f"  {k}: {v}")
    print("-" * 40)


def edit_encrypt():
    cred = _select_cred("请选择要编辑的凭证: ")
    if not cred:
        return
    state, current = get_service_state()
    if state == "active" and current == cred:
        print(f"\n凭证 {cred} 正被运行中的服务使用：")
        print("  1) 不编辑")
        print("  2) 编辑并重启服务")
        print("  3) 编辑但不重启服务（当前 encrypt 已被写入后台）")
        print("  4) 编辑并终止服务")
        c = input("请选择: ").strip()
        if c == "1":
            return
        if c not in ("2", "3", "4"):
            print("输入无效.")
            return
        if not EncryptCred.update_cred(cred):
            return
        if c == "2":
            print("正在重启服务...")
            systemctl("restart", SERVICE_NAME)
        elif c == "4":
            _stop_and_disable()
    else:
        EncryptCred.update_cred(cred)


def delete_encrypt():
    cred = _select_cred("请选择要删除的凭证: ")
    if not cred:
        return
    state, current = get_service_state()
    if state == "active" and current == cred:
        print(f"\n凭证 {cred} 正被运行中的服务使用：")
        print("  1) 不删除")
        print("  2) 删除并终止服务")
        print("  3) 删除但不终止服务（当前 encrypt 已被写入后台）")
        c = input("请选择: ").strip()
        if c == "1":
            return
        if c not in ("2", "3"):
            print("输入无效.")
            return
        EncryptCred.delete_cred(cred)
        if c == "2":
            _stop_and_disable()
        else:
            print("已删除文件，但服务仍在后台运行（直到下次重启/手动停止）.")
    else:
        confirm = input(f"确认删除 {cred}? (y/N): ").strip().lower()
        if confirm == "y":
            EncryptCred.delete_cred(cred)
            print("已删除.")


def manage_encrypt():
    while True:
        clear_screen()
        print("=== 管理凭证 ===\n")
        creds = EncryptCred.list_creds()
        print(f"当前共有 {len(creds)} 个凭证.\n")
        print("  1) 添加")
        print("  2) 查看")
        print("  3) 编辑")
        print("  4) 删除")
        print("  5) 返回主菜单")
        try:
            c = input("\n请选择: ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if c == "5":
            return
        clear_screen()
        try:
            if c == "1":
                print("=== 添加凭证 ===\n")
                add_encrypt()
            elif c == "2":
                print("=== 查看凭证 ===\n")
                if not creds:
                    print("当前没有任何凭证.")
                else:
                    view_encrypt()
            elif c == "3":
                print("=== 编辑凭证 ===\n")
                if not creds:
                    print("当前没有任何凭证.")
                else:
                    edit_encrypt()
            elif c == "4":
                print("=== 删除凭证 ===\n")
                if not creds:
                    print("当前没有任何凭证.")
                else:
                    delete_encrypt()
            else:
                print("输入无效.")
        except (KeyboardInterrupt, EOFError):
            print("\n已中止当前操作.")
        pause()


# ---------- 服务管理 ----------
def view_service_status():
    state, encrypt = get_service_state()
    if state == "not-installed":
        print("没有服务在运行 (auto_login.service 未安装).")
        return
    print(f"服务状态: {state}")
    print(f"使用的凭证: {encrypt}")
    if is_linux():
        subprocess.call(["systemctl", "--no-pager", "status", SERVICE_NAME])


def _generate_access_key():
    os.makedirs(CRED_DIR, exist_ok=True)
    key = secrets.token_urlsafe(24)
    with open(ACCESS_KEY_FILE, "w") as f:
        f.write(key)
    try:
        os.chmod(ACCESS_KEY_FILE, 0o600)
    except Exception:
        pass
    return key


def _write_autostart_sh(python_path):
    content = (
        "#!/usr/bin/env bash\n"
        "\n"
        f'exec "{python_path}" run_auto_login_autostart.py\n'
    )
    try:
        with open(AUTOSTART_SH, "w", newline="\n") as f:
            f.write(content)
        os.chmod(AUTOSTART_SH, 0o755)
        return True
    except PermissionError:
        # 文件可能被 root 拥有（例如先前以 sudo 运行过），回退到 sudo 写入并修正归属。
        print(f"普通用户无写权限, 尝试使用 sudo 写入 {AUTOSTART_SH} ...")
        if not sudo_write_file(AUTOSTART_SH, content):
            return False
        user = getpass.getuser()
        run_sudo(["chown", f"{user}:{user}", AUTOSTART_SH])
        run_sudo(["chmod", "755", AUTOSTART_SH])
        return True


def _build_service_unit(user, workdir, exec_path):
    return (
        "[Unit]\n"
        "Description=Auto Login Service\n"
        "After=network.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={exec_path}\n"
        "Restart=always\n"
        f"User={user}\n"
        f"WorkingDirectory={workdir}\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def _start_and_enable():
    systemctl("daemon-reexec")
    systemctl("daemon-reload")
    systemctl("enable", SERVICE_NAME)
    systemctl("start", SERVICE_NAME)


def _stop_and_disable():
    systemctl("stop", SERVICE_NAME)
    systemctl("disable", SERVICE_NAME)
    run_sudo(["rm", "-f", SERVICE_PATH])
    systemctl("daemon-reload")
    print("服务已关闭并取消开机自启.")


def _resolve_python_path(candidate):
    """尝试把一个可能写错的 PythonPath 解析为可执行的绝对路径。
    返回 (ok, resolved_path_or_reason)。
    """
    if not candidate:
        candidate = "python"
    # 绝对路径且可执行
    if os.path.isabs(candidate) and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return True, candidate
    # 交给 shutil.which 在 PATH 里找
    found = shutil.which(candidate)
    if found:
        return True, found
    return False, candidate


def _prompt_python_path(default_hint=None):
    """在终端让用户重新输入 python 路径；自动建议一个可行的候选。"""
    suggestion = None
    for cand in ("python3", "python"):
        found = shutil.which(cand)
        if found:
            suggestion = found
            break
    tip = f" (建议: {suggestion})" if suggestion else ""
    while True:
        val = input(f"请输入可执行的 Python 路径{tip}, 留空使用建议: ").strip()
        if not val:
            val = suggestion or ""
        ok, resolved = _resolve_python_path(val)
        if ok:
            return resolved
        print(f"  '{val}' 不存在或不可执行, 请重试.")


def _setup_service_with(cred):
    ok, cfg = EncryptCred.load_cred(cred)
    if not ok:
        print("无法加载凭证.")
        return False
    python_path = cfg.get("PythonPath") or "python"

    resolved_ok, resolved = _resolve_python_path(python_path)
    if not resolved_ok:
        print(f"凭证中的 PythonPath '{python_path}' 不可用 (文件不存在或不可执行).")
        resolved = _prompt_python_path()
        # 写回凭证, 方便下次使用
        try:
            EncryptCred.update_cred_from_dict(cred, {"PythonPath": resolved})
            print(f"已将凭证 {cred} 的 PythonPath 更新为: {resolved}")
        except Exception as e:
            print(f"更新凭证失败(忽略): {e}")
    python_path = resolved

    with open(AUTOSTART_NAME_FILE, "w") as f:
        f.write(cred)

    _generate_access_key()
    if not _write_autostart_sh(python_path):
        print("写入启动脚本失败, 终止.")
        return False

    user = getpass.getuser()
    unit = _build_service_unit(user, PROJECT_DIR, AUTOSTART_SH)
    if not sudo_write_file(SERVICE_PATH, unit):
        return False

    # 清掉之前的失败状态, 避免 "Start request repeated too quickly"
    systemctl("reset-failed", SERVICE_NAME)
    _start_and_enable()
    print(f"\n服务已启动并设置开机自启.")
    print(f"  使用凭证: {cred}")
    print(f"  Python 路径: {python_path}")
    return True


def start_service():
    state, current = get_service_state()
    if state == "active":
        print(f"服务已在运行, 使用凭证: {current}")
        ans = input("是否重新设置? (y/N): ").strip().lower()
        if ans != "y":
            return
        _stop_and_disable()

    creds = EncryptCred.list_creds()
    if not creds:
        print("没有可用凭证, 进入添加凭证流程...")
        add_encrypt()
        creds = EncryptCred.list_creds()
        if not creds:
            print("仍无可用凭证, 取消启动.")
            return

    if len(creds) == 1:
        chosen = creds[0]
        print(f"使用唯一可用凭证: {chosen}")
    else:
        chosen = _select_cred("请选择用于服务的凭证: ")
        if not chosen:
            return

    _setup_service_with(chosen)


def stop_service():
    state, _ = get_service_state()
    if state == "not-installed":
        print("没有服务在运行.")
        return
    _stop_and_disable()


# ---------- Web 端复用的操作 ----------
def web_list_creds():
    state, current = get_service_state()
    out = []
    for f in EncryptCred.list_creds():
        ok, cfg = EncryptCred.load_cred(f)
        out.append({
            "filename": f,
            "config_name": cfg.get("ConfigName") if ok else f,
            "in_use": (state == "active" and current == f),
        })
    return {
        "creds": out,
        "service_state": state,
        "active_cred": current,
    }


def web_view_cred(name):
    if name not in EncryptCred.list_creds():
        return None
    ok, cfg = EncryptCred.load_cred(name)
    return cfg if ok else None


def web_create_cred(data):
    return EncryptCred.create_cred_from_dict(data)


def web_update_cred(name, data, action="default"):
    """action: default(仅在未被使用时允许), restart, nothing, stop"""
    state, current = get_service_state()
    in_use = state == "active" and current == name
    if in_use and action == "default":
        return False, "in_use"
    if not EncryptCred.update_cred_from_dict(name, data):
        return False, "update_failed"
    if in_use:
        if action == "restart":
            systemctl("restart", SERVICE_NAME)
        elif action == "stop":
            _stop_and_disable()
    return True, "ok"


def web_delete_cred(name, action="default"):
    """action: default(仅在未被使用时), stop(删除并停服务), keep(只删除文件)"""
    state, current = get_service_state()
    in_use = state == "active" and current == name
    if in_use and action == "default":
        return False, "in_use"
    EncryptCred.delete_cred(name)
    if in_use and action == "stop":
        _stop_and_disable()
    return True, "ok"


def web_start_service(cred_name):
    if cred_name not in EncryptCred.list_creds():
        return False, "cred_not_found"
    state, _ = get_service_state()
    if state == "active":
        return False, "already_active"
    return (True, "ok") if _setup_service_with(cred_name) else (False, "setup_failed")


def web_stop_service():
    state, _ = get_service_state()
    if state == "not-installed":
        return False, "not_running"
    _stop_and_disable()
    return True, "ok"


def _build_ops():
    return {
        "list_creds": web_list_creds,
        "view_cred": web_view_cred,
        "create_cred": web_create_cred,
        "update_cred": web_update_cred,
        "delete_cred": web_delete_cred,
        "start_service": web_start_service,
        "stop_service": web_stop_service,
    }


# ---------- 浏览器查看 ----------
def _ask_port():
    while True:
        s = input("请输入端口号 (1024-65535): ").strip()
        try:
            p = int(s)
            if 1024 <= p <= 65535:
                return p
        except Exception:
            pass
        print("端口号不合法, 请重新输入.")


def _get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def open_in_browser():
    port = _ask_port()
    lan = input("是否需要在局域网内访问? (y/N): ").strip().lower() == "y"
    access_key = _generate_access_key()

    host = "0.0.0.0" if lan else "127.0.0.1"
    print("\n=== 浏览器访问地址 ===")
    print(f"  本机: http://localhost:{port}")
    if lan:
        ip = _get_lan_ip()
        if ip:
            print(f"  局域网: http://{ip}:{port}")

    print("\n--- 一次性访问密钥 (仅本次显示) ---")
    print(f"  {access_key}")
    print("-" * 40)

    copied, tool = try_copy_to_clipboard(access_key)
    if copied:
        print(f"密钥已复制到剪贴板 (使用 {tool}), 直接在浏览器中粘贴即可.")
    else:
        print("(未找到可用剪贴板工具, 请手动选中上方密钥复制.)")
        if not sys.platform.startswith(("darwin", "win")):
            print(" 提示: 可安装 xclip/xsel/wl-copy 以支持自动复制.")
    input("\n按回车启动 Web 服务 (Ctrl+C 可停止并返回菜单)... ")

    try:
        from web_view import create_app
    except ImportError:
        print("缺少 Flask 依赖, 请先安装: pip install flask")
        return
    app = create_app(
        access_key=access_key,
        project_dir=PROJECT_DIR,
        get_state=get_service_state,
        ops=_build_ops(),
    )
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nWeb 服务已停止.")
    except OSError as e:
        print(f"启动失败: {e}")


# ---------- 主循环 ----------
MENU_TEXT = (
    "=========== 校园网自动登陆 管理工具 ===========\n"
    "  1. 管理凭证 (encrypt)\n"
    "  2. 查看服务状态\n"
    "  3. 启动服务 (并开机自启动)\n"
    "  4. 关闭服务 (并取消开机自启动)\n"
    "  5. 在浏览器查看\n"
    "  6. 退出"
)


def _run(title, fn, pause_after=True):
    clear_screen()
    print(f"=== {title} ===\n")
    try:
        fn()
    except (KeyboardInterrupt, EOFError):
        print("\n已中止当前操作.")
    if pause_after:
        pause()


def main_menu():
    while True:
        clear_screen()
        print(MENU_TEXT)
        try:
            c = input("请选择: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if c == "1":
            _run("管理凭证", manage_encrypt, pause_after=False)
        elif c == "2":
            _run("服务状态", view_service_status)
        elif c == "3":
            _run("启动服务 (并开机自启动)", start_service)
        elif c == "4":
            _run("关闭服务 (并取消开机自启动)", stop_service)
        elif c == "5":
            _run("在浏览器查看", open_in_browser, pause_after=False)
        elif c == "6":
            clear_screen()
            print("再见.")
            return
        else:
            print("输入无效.")
            pause()


def main():
    if not is_linux():
        print("注意: 当前并非 Linux 平台, 服务相关功能 (systemctl) 不可用, "
              "凭证管理与浏览器查看功能可正常使用.")
    step0_setup()
    try:
        main_menu()
    except (KeyboardInterrupt, EOFError):
        print("\n已退出.")


if __name__ == "__main__":
    main()
