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

首先将python脚本文件放到用户目录下:
```bash
cp ./auto_login.py ~/
```

然后赋予文件权限:
```bash
chmod +x ~/auto_login.py
```

进入用户目录，执行程序:
```bash
cd
python auto_login.py -u 用户名 -p 用户密码 -c 检查网络状态间隔 -e 邮箱 -eac 邮箱授权码
```

或者后台运行:
```bash
nohup python auto_login.py -u 用户名 -p 用户密码 -c 检查网络状态间隔 -e 邮箱 -eac 邮箱授权码 >/dev/null 2>&1 &
```

执行脚本的参数如下:
```
--UserName, -u          校园网账户的用户名
--Password, -p          校园网账户的密码
--CheckInterval, -c     检查网络状态间隔，单位为秒，默认为120
--Email, -e             发送网络状态的邮箱地址
--EmailAuthCode, -eac   发送网络状态的邮箱授权码
--SmtpServer, -s        邮箱SMTP服务器，默认为smtp.qq.com（QQ邮箱）
--SmtpPort, -sp         邮箱SMTP服务器端口，默认为465（QQ邮箱）
```

程序执行的记录文件在用户目录的`~\auto_login.py`中。

# 3. 登出校园网

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



