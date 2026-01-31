# -*- coding: utf-8 -*-

import getpass
import json
from cryptography.fernet import Fernet
import os


class EncryptCred:
    def __init__(self):
        os.makedirs("credentials", exist_ok=True)

    def run(self):
        input_info = self.choice_cred()
        if input_info[0]:
            ConfigFileName = input_info[1]
        else:
            ConfigFileName = self.save_cred()

        # ConfigName写入临时文件
        if os.path.exists("./credentials/.ConfigName"):
            os.remove("./credentials/.ConfigName")
        with open("./credentials/.ConfigName", "w") as f:
            f.write(ConfigFileName)

        return ConfigFileName

    def run_auto_start(self):
        ConfigFileName = self.run()
        # ConfigName写入临时文件
        if os.path.exists("./credentials/.ConfigNameAutoStart"):
            os.remove("./credentials/.ConfigNameAutoStart")
        with open("./credentials/.ConfigNameAutoStart", "w") as f:
            f.write(ConfigFileName)

    @staticmethod
    def choice_cred():
        if not os.path.exists(f"./credentials/.cred_key"):
            print("没有找到已保存的凭证, 开始新建凭证.\n")
            return False, ""

        saved_cred = {}
        i = 1
        for cred in os.listdir("credentials"):
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
            except:
                print("输入无效，请重新输入.\n")

        if choice == 0:
            print("\n开始新建凭证.\n")
            return False, ""

        print(f"\n选择凭证{saved_cred[choice]}\n")
        return True, saved_cred[choice]

    # 生成密钥
    @staticmethod
    def generate_key():
        key = Fernet.generate_key()
        with open("credentials/.cred_key", "wb") as f:
            f.write(key)
        os.chmod("credentials/.cred_key", 0o600)  # 仅当前用户可读
        return key

    # 加密并保存凭证
    def save_cred(self):
        # 加载/生成密钥
        key = self.generate_key() if not os.path.exists("./credentials/.cred_key") else open("./credentials/.cred_key", "rb").read()
        fernet = Fernet(key)

        # 交互式输入凭证（此时有终端，可正常用getpass）
        ConfigName = input("配置名称 ConfigName: ").strip()
        UserName = input("校园网账户用户名 UserName: ").strip()
        PassWord = getpass.getpass("校园网账户密码 PassWord: ").strip()
        CheckInterval = input("检查间隔 CheckInterval (单位为秒，默认120): ").strip()
        EmailAddress = input("邮箱账户 EmailAddress: ").strip()
        EmailAuthCode = getpass.getpass("邮箱授权码 EmailAuthCode: ").strip()
        EmailSmtpServer = input("SMTP服务器 EmailSmtpServer (默认QQ邮箱　smtp.qq.com): ").strip()
        EmailSmtpPort = input("SMTP端口 EmailSmtpPort (默认QQ邮箱　465): ").strip()

        # 处理默认值
        if not CheckInterval:
            CheckInterval = 120
        else:
            CheckInterval = int(CheckInterval)
        if not EmailSmtpServer:
            EmailSmtpServer = "smtp.qq.com"
        if not EmailSmtpPort:
            EmailSmtpPort = 465
        else:
            EmailSmtpPort = int(EmailSmtpPort)

        # 加密
        enc_UserName = fernet.encrypt(UserName.encode()).decode()
        enc_PassWord = fernet.encrypt(PassWord.encode()).decode()
        enc_EmailAddress = fernet.encrypt(EmailAddress.encode()).decode()
        enc_EmailAuthCode = fernet.encrypt(EmailAuthCode.encode()).decode()

        data = {
            "ConfigName": ConfigName,
            "UserName": enc_UserName,
            "PassWord": enc_PassWord,
            "CheckInterval": CheckInterval,
            "EmailAddress": enc_EmailAddress,
            "EmailAuthCode": enc_EmailAuthCode,
            "EmailSmtpServer": EmailSmtpServer,
            "EmailSmtpPort": EmailSmtpPort
        }

        # 保存加密凭证
        with open(f"./credentials/.{ConfigName}.encrypted_cred", "w") as f:
            json.dump(data, f)
        os.chmod(f"./credentials/.{ConfigName}.encrypted_cred", 0o600)

        print(f"凭证已加密保存至文件 ./credentials/.{ConfigName}.encrypted_cred")

        return f".{ConfigName}.encrypted_cred"

    @staticmethod
    # ========== 加载并解密凭证 ==========
    def load_cred(ConfigFileName):
        """加载并解密配置文件中的凭证"""
        # 检查文件是否存在
        if not os.path.exists("./credentials/.cred_key") or not os.path.exists(f"./credentials/{ConfigFileName}"):
            print("未找到加密密钥/凭证文件.")
            return False, {}

        # 解密
        with open("./credentials/.cred_key", "rb") as f:
            key = f.read()
        fernet = Fernet(key)

        with open(f"./credentials/{ConfigFileName}", "r") as f:
            config = json.load(f)

        config_decode = {
            "ConfigName": config["ConfigName"],
            "UserName": fernet.decrypt(config["UserName"].encode()).decode(),
            "PassWord": fernet.decrypt(config["PassWord"].encode()).decode(),
            "CheckInterval": int(config["CheckInterval"]),
            "EmailAddress": fernet.decrypt(config["EmailAddress"].encode()).decode(),
            "EmailAuthCode": fernet.decrypt(config["EmailAuthCode"].encode()).decode(),
            "EmailSmtpServer": config["EmailSmtpServer"],
            "EmailSmtpPort": int(config["EmailSmtpPort"])
        }

        return True, config_decode


if __name__ == "__main__":
    encrypt_cred = EncryptCred()
    config = encrypt_cred.run()
