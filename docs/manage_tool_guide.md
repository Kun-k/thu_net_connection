# 一键管理工具 使用文档

本文档只覆盖本仓库提供的 **一键管理工具**（入口: `python manage.py`）。
它把 README.MD 中的「步骤 0 ~ 4」全部打包成一个交互式工具，并同时提供
**终端菜单** 与 **浏览器 Web 面板** 两种使用方式，二者功能等价。

---

## 1. 安装

```bash
# 1) 进入项目目录
cd /path/to/thu_net_connection

# 2) 安装依赖 (Python 3.8+)
pip install -r requirements.txt

# 3) 运行
python manage.py
```

依赖清单 (见 `requirements.txt`)：

| 包 | 用途 |
| ---- | ---- |
| `cryptography` | 使用 Fernet 对凭证的用户名/密码/邮箱授权码等字段进行对称加密存储 |
| `flask` | Web 面板服务 |

> 首次运行时会自动执行 **步骤 0**：把 `TunetZRRZ2025_linux/Tunet_linux2025/auth-client`
> 和 `.auth-setting` 复制到 `~/`，并赋予 `auth-client` 可执行权限。
> 如果检测到已经完成则直接跳过。

---

## 2. 终端菜单

启动后看到主菜单：

```
=========== 校园网自动登陆 管理工具 ===========
  1. 管理凭证 (encrypt)
  2. 查看服务状态
  3. 启动服务 (并开机自启动)
  4. 关闭服务 (并取消开机自启动)
  5. 在浏览器查看
  6. 退出
```

每次选择一项后，终端会**清屏并只显示当前功能的内容**；操作完成后按回车返回主菜单。

### 2.1 管理凭证（选项 1）

子菜单：`1) 添加  2) 查看  3) 编辑  4) 删除  5) 返回主菜单`

凭证存储在 `credentials/` 目录，形如 `.<ConfigName>.encrypted_cred`，敏感字段使用
`credentials/.cred_key` 里的 Fernet 密钥加密。每个凭证包含字段：

| 字段 | 说明 |
| ---- | ---- |
| `ConfigName` | 配置名（用于生成文件名，必填且建议英数字） |
| `ServerName` | 服务器名称，仅用于邮件通知正文 |
| `UserName` / `PassWord` | 校园网账号 / 密码（加密） |
| `CheckInterval` | 检查网络的间隔（秒），默认 120 |
| `EmailAddress` / `EmailAuthCode` | 用于状态通知的邮箱账号 / 授权码（加密） |
| `EmailSmtpServer` / `EmailSmtpPort` | 默认 `smtp.qq.com` / `465` |
| `PythonPath` | 运行 `run_auto_login_autostart.py` 所用的 Python 解释器路径 |

#### 添加
按提示依次输入字段；`PythonPath` 为空时默认使用 `sys.executable`。

#### 查看
**会显示明文用户名 / 密码 / 邮箱授权码**，所以进入前会二次确认。

#### 编辑
- 直接回车保留当前值；密码类字段（`PassWord` / `EmailAuthCode`）空回车亦保留原值。
- 如果所选凭证**正被运行中的服务使用**，会出现额外选项：
  1. 不编辑
  2. 编辑并重启服务
  3. 编辑但不重启服务（当前 encrypt 已写入后台）
  4. 编辑并终止服务

#### 删除
- 普通情况二次确认后删除文件。
- 若是**运行中的服务正在使用的凭证**：
  1. 不删除
  2. 删除并终止服务
  3. 删除但不终止服务（当前 encrypt 已写入后台）

### 2.2 查看服务状态（选项 2）

输出 `systemctl is-active` 的状态、使用的凭证文件名，并追加完整的 `systemctl status auto_login.service` 输出。

### 2.3 启动服务（选项 3）

流程：

1. 若服务已在运行，提示"已在运行，使用凭证 X，是否重新设置?"；重新设置会先 stop + disable。
2. 若无任何凭证，自动跳入"添加凭证"流程。
3. 若存在多个凭证，提示选择一个。
4. **校验 `PythonPath` 是否真实可执行**（`shutil.which` 或绝对路径 + `os.access(X_OK)`）。
   不可执行时会提示重新输入，并自动建议当前系统上找到的 `python3` / `python` 路径。
   新路径会**写回凭证**，下次启动不再提示。
