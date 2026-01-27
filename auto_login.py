'''
python auto_login.py -u rk23 -p rk23@mails.tsinghua.edu.cn -c 120 -e 445166827@qq.com -eac ecosojclduzfbghh
'''

import argparse
import subprocess
import socket
import shlex
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import email.utils
import logging
from logging.handlers import RotatingFileHandler


arguments = argparse.ArgumentParser(description='ThuNetConnection')
arguments.add_argument('--UserName', '-u', type=str, required=True)
arguments.add_argument('--PassWord', '-p', type=str, required=True)
arguments.add_argument('--CheckInterval', '-c', type=int, default=120)
arguments.add_argument('--EmailAddress', '-e', type=str, required=True)
arguments.add_argument('--EmailAuthCode', '-eac', type=str, required=True)
arguments.add_argument('--EmailSmtpServer', '-ess', type=str, default="smtp.qq.com")
arguments.add_argument('--EmailSmtpPort', '-esp', type=str, default=465)

args = arguments.parse_args()
UserName = args.UserName
PassWord = args.PassWord
CheckInterval = args.CheckInterval
EmailAddress = args.EmailAddress
EmailAuthCode = args.EmailAuthCode
EmailSmtpServer = args.EmailSmtpServer
EmailSmtpPort = args.EmailSmtpPort


# 创建RotatingFileHandler
handler = RotatingFileHandler(
    filename='auto_login.log',  # 日志文件名
    maxBytes=10000,             # 单个文件最大字节数（10KB）
    backupCount=10              # 保留的备份文件数量
)
# 配置日志
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
# 添加到logger
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


ping_host_list = [
    "baidu.com",
    "blog.csdn.net",
    "ping.tsinghua.edu.cn",
    "www.qq.com",
    "www.iqiyi.com"
]
ping_host_idx = 0


def check_network():
    global ping_host_idx
    host = ping_host_list[ping_host_idx]
    ping_host_idx += 1
    if ping_host_idx >= len(ping_host_list):
        ping_host_idx = 0

    ping_cmd = ["ping", "-c", "4", host]
    logger.info("检查网络连通性: ping %s" % host)

    try:
        result = subprocess.run(
            ping_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            logger.info("网络正常, ping %s 成功" % host)
            return True
        else:
            logger.info("网络异常, ping %s 失败" % host)
            return False
    except Exception as e:
        logger.info("网络检测出错, 错误信息 %s" % e)
        return False


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


def get_all_ip_info():
    ip_info = ""
    if local_ip[0]:
        ip_info += "本地IP: %s\n" % local_ip[1]
    if public_ip[0]:
        ip_info += "公网IP: %s\n" % public_ip[1]
    return ip_info


def connect_network():
    logger.info("尝试连接网络")
    while True:
        subprocess.call(["./auth-client", "-u", UserName, "-p", PassWord, "auth"])
        if check_network():
            break
        time.sleep(10)


def send_email(to_email, subject, content, sender, auth_code, smtp_server="smtp.qq.com", smtp_port=465):
    """
    终极修复版：使用官方工具构造符合RFC规范的From字段
    """
    # 1. 构造邮件内容
    msg = MIMEText(content, "plain", "utf-8")

    # 关键修复：用官方函数构造From（显示名+邮箱，完全符合RFC）
    # 显示名建议用简单的中文/英文，如"SystemNotice" "系统通知"
    from_name = "SystemNotice"  # 纯英文显示名，避免编码问题
    msg["From"] = email.utils.formataddr((Header(from_name, 'utf-8').encode(), sender))

    # To字段也用相同方式构造（可选，但统一格式更稳妥）
    msg["To"] = email.utils.formataddr((Header("Recipient", 'utf-8').encode(), to_email))

    # 主题字段也严格按RFC构造
    msg["Subject"] = Header(subject, 'utf-8')

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as smtp_obj:
            smtp_obj.login(sender, auth_code)
            # 强制指定发件人（和From字段一致）
            smtp_obj.sendmail(sender, [to_email], msg.as_string())
        logger.info("邮件发送成功！")
        return True
    except smtplib.SMTPException as e:
        logger.info(f"邮件发送失败，MTP错误：{str(e)}")
        return False
    except Exception as e:
        logger.info(f"邮件发送失败，其他错误：{str(e)}")
        return False


if "__main__" == __name__:
    start_info = "执行校园网自动登陆程序: \nUserName: %s\n\nEmail: %s" % (UserName, EmailAddress)
    logger.info(start_info)

    local_ip = get_local_ip()
    public_ip = get_public_ip()

    ip_info = get_all_ip_info()
    logger.info("当前IP信息: %s " % ip_info)

    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email_subject_start = "校园网自动登陆程序-程序启动"
    email_content_start = "时间: %s \n %s \n当前IP信息: %s" % (curr_time, start_info, ip_info)

    if send_email(EmailAddress, email_subject_start, email_content_start, EmailAddress, EmailAuthCode, EmailSmtpServer, EmailSmtpPort):
        send_reconnect_info_flag = False
    else:
        send_reconnect_info_flag = True

    send_start_info_flag = False
    email_subject = ""
    email_content = ""

    while True:
        if not check_network():
            connect_network()
            send_reconnect_info_flag = True
            ip_info = get_all_ip_info()
            connect_info = "网络重连成功: \nUserName: %s\n\nEmail: %s" % (UserName, EmailAddress)
            logger.info(connect_info)
            logger.info("当前IP信息: %s " % ip_info)

            email_subject = "校园网自动登陆程序-网络重连"
            email_content = "时间: %s \n %s \n当前IP信息: %s" % (curr_time, connect_info, ip_info)

        if send_start_info_flag:
            if send_email(EmailAddress, email_subject_start, email_content_start, EmailAddress, EmailAuthCode, EmailSmtpServer, EmailSmtpPort):
                send_start_info_flag = False

        if send_reconnect_info_flag:
            curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if send_email(EmailAddress, email_subject, email_content, EmailAddress, EmailAuthCode, EmailSmtpServer, EmailSmtpPort):
                send_reconnect_info_flag = False

        time.sleep(CheckInterval)

