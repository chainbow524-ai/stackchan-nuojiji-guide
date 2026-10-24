# 设备联网与固件准备

[返回首页](../README.md) · 上一步：[VPS基础部署](01-server.md)

## 1. 本教程使用的固件来源

浅默刷入的是基于 [kisaragi-mochi/stackchan-mcp](https://github.com/kisaragi-mochi/stackchan-mcp) 仓库中 `firmware/` 源码自行编译的StackChan固件，应用版本显示2.2.6；在此基础上加入了本教程的字幕与拍照预览层级修复，并保留自定义头像。因此它属于基于该仓库源码的个人修改版，不是声称直接刷了上游最新、未经修改的成品固件。

### 个人版与公开应用更新版

个人冷脸素材不公开。公开版 **v2.2.6-qianmo.1** 已重新编译为14帧几何表情，并在同一设备上通过应用更新验证字幕、预览、拍照传图、happy/idle切换及网关连接后眨眼。应用内仍显示2.2.6。

仓库中的 `firmware/xiaozhi-public.bin` 仅用于匹配设备的应用更新；[公开固件说明](public-firmware.md)包含文件哈希、硬件与分区条件、备份及刷写命令、测试范围。对应的完整源码包需随固件上传到本仓库GitHub Releases，本版对应源码与校验值见[GitHub Releases](https://github.com/chainbow524-ai/stackchan-nuojiji-guide/releases)。

默认网关地址、备用地址和令牌为空，不强制覆盖已有配置。读者须配置自己的Wi-Fi、网关和令牌。仅更新应用保留原设置区时，设备可继续连接先前配置的服务器，这不代表公开固件内含浅默的连接信息。完整Flash备份含私人数据，不得公开。

第一次使用的读者应先确认手上设备已安装适配该硬件的固件。仅有CoreS3或看到黄色脸，不能证明包含相同的MCP功能。

- 已经能连接自己的网关：保留现有固件，先完成直接看图测试。
- 原厂设备或其他固件：先读[上游安装与发布说明](https://github.com/kisaragi-mochi/stackchan-mcp#quick-start)和[固件发布页](https://github.com/kisaragi-mochi/stackchan-mcp/releases)，确认硬件、分区、素材及所选发布版本匹配后再做初次安装。
- 本稿没有附带一个“所有设备通用”的整片固件，也不把初次刷机与保留设置的应用更新混成同一条命令。第一次安装的完整流程应以所选上游版本为准。

CoreS3的16MB Flash、8MB PSRAM等硬件信息可参考[M5Stack设备文档](https://docs.m5stack.com/en/core/CoreS3)。8MB容量不表示PSRAM工作模式可以随意选，本文实测板型使用Quad。

## 2. 配置 Wi-Fi 和远程网关

**位置：手机和设备配网页面，不是电脑 PowerShell。**

1. 先打开设备要连接的2.4GHz Wi-Fi或手机热点，再给设备开机。
2. 初次配网时，按所装固件的引导连接设备临时热点；上游文档说明其配置门户常用 `http://192.168.4.1`。
3. 填写真正可用的Wi-Fi名称及密码。
4. 在 Advanced / 高级设置中，填写本版支持的 WebSocket Gateway URL 和 Gateway Token。

| 字段 | 本教程的值 |
| --- | --- |
| WebSocket Gateway URL | `wss://mcp.example.com/`，换成你的域名 |
| Gateway Token | 与VPS `STACKCHAN_TOKEN`相同的值 |
| Fallback Gateway URL | 本路线不要求配置，已有有效备用设置不要随手清除 |

例如：假设你已拥有 `1234.com`，并已将它解析到这台VPS，表中地址应分别填写：

| 用途 | 完整输入示例 |
| --- | --- |
| 设备WebSocket Gateway URL | `wss://1234.com/` |
| 糯叽机MCP服务地址 | `https://1234.com/mcp` |
| VPS中的VISION_URL | `https://1234.com/capture` |

协议名是 **`wss`**，不是`wws`。这里的域名应是完整的 `1234.com`，而不是只输入`1234`；如果你实际配置的是子域名 `mcp.1234.com`，三个地址也要对应换成该子域名。示例不能代替自己拥有并配置好的真实域名。

这里填根路径的WSS地址，不填客户端的 `/mcp`，也不填 `/capture`。界面若没有这些字段，先核对固件版本，不在源码里到处硬编码地址。

按该固件说明保存配置并启动/重启。个人固件启动时短触屏幕可能进入配网，因此正常开机时先别碰屏幕。网络连接超时约60秒也可能进入配网；这不自动意味着Wi-Fi记录被擦除。

## 3. 看服务器是否真正连接成功

**位置：VPS终端。**

```bash
sudo journalctl -u stackchan-mcp --since "5 minutes ago" --no-pager -o cat |
grep -E 'ESP32 (connecting|ready|disconnected)|connection (open|closed)' |
tail -12
```

正常应有新的 `ESP32 ready`。注意日期时间，不把几小时前的ready当成当前在线。日志没有输出只说明时间范围里没有匹配记录，不能凭此直接判断设备坏了。

本版网关在会话初始化后会尝试设置 `idle` 头像；冷脸出现是有帮助的现象，但正式确认仍用日志和实际工具调用。原厂素材可能不是浅默自定义的冷脸。

## 4. 电脑读取串口

只有排错或刷机才需要这一节。普通使用无需一直开着电脑终端。

**位置：Windows PowerShell。**

```powershell
python -X utf8 -m serial.tools.list_ports -v
```

没有Python/pyserial时，先安装Python并运行 `python -m pip install pyserial esptool`。个人刷机工具为esptool5.x；旧版参数命名可能不同，先看版本和帮助。

本次设备曾显示COM3、USB VID:PID=303A:1001。但你的端口可能是COM4等，要使用实际列表中的编号。

- `FileNotFoundError`：读取时那个串口不存在，重新枚举。
- `PermissionError / Access denied`：可能被其他串口程序占用，也可能是运行环境权限限制；先关串口监视器/烧录网页，再用本机PowerShell验证。
- 串口短暂消失：USB CDC重枚举、设备重启或供电变化都可能有关，不立即恢复出厂。

## 5. 全量备份

**会短暂重启设备。确认端口、USB数据线和文件保存位置后再执行。**

下面使用用户“文档”目录，在Windows里先设置备份目录：

```powershell
$stackchanBackupDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'StackChanBackups'
New-Item -ItemType Directory -Force -Path $stackchanBackupDir | Out-Null
$stackchanBackupFile = Join-Path $stackchanBackupDir ('before-update-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bin')
```

替换COM3为实际端口后运行：

```powershell
esptool --chip esp32s3 --port COM3 --baud 460800 read-flash 0x0 0x1000000 "$stackchanBackupFile"
```

本例仅适用于已确认16MB Flash的设备。个人完整读取约159秒，其他环境耗时不同。正常输出 `Read 16777216 bytes`，之后自动复位。记录备份路径，把文件私下保存；Flash备份可能含网络配置等私密信息，不能作为GitHub公开附件。

## 6. 什么时候才刷应用固件

读完[显示修复章](04-display.md)，明确需要更新后才操作。对于个人已确认的v2分区，应用槽从0x20000开始，容量0x3f0000，另有NVS、OTA数据和素材区。并非所有设备都相同；若活动启动槽在别处，只写0x20000不保证实际启动到新固件。

只有确认当前分区、启动槽、固件板型和文件哈希正确，且备份完成后，才使用应用更新命令。不要把上游构建输出的一整套刷写地址不加区别地照抄到日常更新；那可能包含分区、OTA数据和素材。

下一步：[直接看图测试](03-direct-photo.md)。
