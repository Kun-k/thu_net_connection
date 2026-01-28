from auto_login import AutoLogin
from encrypt_cred import EncryptCred

if __name__ == "__main__":
    # 读取"credentials/.ConfigName"文件，获取ConfigName
    with open("./credentials/.ConfigName", "r") as f:
        ConfigFileName = f.read().strip()

    config = EncryptCred.load_cred(ConfigFileName)

    if config[0]:
        auto_login = AutoLogin(config[1])
        auto_login.run()
