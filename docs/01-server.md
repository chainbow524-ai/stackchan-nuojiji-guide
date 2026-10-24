# VPS 网关与 HTTPS 基础部署

[返回首页](../README.md) · 上一步：[分清操作位置](00-before-you-start.md)

本章是给新建 Ubuntu VPS 的参考部署路线。个人现有网关已实测，**下面整套全新环境安装流程尚未单独从零复测**。命令经过源码对照整理；不等于所有 Ubuntu、云厂商网络和糯叽机版本都验证过。已有 `stackchan-mcp` 服务的用户先看第1节，不要照着覆盖配置。

本文以网关0.18.0为基准。不要为了排错随手改成最新版；后续版本可能已经改变工具、认证和补丁位置。

## 1. 检查服务器，不先安装

**位置：VPS 终端。**

```bash
whoami
pwd
python3 --version
sudo systemctl status stackchan-mcp --no-pager
```

- 已显示 `active (running)`：优先保留当前服务，去客户端验证 `get_status`，不要重复安装第二个实例。
- 提示服务不存在：新服务器属于正常情况，可以继续。
- `sudo` 或登录账号有问题：先解决权限，不把所有命令随手换成 root 执行。

接下来使用 `~` 表示当前普通用户主目录。示例常见用户为 `ubuntu`，并不要求每个人都使用这个用户名。

## 2. 安装基础工具和 uv

**位置：VPS 终端，仅新服务器执行。**

```bash
sudo apt-get update
sudo apt-get install -y curl ca-certificates git unzip nano
```

正常应完成软件包安装并回到提示符。如果第三方软件源出现402、签名错误等，先处理出错的软件源；不要关闭签名验证或反复粘贴整套部署命令。已有服务不需要因为更新索引失败而卸载重装。

安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/stackchan-uv-install.sh
sh /tmp/stackchan-uv-install.sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

