# 0. 设置文件权限

首先将auth-client和.auth-setting文件放到用户目录下:
```bash
cp ./TunetZRRZ2025_linux/Tunet_linux2025/auth-client ~/
cp ./TunetZRRZ2025_linux/Tunet_linux2025/.auth-setting ~/
```

然后赋予文件权限:
```bash
chmod +x ~/auth-client
```

# 1. 手动登陆校园网

```bash
cd 
./auth-client -u 用户名 -p 用户密码 auth
```

# 2. 自动登陆校园网

赋予文件权限:
```bash
chmod +x *.sh
```

执行脚本`sh_run.sh`, 按照输出内容提示, 输入信息.
```bash
./sh_run.sh
```

需要输入的配置信息包括:
```
UserName,           校园网账户的用户名
Password,           校园网账户的密码
CheckInterval,      检查网络状态间隔，单位为秒，默认为120
Email,              发送网络状态的邮箱地址
EmailAuthCode,      发送网络状态的邮箱授权码
SmtpServer,         邮箱SMTP服务器，默认为smtp.qq.com（QQ邮箱）
SmtpPort,           邮箱SMTP服务器端口，默认为465（QQ邮箱）
```

# 3. 配置程序自启动

如果希望配置程序自启动，需要首先执行脚本`sh_run_encrypt_cred_autostart.sh`, 选择或生成一组用于自启动的配置信息:
```bash
./sh_run_encrypt_cred_autostart.sh
```

然后将脚本`sh_run_auto_login_autostart.sh`设置为自启动脚本：

1. 编辑脚本`sh_run_auto_login_autostart.sh`，进行python环境配置，选择一个python路径。

2. 创建service文件:
```bash
sudo vim /etc/systemd/system/auto_login.service
```
写入内容：
```ini
[Unit]
Description=Auto Login Service
After=network.target

[Service]
Type=simple
ExecStart=path to [sh_run_auto_login_autostart.sh]
Restart=always
User=你的用户名
WorkingDirectory=项目目录
[Install]
WantedBy=multi-user.target
```

3. 启动服务:
```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl start auto_login.service
```

4. 设置开机自启:
```bash
sudo systemctl enable auto_login.service
```

5. 查看服务状态:
```bash
sudo systemctl status auto_login.service
```

# 4. 登出校园网

如果之前执行过自动登陆程序，则首先退出程序:
```bash
ps -aux | grep python |grep auto_login
```
查找对应的进程PID，然后kill进程。

之后执行登出命令:
```bash
cd 
./auth-client -u 用户名 auth --logout
```



