import subprocess
import socket
import shlex
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import email.utils
from logger import get_logger
from encrypt_cred import EncryptCred


class AutoLogin:
    def __init__(self, config):
        self.logger = get_logger("auto_login.log")

        self.ping_host_list = []
        with open("ping_host_list", "r") as f:
            # 每行一条数据
            for line in f:
                self.ping_host_list.append(line.strip())
        self.ping_host_idx = 0

        self.UserName = config["UserName"]
        self.PassWord = config["PassWord"]
        self.EmailAddress = config["EmailAddress"]
        self.EmailAuthCode = config["EmailAuthCode"]
        self.CheckInterval = config["CheckInterval"]
        self.EmailSmtpServer = config["EmailSmtpServer"]
        self.EmailSmtpPort = config["EmailSmtpPort"]

    def check_network(self):
        host = self.ping_host_list[self.ping_host_idx]
        self.ping_host_idx += 1
        if self.ping_host_idx >= len(self.ping_host_list):
            self.ping_host_idx = 0

        ping_cmd = ["ping", "-c", "4", host]
        self.logger.info("检查网络连通性: ping %s" % host)

        try:
            result = subprocess.run(
                ping_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                self.logger.info("网络正常, ping %s 成功" % host)
                return True
            else:
                self.logger.info("网络异常, ping %s 失败" % host)
                return False
        except Exception as e:
            self.logger.info("网络检测出错, 错误信息 %s" % e)
            return False

    @staticmethod
    def get_local_ip():
        """获取一个可用的本机IP（简化版，适合大多数场景）"""
        try:
            # 通过连接外部服务器（不实际发送数据）获取本机出口IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("223.5.5.5", 80))  # 谷歌DNS服务器
            ip = s.getsockname()[0]
            s.close()
            return True, ip
        except Exception:
            return False, ""

    @staticmethod
    def get_public_ip():
        """获取本机公网IP（国内稳定版）"""
        domestic_apis = ["curl -s --max-time 3 ip.cn", "curl -s --max-time 3 ifconfig.me"]
        for api_cmd in domestic_apis:
            try:
                result = subprocess.run(
                    shlex.split(api_cmd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0:
                    ip_str = result.stdout.strip()
                    if len(ip_str.split(".")) == 4:
                        return True, ip_str
            except Exception:
                continue
        return False, ""

    def get_all_ip_info(self):
        local_ip = self.get_local_ip()
        public_ip = self.get_public_ip()

        ip_info = ""
        if local_ip[0]:
            ip_info += "本地IP: %s\n" % local_ip[1]
        if public_ip[0]:
            ip_info += "公网IP: %s\n" % public_ip[1]
        return ip_info

    def connect_network(self):
        self.logger.info("尝试连接网络")
        while True:
            subprocess.call(["~/auth-client", "-u", self.UserName, "-p", self.PassWord, "auth"])
            if self.check_network():
                break
            time.sleep(10)

    def send_email(self, subject, content):
        """
        终极修复版：使用官方工具构造符合RFC规范的From字段
        """
        # 1. 构造邮件内容
        msg = MIMEText(content, "plain", "utf-8")

        # 关键修复：用官方函数构造From（显示名+邮箱，完全符合RFC）
        # 显示名建议用简单的中文/英文，如"SystemNotice" "系统通知"
        from_name = "SystemNotice"  # 纯英文显示名，避免编码问题
        msg["From"] = email.utils.formataddr((Header(from_name, 'utf-8').encode(), self.EmailAddress))

        # To字段也用相同方式构造（可选，但统一格式更稳妥）
        msg["To"] = email.utils.formataddr((Header("Recipient", 'utf-8').encode(), self.EmailAddress))

        # 主题字段也严格按RFC构造
        msg["Subject"] = Header(subject, 'utf-8')

        try:
            with smtplib.SMTP_SSL(self.EmailSmtpServer, self.EmailSmtpPort, timeout=10) as smtp_obj:
                smtp_obj.login(self.EmailAddress, self.EmailAuthCode)
                # 强制指定发件人（和From字段一致）
                smtp_obj.sendmail(self.EmailAddress, [self.EmailAddress], msg.as_string())
            self.logger.info("邮件发送成功！")
            return True
        except smtplib.SMTPException as e:
            self.logger.info(f"邮件发送失败，MTP错误：{str(e)}")
            return False
        except Exception as e:
            self.logger.info(f"邮件发送失败，其他错误：{str(e)}")
            return False

    def run(self):
        start_info = "执行校园网自动登陆程序: \nUserName: %s\n\nEmail: %s" % (self.UserName, self.EmailAddress)
        self.logger.info(start_info)

        ip_info = self.get_all_ip_info()
        self.logger.info("当前IP信息: %s " % ip_info)

        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        email_subject_start = "校园网自动登陆程序-程序启动"
        email_content_start = "时间: %s \n %s \n当前IP信息: %s" % (curr_time, start_info, ip_info)

        if self.send_email(email_subject_start, email_content_start):
            send_reconnect_info_flag = False
        else:
            send_reconnect_info_flag = True

        send_start_info_flag = False
        email_subject = ""
        email_content = ""

        while True:
            if not self.check_network():
                self.connect_network()
                send_reconnect_info_flag = True
                ip_info = self.get_all_ip_info()
                connect_info = "网络重连成功: \nUserName: %s\n\nEmail: %s" % (self.UserName, self.EmailAddress)
                self.logger.info(connect_info)
                self.logger.info("当前IP信息: %s " % ip_info)

                email_subject = "校园网自动登陆程序-网络重连"
                email_content = "时间: %s \n %s \n当前IP信息: %s" % (curr_time, connect_info, ip_info)

            if send_start_info_flag:
                if self.send_email(email_subject_start, email_content_start):
                    send_start_info_flag = False

            if send_reconnect_info_flag:
                curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if self.send_email(email_subject, email_content):
                    send_reconnect_info_flag = False

            time.sleep(self.CheckInterval)


if __name__ == "__main__":
    # 读取"credentials/.ConfigName"文件，获取ConfigName
    with open("credentials/.ConfigName", "r") as f:
        ConfigFileName = f.read().strip()

    config = EncryptCred.load_cred(ConfigFileName)
    if config[0]:
        auto_login = AutoLogin(config[1])