安装脚本来自 [uv官方安装文档](https://docs.astral.sh/uv/getting-started/installation/)。如果你已经装好 uv，跳过安装即可。

安装本教程参考版本。Ubuntu 22.04系统自带的Python可能过旧，这里让 uv 使用 Python3.12：

```bash
uv tool install --python 3.12 'stackchan-mcp==0.18.0'
stackchan-mcp --help
stackchan-mcp serve --help
```

看到帮助且存在 `serve --transport streamable-http` 才继续。若版本不可取得、依赖安装失败或缺少该运输方式，先停下核对，不随意改成其他命令。安装入口与项目来源见 [stackchan-mcp上游仓库](https://github.com/kisaragi-mochi/stackchan-mcp)。

## 3. 创建独立配置目录和令牌

**位置：VPS 终端，仅目标目录尚不存在时执行。**

```bash
mkdir -m 700 ~/stackchan-gateway
```

如果提示目录已存在，先检查内容，不覆盖已有 `.env`。

在本机文件中生成随机令牌，不把它显示在终端输出：

```bash
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path.home() / 'stackchan-gateway' / '.env'
if p.exists():
    raise SystemExit('已有 .env，停止，未覆盖。')
with p.open('x') as f:
    f.write('STACKCHAN_TOKEN=' + secrets.token_urlsafe(32) + '\n')
    f.write('BEARER_TOKEN=\nHOST=127.0.0.1\nWS_PORT=8765\nCAPTURE_PORT=8766\n')
    f.write('VISION_URL=https://mcp.example.com/capture\nVISION_TOKEN=\n')
    f.write('MCP_HTTP_HOST=127.0.0.1\nMCP_HTTP_PORT=8767\n')
    f.write('MCP_HTTP_ALLOWED_HOSTS=mcp.example.com\n')
p.chmod(0o600)
print('配置已生成；请在服务器本地编辑域名并保存自己的令牌。')
PY
nano ~/stackchan-gateway/.env
```

把里面两处 `mcp.example.com` 换成你的实际域名。把令牌保存在自己的密码管理器，后面填设备和糯叽机时使用同一个值。

如果客户端请求携带 Origin，`MCP_HTTP_ALLOWED_HOSTS` 还需要加入该请求实际的来源域名（按需包含端口），以逗号分隔。这个变量按本版源码接受主机名/主机名加端口，不填完整页面路径。不要套用其他网关的配置变量名；本程序使用上述字段。

## 4. 生成 systemd 服务

**此步骤创建开机自启服务；会启动网关。已有同名服务不要执行。**

先检查：

```bash
sudo systemctl cat stackchan-mcp
```

如果已经显示有效服务内容，停止创建并沿用现有配置。确认是新服务器后，运行：

```bash
STACKCHAN_BIN="$(command -v stackchan-mcp)"
STACKCHAN_USER="$(id -un)"
test -n "$STACKCHAN_BIN" && test -x "$STACKCHAN_BIN"
```

最后一条成功时可能没有输出。若找不到程序，先修好 PATH，不继续。

```bash
sudo tee /etc/systemd/system/stackchan-mcp.service >/dev/null <<EOF
[Unit]
Description=StackChan MCP Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$STACKCHAN_USER
WorkingDirectory=$HOME/stackchan-gateway
EnvironmentFile=$HOME/stackchan-gateway/.env
ExecStart=$STACKCHAN_BIN serve --transport streamable-http
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now stackchan-mcp
sudo systemctl is-active stackchan-mcp
```

正常输出 `active`。若失败，查看 `sudo journalctl -u stackchan-mcp -n 30 --no-pager`，先排掉依赖、端口、路径、配置问题。

检查内部监听：

```bash
sudo ss -lntp | grep -E ':(8765|8766|8767)\b'
```

按本例应能看到三个端口在本机监听。不要同时另开一个前台 `stackchan-mcp` 抢占同一组端口。

## 5. 域名和公网防火墙

在域名控制台创建 A 记录指向 VPS 的实际公网 IPv4。没有正常配置 IPv6 时，不保留指向错误服务器的 AAAA 记录。

云服务器安全组/防火墙需要允许公网 TCP80和443，SSH22按你自己的维护方式设置。这里不要求公开8765、8766或8767，它们只供本机反向代理使用。

`sudo ufw status verbose` 显示 inactive，只说明UFW没启用，不等于云厂商防火墙也没有限制。

## 6. 安装和配置 Caddy

**位置：VPS 终端，仅没有 Caddy 的新服务器。**

```bash
sudo apt-get install -y caddy
```

已有 Caddy、网站或其他网关时，不重新安装、不清空 `/etc/caddy/Caddyfile`。先备份：

```bash
sudo cp -a /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.before-stackchan-$(date +%Y%m%d-%H%M%S)"
sudo nano /etc/caddy/Caddyfile
```

向文件中添加下面这个独立站点块。必须替换域名；若已有同域名站点，把对应路由合并进去，不再创建重复站点。不同域名的现有站点保留。

```caddyfile
mcp.example.com {
    handle /mcp* {
        reverse_proxy 127.0.0.1:8767
    }
    @capture_routes path /capture /avatar_set/*
    handle @capture_routes {
        reverse_proxy 127.0.0.1:8766
    }
    handle / {
        reverse_proxy 127.0.0.1:8765
    }
    handle {
        respond "Not found" 404
    }
}
```

这里使用 `handle` 保留原路径，不是删掉 `/capture` 前缀后再转发。Caddy会处理 WebSocket 代理，不需要额外改成HTTP明文公网入口。

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl is-active caddy
```

**只有 validate 成功后才执行 reload。** 最后应显示active。DNS尚未生效、端口占用、网络不通时，证书申请可能失败；按日志排查，不卸载其他站点服务。Caddy的写法依据[官方反向代理文档](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)。

## 7. 先验证入口，再接设备

**位置：VPS终端。替换域名后执行。**

```bash
curl -i --connect-timeout 10 --max-time 20 https://mcp.example.com/mcp
curl -i --connect-timeout 10 --max-time 20 -X POST https://mcp.example.com/capture
```

未携带令牌时，按本例启用认证后应看到401，表示相应HTTP服务有响应，不是完整工具调用成功。如果返回502，查反向代理目标服务；若超时，查DNS、路径、防火墙和网络。只有根路径有响应，不足以证明 `/capture` 路由也正确。

## 本章检查点

- 服务active，三个内部端口正常。
- Caddy配置校验通过，域名HTTPS能得到服务响应。
- 已保存真实令牌，未把它提交到GitHub。
- `VISION_URL` 是公网 `/capture` 地址，而不是 `127.0.0.1` 或外部视觉模型URL。

下一步：[设备联网与固件准备](02-device.md)。