5. 写出 `sh_run_auto_login_autostart.sh`（使用 `PythonPath`）。
   若文件存在且被 root 拥有（比如之前以 sudo 运行过），自动回退到 `sudo tee` 写入，然后 `chown` 回当前用户、`chmod 755`。
6. 使用当前 `getpass.getuser()` + `os.path.abspath(.)` 生成 `auto_login.service`：
   ```ini
   [Unit]
   Description=Auto Login Service
   After=network.target

   [Service]
   Type=simple
   ExecStart=<项目目录>/sh_run_auto_login_autostart.sh
   Restart=always
   User=<当前用户>
   WorkingDirectory=<项目目录>

   [Install]
   WantedBy=multi-user.target
   ```
7. `sudo tee` 写入 `/etc/systemd/system/auto_login.service`，再执行
   `systemctl daemon-reload && enable && reset-failed && start`。
   `reset-failed` 用于清除上一次可能残留的 "Start request repeated too quickly" 标记。

### 2.4 关闭服务（选项 4）

`systemctl stop && disable` + 删除 `/etc/systemd/system/auto_login.service` + `daemon-reload`。

### 2.5 在浏览器查看（选项 5）

1. 提示输入端口（1024~65535，非法则循环重试）。
2. 询问是否需要局域网访问 —— 选择后决定 bind `127.0.0.1` 还是 `0.0.0.0`。
3. 生成一次性访问密钥（`secrets.token_urlsafe(24)`），**仅本次显示**。
4. **自动复制到系统剪贴板**：依次尝试 `pbcopy` (macOS) / `clip` (Windows) /
   `xclip` / `xsel` / `wl-copy` (Linux)。
   成功则显示"密钥已复制到剪贴板"；否则提示手动选中复制，并建议在 Linux 上安装
   `xclip`（`sudo apt install xclip`）。
5. 打印访问地址（本机 + 局域网 IP）。
6. 回车后启动 Flask，Ctrl+C 停止并返回主菜单。

---

## 3. 浏览器 Web 面板

选项 5 启动后，用浏览器访问提示的 URL。

### 3.1 登录

在登录页粘贴刚才的密钥。密钥每次启动 Web 服务都会**重新生成**（也会在选项 3
每次启动 auto_login.service 时刷新）。

### 3.2 状态面板（默认标签）

| 卡片 | 内容 |
| ---- | ---- |
| 服务状态 | `systemctl is-active` 结果（badge 颜色随状态变化） |
| 使用凭证 | `credentials/.ConfigNameAutoStart` 指向的凭证文件 |
| 本机 IP | 通过 UDP socket 连 223.5.5.5 探测 |
| 公网 IP | 调用 `curl ifconfig.me` / `ip.cn` |

下方展示 `auto_login.log` 末 200 行日志，整个面板每 5 秒自动刷新。

### 3.3 凭证管理 标签

- **新建凭证**：弹窗表单，各字段含义与终端版一致。
- **查看**：点击"查看"后会有二次确认，然后弹出解密后字段（包括明文密码）。
- **编辑**：`ConfigName` 不可改；`PassWord` / `EmailAuthCode` 留空表示保留原值；
  若该凭证正被服务使用，保存时会弹出冲突选择（与终端版对应）：
  - 保存修改但不重启服务
  - 保存修改并重启服务
  - 保存并终止服务
- **删除**：非使用中直接二次确认；使用中弹出：
  - 删除并终止服务
  - 删除文件但保留服务运行

### 3.4 服务控制 标签

- 下拉选择凭证 → 点击"启动 + 开机自启"。
- 点击"停止 + 取消自启"关闭服务。

> **sudo 密码提示在终端窗口出现。** 因为 `manage.py` 通过子进程调用 `sudo systemctl ...`，
> 第一次使用时 sudo 会在**运行 `manage.py` 的那个终端**弹出密码输入。Web 请求会阻塞
> 等待密码输入完成，请保证终端可见且可输入。若不想每次都输密码，可在 `visudo`
> 里配置 `NOPASSWD: /usr/bin/systemctl, /usr/bin/tee, /usr/bin/chown, /usr/bin/chmod, /usr/bin/rm`
> （仅针对需要的命令）。

### 3.5 HTTP API（供调试）

