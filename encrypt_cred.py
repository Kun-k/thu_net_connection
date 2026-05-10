# -*- coding: utf-8 -*-

import getpass
import json
import os
import sys

from cryptography.fernet import Fernet


CRED_DIR = "credentials"
KEY_FILE = os.path.join(CRED_DIR, ".cred_key")


def _ensure_dir():
    os.makedirs(CRED_DIR, exist_ok=True)


def _load_or_create_key():
    _ensure_dir()
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        os.chmod(KEY_FILE, 0o600)
        return key
    with open(KEY_FILE, "rb") as f:
        return f.read()


class EncryptCred:
    def __init__(self):
        _ensure_dir()

    # --- legacy entrypoints (kept for compatibility with sh_run.sh) ---
    def run(self):
        input_info = self.choice_cred()
        if input_info[0]:
            ConfigFileName = input_info[1]
        else:
            ConfigFileName = self.save_cred()

        if os.path.exists(os.path.join(CRED_DIR, ".ConfigName")):
            os.remove(os.path.join(CRED_DIR, ".ConfigName"))
        with open(os.path.join(CRED_DIR, ".ConfigName"), "w") as f:
            f.write(ConfigFileName)

        return ConfigFileName

    def run_auto_start(self):
        ConfigFileName = self.run()
        target = os.path.join(CRED_DIR, ".ConfigNameAutoStart")
        if os.path.exists(target):
            os.remove(target)
        with open(target, "w") as f:
            f.write(ConfigFileName)

    @staticmethod
    def choice_cred():
        if not os.path.exists(KEY_FILE):
            print("没有找到已保存的凭证, 开始新建凭证.\n")
            return False, ""

        saved_cred = {}
        i = 1
        for cred in os.listdir(CRED_DIR):
            if cred.endswith("encrypted_cred"):
                saved_cred[i] = cred
                i += 1

        if len(saved_cred) == 0:
            print("没有找到已保存的凭证, 开始新建凭证.\n")
            return False, ""

        print("已保存的凭证：")
        for k, v in saved_cred.items():
            print(f"\t{k}. {v}")

        while True:
            try:
                choice = int(input("请选择要使用的凭证(输入序号，0表示新建):"))
                if choice not in saved_cred.keys() and choice != 0:
                    raise Exception
                break
            except Exception:
                print("输入无效，请重新输入.\n")

        if choice == 0:
            print("\n开始新建凭证.\n")
            return False, ""

        print(f"\n选择凭证{saved_cred[choice]}\n")
        return True, saved_cred[choice]

    # --- helpers ---
    @staticmethod
    def list_creds():
        _ensure_dir()
        if not os.path.exists(KEY_FILE):
            return []
        return sorted(
            f for f in os.listdir(CRED_DIR) if f.endswith("encrypted_cred")
        )

    @staticmethod
    def generate_key():
        return _load_or_create_key()

    # --- create ---
    def save_cred(self):
        ConfigName = input("配置名称 ConfigName: ").strip()
        ServerName = input("服务器名称 ServerName: ").strip()
        UserName = input("校园网账户用户名 UserName: ").strip()
        PassWord = getpass.getpass("校园网账户密码 PassWord: ").strip()
        CheckInterval = input("检查间隔 CheckInterval (单位为秒，默认120): ").strip()
        EmailAddress = input("邮箱账户 EmailAddress: ").strip()
        EmailAuthCode = getpass.getpass("邮箱授权码 EmailAuthCode: ").strip()
        EmailSmtpServer = input("SMTP服务器 EmailSmtpServer (默认 smtp.qq.com): ").strip()
        EmailSmtpPort = input("SMTP端口 EmailSmtpPort (默认 465): ").strip()
        PythonPath = input(f"Python 解释器路径 PythonPath (默认 {sys.executable}): ").strip()

        return EncryptCred.create_cred_from_dict({
            "ConfigName": ConfigName,
            "ServerName": ServerName,
            "UserName": UserName,
            "PassWord": PassWord,
            "CheckInterval": CheckInterval,
            "EmailAddress": EmailAddress,
            "EmailAuthCode": EmailAuthCode,
            "EmailSmtpServer": EmailSmtpServer,
            "EmailSmtpPort": EmailSmtpPort,
            "PythonPath": PythonPath,
        })

    @staticmethod
    def _normalize(data):
        out = dict(data)
        ci = out.get("CheckInterval")
        out["CheckInterval"] = int(ci) if ci not in (None, "", 0) else 120
        if not out.get("EmailSmtpServer"):
            out["EmailSmtpServer"] = "smtp.qq.com"
        ep = out.get("EmailSmtpPort")
        out["EmailSmtpPort"] = int(ep) if ep not in (None, "", 0) else 465
        if not out.get("PythonPath"):
            out["PythonPath"] = sys.executable or "python"
        return out

    @staticmethod
    def create_cred_from_dict(data):
        """非交互式创建凭证；返回保存的文件名 (.<ConfigName>.encrypted_cred)。"""
        d = EncryptCred._normalize(data)
        if not d.get("ConfigName"):
            raise ValueError("ConfigName 不能为空")

        key = _load_or_create_key()
        fernet = Fernet(key)
        record = {
            "ConfigName": d["ConfigName"],
            "ServerName": d.get("ServerName", ""),
            "UserName": fernet.encrypt(d["UserName"].encode()).decode(),
            "PassWord": fernet.encrypt(d["PassWord"].encode()).decode(),
            "CheckInterval": d["CheckInterval"],
            "EmailAddress": fernet.encrypt(d["EmailAddress"].encode()).decode(),
            "EmailAuthCode": fernet.encrypt(d["EmailAuthCode"].encode()).decode(),
            "EmailSmtpServer": d["EmailSmtpServer"],
            "EmailSmtpPort": d["EmailSmtpPort"],
            "PythonPath": d["PythonPath"],
        }
        filename = f".{d['ConfigName']}.encrypted_cred"
        path = os.path.join(CRED_DIR, filename)
        with open(path, "w") as f:
            json.dump(record, f)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        return filename

    # --- read ---
    @staticmethod
    def load_cred(ConfigFileName):
        if not os.path.exists(KEY_FILE) or not os.path.exists(
            os.path.join(CRED_DIR, ConfigFileName)
        ):
            print("未找到加密密钥/凭证文件.")
            return False, {}

        with open(KEY_FILE, "rb") as f:
            key = f.read()
        fernet = Fernet(key)

        with open(os.path.join(CRED_DIR, ConfigFileName), "r") as f:
            config = json.load(f)

        decoded = {
            "ConfigName": config["ConfigName"],
            "ServerName": config.get("ServerName", ""),
            "UserName": fernet.decrypt(config["UserName"].encode()).decode(),
            "PassWord": fernet.decrypt(config["PassWord"].encode()).decode(),
            "CheckInterval": int(config["CheckInterval"]),
            "EmailAddress": fernet.decrypt(config["EmailAddress"].encode()).decode(),
            "EmailAuthCode": fernet.decrypt(config["EmailAuthCode"].encode()).decode(),
            "EmailSmtpServer": config["EmailSmtpServer"],
            "EmailSmtpPort": int(config["EmailSmtpPort"]),
            "PythonPath": config.get("PythonPath", "python"),
        }
        return True, decoded

    # --- update ---
    @staticmethod
    def update_cred(ConfigFileName):
        ok, current = EncryptCred.load_cred(ConfigFileName)
        if not ok:
            return False

        print("（直接回车保留当前值；密码类字段为空回车保留）")

        def ask(label, key, secret=False):
            cur = current[key]
            shown = "******" if secret else cur
            prompt = f"{label} [{shown}]: "
            val = (getpass.getpass(prompt) if secret else input(prompt)).strip()
            return val if val else cur

        ServerName = ask("服务器名称 ServerName", "ServerName")
        UserName = ask("校园网账户用户名 UserName", "UserName")
        PassWord = ask("校园网账户密码 PassWord", "PassWord", secret=True)
        ci = input(f"检查间隔 CheckInterval [{current['CheckInterval']}]: ").strip()
        CheckInterval = int(ci) if ci else current["CheckInterval"]
        EmailAddress = ask("邮箱账户 EmailAddress", "EmailAddress")
        EmailAuthCode = ask("邮箱授权码 EmailAuthCode", "EmailAuthCode", secret=True)
        EmailSmtpServer = ask("SMTP服务器 EmailSmtpServer", "EmailSmtpServer")
        ep = input(f"SMTP端口 EmailSmtpPort [{current['EmailSmtpPort']}]: ").strip()
        EmailSmtpPort = int(ep) if ep else current["EmailSmtpPort"]
        PythonPath = ask("Python 解释器路径 PythonPath", "PythonPath")

        return EncryptCred.update_cred_from_dict(ConfigFileName, {
            "ServerName": ServerName,
            "UserName": UserName,
            "PassWord": PassWord,
            "CheckInterval": CheckInterval,
            "EmailAddress": EmailAddress,
            "EmailAuthCode": EmailAuthCode,
            "EmailSmtpServer": EmailSmtpServer,
            "EmailSmtpPort": EmailSmtpPort,
            "PythonPath": PythonPath,
        })

    @staticmethod
    def update_cred_from_dict(ConfigFileName, data):
        """非交互式更新；data 中缺失或空字符串的密码类字段保留原值。"""
        ok, current = EncryptCred.load_cred(ConfigFileName)
        if not ok:
            return False

        merged = dict(current)
        for k, v in data.items():
            if v is None:
                continue
            if k in ("PassWord", "EmailAuthCode") and v == "":
                continue
            merged[k] = v
        merged["ConfigName"] = current["ConfigName"]
        merged = EncryptCred._normalize(merged)

        key = _load_or_create_key()
        fernet = Fernet(key)
        record = {
            "ConfigName": merged["ConfigName"],
            "ServerName": merged.get("ServerName", ""),
            "UserName": fernet.encrypt(merged["UserName"].encode()).decode(),
            "PassWord": fernet.encrypt(merged["PassWord"].encode()).decode(),
            "CheckInterval": merged["CheckInterval"],
            "EmailAddress": fernet.encrypt(merged["EmailAddress"].encode()).decode(),
            "EmailAuthCode": fernet.encrypt(merged["EmailAuthCode"].encode()).decode(),
            "EmailSmtpServer": merged["EmailSmtpServer"],
            "EmailSmtpPort": merged["EmailSmtpPort"],
            "PythonPath": merged["PythonPath"],
        }
        path = os.path.join(CRED_DIR, ConfigFileName)
        with open(path, "w") as f:
            json.dump(record, f)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
        return True

    # --- delete ---
    @staticmethod
    def delete_cred(ConfigFileName):
        path = os.path.join(CRED_DIR, ConfigFileName)
        if os.path.exists(path):
            os.remove(path)
        autostart = os.path.join(CRED_DIR, ".ConfigNameAutoStart")
        if os.path.exists(autostart):
            with open(autostart) as f:
                if f.read().strip() == ConfigFileName:
                    os.remove(autostart)
        cur = os.path.join(CRED_DIR, ".ConfigName")
        if os.path.exists(cur):
            with open(cur) as f:
                if f.read().strip() == ConfigFileName:
                    os.remove(cur)
        return True


if __name__ == "__main__":
    EncryptCred().run()