登录后 session 有效，均为 JSON。

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/api/status` | 服务状态 / IP / 日志末尾 |
| GET | `/api/creds` | 凭证列表 + 服务状态 + 当前激活凭证 |
| GET | `/api/creds/<name>` | 解密后的凭证详情 |
| POST | `/api/creds` | 新建 (body = 字段 JSON) |
| PUT | `/api/creds/<name>` | 更新，可附 `_action: nothing\|restart\|stop` |
| DELETE | `/api/creds/<name>?action=default\|stop\|keep` | 删除 |
| POST | `/api/service/start` | body: `{"cred_name": "..."}` |
| POST | `/api/service/stop` | 停止并 disable |

---

## 4. 权限与 sudo

- **步骤 0**（复制 auth-client）：不需要 sudo，写到用户 Home。
- **凭证 CRUD**：不需要 sudo，`credentials/` 在项目目录内。
- **启动/停止服务**：需要 sudo，`systemctl` + 写 `/etc/systemd/system/`。
  工具自动 `sudo systemctl / sudo tee / sudo rm`，密码在终端输入。
- 若以 `root` 身份直接运行（`os.geteuid() == 0`），则内部跳过 `sudo`。

---

## 5. 文件结构（新工具相关）

```
manage.py                           # 一键管理工具入口
encrypt_cred.py                     # 凭证 CRUD + 加解密；新增非交互式 from_dict 方法
web_view.py                         # Flask 蓝图（登录、状态、凭证、服务控制 API）
templates/
  ├── login.html                    # 密钥登录页
  └── index.html                    # 三标签页：状态 / 凭证 / 服务
requirements.txt                    # cryptography + flask

credentials/                        # 运行时生成 (git-ignored)
  ├── .cred_key                     # Fernet 密钥 (600)
  ├── .<ConfigName>.encrypted_cred  # 加密凭证 (600)
  ├── .ConfigName                   # 手动运行使用的凭证
  ├── .ConfigNameAutoStart          # 自启服务使用的凭证
  └── .access_key                   # 当前 Web 面板的一次性密钥

sh_run_auto_login_autostart.sh      # 由工具自动生成, exec <PythonPath> run_auto_login_autostart.py
/etc/systemd/system/auto_login.service  # 由工具自动生成 + 安装
auto_login.log                      # 运行日志, 被 Web 面板读取末尾展示
```

---

## 6. 故障排查

### 6.1 `Permission denied: sh_run_auto_login_autostart.sh`
该文件之前被 root 拥有。新版已自动回退到 sudo 写入并改回当前用户，如仍失败：
```bash
sudo rm -f sh_run_auto_login_autostart.sh
python manage.py   # 重新执行选项 3
```

### 6.2 服务 `failed (exit-code 127)`
127 表示 `sh_run_auto_login_autostart.sh` 里的 Python 路径不存在。典型场景：
凭证里的 `PythonPath` 写成了 Windows 风格或 `python`，而 Linux 上没有该命令。

现在选项 3 会**预检**可执行性并提示重新输入。也可手动修正：
```bash
which python3                              # 找到可用路径
# 然后"管理凭证 → 编辑 → PythonPath"填入
```

### 6.3 "Start request repeated too quickly"
systemd 在短时间内多次失败触发限流。选项 3 现在会在 start 前执行
`systemctl reset-failed auto_login.service`。如果你手动 `systemctl start` 仍报这个：
```bash
sudo systemctl reset-failed auto_login.service
sudo systemctl start auto_login.service
```

### 6.4 Web 面板一启动 sudo 就提示密码
这是预期行为（服务启停需要 root）。想免密参考 §3.4 末尾的 `NOPASSWD` 配置建议。

### 6.5 Web 面板打开后看不到日志
`auto_login.log` 只在服务启动后产生。还未启动过服务时日志文件可能不存在。

### 6.6 局域网其他设备访问不到
- 确认选项 5 时选择了"局域网访问"（bind `0.0.0.0`）。
- 放行相应端口的防火墙规则，例如 `sudo ufw allow 8080/tcp`。

---

## 7. 退出与卸载

- **退出工具**：主菜单选 `6` 或 `Ctrl+C`。
- **停服务**：主菜单选 `4`，会 `stop + disable + 删除 service 文件`。
- **彻底清理凭证**：`rm -rf credentials/`（注意：会丢失全部加密凭证）。
