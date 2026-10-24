# 常见问题与日常开关机

[返回首页](../README.md)

先辨认失败在哪一段：**糯叽机 → 公网HTTPS入口 → VPS网关 → 设备长连接 → 照片上传 → 图片交给聊天模型**。不要把所有故障都归结成“重新配网”。

## 1. 服务器active，但机器人没连上

active只是进程运行。看最近的设备连接记录：

**位置：VPS终端。**

```bash
sudo journalctl -u stackchan-mcp --since "5 minutes ago" --no-pager -o cat |
grep -E 'ESP32 (connecting|ready|disconnected)|connection (open|closed)' |
tail -12
```

看日期和时间。无输出不等于服务坏了，也不等于ready。需要时再看 `sudo systemctl status stackchan-mcp --no-pager`。完整日志可能含工具列表、设备ID或其他私人信息，发给别人前脱敏。

## 2. 又进配网、一直初始化、黄色默认脸

启动时不要碰屏幕；本版短触可能触发配网。Wi-Fi连接等约60秒超时后也可能进入配网。先确认热点名称、密码、2.4GHz兼容性、信号及供电。黄色脸与待命字样不单独证明设备到VPS已经连通。

已进入配网模式且确实需要更新Wi-Fi时，可以按正常流程重新选择网络并保存；不恢复出厂。没有证据表明每次VPS超时都必须重新配网。

设备备份命令是读取操作，不主动擦除Wi-Fi；读取后的复位可能重新触发启动和网络问题。不要把先后发生误当成“备份擦掉设置”。

## 3. 连接时好时坏、ping通但443不通

**位置：电脑Windows PowerShell。域名和IP换成你自己的。**

```powershell
Test-NetConnection mcp.example.com -Port 443
Resolve-DnsName mcp.example.com -Type A -DnsOnly
```

再用你在云控制台确认的VPS公网IP直接测试443，以区分解析和访问路径问题。ping成功不代表TCP443也成功。

要和设备比较，电脑必须连同一个热点，并说明是否开了VPN。校园网成功不能证明手机热点可达；关闭VPN后DNS缓存或软件代理状态也可能暂时不同，不用一条结果就断言运营商屏蔽。

服务器侧检查：

```bash
systemctl is-active caddy
sudo ss -lntp 'sport = :443'
sudo ufw status verbose
```

还要检查云防火墙/安全组。没有证据前不“一键放通全部端口”。个人曾出现域名解析结果不同、热点443失败后又成功，最终原因未查明，不写成已经证实的永久性故障。

## 4. Windows curl出现CRYPT_E_REVOCATION_OFFLINE

它表示Windows无法完成证书吊销查询，不自动说明服务器证书一定坏了。可做一次针对性测试：

```powershell
curl.exe --ssl-revoke-best-effort -I --connect-timeout 10 --max-time 20 https://mcp.example.com/
```

该参数允许吊销查询离线时继续，其余证书校验仍保留；只影响这次curl，不修改系统设置。不要为了测试而永久关闭证书检查。

根路径未带令牌返回401可能是WebSocket认证的预期反应，但这仍不是成功的WebSocket升级，也不是设备当前在线的证明。

## 5. ESP32 auth rejected、401和403

先核对**这条日志到底是谁触发的**。电脑无令牌curl测试也会产生auth rejected；不要拿它当设备Token必定错误的证据。

设备真实认证失败时，再核对网关STACKCHAN_TOKEN、固件保存的Gateway Token和客户端MCP令牌。VISION_TOKEN若单独设置，还需与相机初始化提供的值对应。

403要按错误内容区分Host、Origin检查以及客户端的请求方式。个人日志曾同时出现OPTIONS403与实际POST成功，不能见到任意一个403就断言所有工具都不可用，也不直接全放通来源。配置MCP_HTTP_ALLOWED_HOSTS时以实际请求来源为准，不把不同网关的变量名混用。

不发送完整令牌。改配置后重启相关进程，客户端按需刷新；不要盲目轮换其他服务的Key。

## 6. 参数校验提示_actor不被允许

这属于参数检查，尚未到拍照或模型。个人新增工具曾写additionalProperties=false，而实际调用附带_actor，导致拒绝。

修复只让该工具接收并忽略_actor，仍检查question或text，不把元数据原封不动发给设备。改schema后重启网关、刷新客户端工具列表。

## 7. 拍照返回Failed to connect to explain URL

固件在建立照片上传连接时抛出这条错误。它不是外部模型拒绝图片，也不能单独说相机传感器坏了。

先看初始化时给设备的上传地址：

```bash
sudo journalctl -u stackchan-mcp --since "15 minutes ago" --no-pager -o cat |
grep -E 'Gateway started:|vision_url=|Capture upload auth rejected' |
tail -5
```

VISION_URL应是公网 `https://域名/capture`。核对Caddy这一路由指向8766，且不删除/capture路径。

如果地址正确，需要在相机调用发生时读取设备串口，区分DNS/TCP/TLS超时、连接内存或其他错误。不凭概括错误直接重配所有网络、关闭认证或改模型。

## 8. 怎么读取设备日志

**位置：Windows PowerShell。设备通过USB数据线连接电脑。**

先枚举端口：

```powershell
python -X utf8 -m serial.tools.list_ports -v
```

把下面COM3换成实际端口。读取期间不主动拨动DTR/RTS来复位设备：

```powershell
@'
import serial, time
s = serial.Serial()
s.port = 'COM3'
s.baudrate = 115200
s.timeout = 1
s.dtr = False
s.rts = False
s.open()
print('Recording for 90 seconds. Trigger the photo tool now.', flush=True)
try:
    end = time.monotonic() + 90
    while time.monotonic() < end:
        line = s.readline()
        if line:
            print(line.decode('utf-8', errors='replace').rstrip(), flush=True)
finally:
    s.close()
'@ | python -X utf8 -
```

看到Recording后，立即在糯叽机触发一次相机调用。结束后保留失败时前后约20行。只有周期内存输出通常不足以解释连接失败；开机日志需采集工具启动后再正常重启设备，并处理USB重新枚举。

如果读取时COM口消失，先枚举再重试，不在看不到端口时反复烧录。90秒只是采集时长，不是对设备配置的修改。

## 9. 只有图片路径，角色说看不到

看[直接看图章](03-direct-photo.md)。确认调用take_photo、图片块是否返回、糯叽机是否把它交给支持图片输入的模型。不要让角色猜服务器路径里的文件内容。

`[image content omitted]` 与后续实测出现的 `[image #1 returned ... attached as a picture]` 不是同一含义；以当次实际客户端行为为准。

## 10. 字幕或预览又被遮住

先验证拍照是否返回图片、show_text是否正常。再检查运行中的固件是否真的包含move_foreground修改，是否只是编译了还没刷入。

换表情可能再次提起头像。同轮先换表情再显示字幕。预览只在原定时长内显示，不永久替代头像。

## 11. 眨眼开过，重启后又没了

本版固件开关不是持久保存的开机默认值。可调用set_blink(true)，或者按[自动眨眼章](05-auto-blink.md)让网关在默认头像初始化成功后自动调用。

做过补丁却失效时，查是否升级/重装覆盖文件、当前会话是否跳过默认头像初始化，以及素材是否完整。不要先重刷整个设备。

## 12. 找不到smooth_ui_toolkit，或fullclean失败

缺组件通常是源代码子模块不完整，不是字幕那行C++错误。优先初始化递归子模块，普通源码ZIP可能不带它；不要不核对父仓库引用就取组件最新提交当成相同环境。

上次配置失败后，idf.py可能拒绝清理build。确认目标firmware目录后改名保留，再重试构建；不要全盘递归删除。

## 13. 外部识图502，或更换请求方式后结果不同

优先复用已经成功的同机识图实现，对照URL、模型、认证、请求体及运行环境。单凭502不足以断言图片能力不支持。个人没有定位Python与Node请求差异的最终根因。

如果直接看图已成功，主路线不需要继续排这个备用接口问题。

## 14. 工具数量不同、刷新后仍找不到

设备工具数、网关客户端工具数和已缓存列表可能不同。先检查实际注册，再刷新客户端MCP并确认角色启用服务，不按53这个数字判断所有版本。

新增工具的列表注册和分发逻辑要一起存在。升级后直接修改在site-packages中的扩展可能消失。

## 15. 今天用完可以关什么

- 可以关闭电脑PowerShell、云控制台和WebShell网页；systemd服务不依赖这些窗口。
- 想让机器人继续在线，VPS实例、网关与Caddy服务、设备电源和Wi-Fi要保持可用。
- Docker编译命令用了--rm，结束后容器会退出并清理，不用因此关整台服务器。
- 设备可以正常关机，下次先开热点再开机。USB若是唯一供电，拔线会关机；换其他供电后不需要连电脑。
- 私下保留源码、配置和Flash备份，不清理仍被其他服务使用的目录。

## 16. 已明确要求使用工具，却连调用卡片都没有

糯叽机聊天页面里，是否发起MCP工具调用通常由当前聊天AI结合问题、人设和可用工具判断。工具已启用不代表角色每一轮都会调用。

先确认当前角色启用了这台MCP服务，客户端工具列表中确实有目标工具，连接状态正常。再明确说明要用哪个工具，例如：

> 请实际调用 StackChan 的 take_photo，拍摄一张新照片后回答。不要只口头描述或假装已经调用。

如果已明确要求使用工具，仍没有出现任何调用卡片，可以尝试换一个工具调用能力更好的模型（也就是更“聪明”、更擅长执行工具的模型）；直接看图还要确认模型支持图片输入。必要时刷新MCP列表或新开对话测试。

**连卡片都没出现时，先检查聊天模型和客户端是否真正发起了调用，不要因此先重刷机器人或反复配网。** 出现卡片但卡片里返回错误，才继续按对应的网络、设备或接口错误排查。若客户端本身有连接报错，也应先处理连接，而不是把一切都归因于模型。


## 17. 备份Flash在固定位置中断，降低速度或分段也不行

本次实际遇到的是刷入前的读取备份故障：Windows、esptool 5.3.1、ESP32-S3、USB-Serial/JTAG、COM3。默认方式读取16MB时，反复在地址0x001b9000附近停止，可能显示：

```text
A fatal error occurred: Packet content transfer stopped
A fatal error occurred: No more data to read from the serial port.
```

降低波特率到115200没有解决。单独读取前1MB成功，但分16段读取时，第二段仍在相同地址附近失败，因此本次没有继续反复降低速度或缩小分段。

这些提示表示该次备份没有完成。即使出现Hard resetting via RTS pin，也不能把它当成备份成功；不完整文件不能用于完整恢复。read-flash是读取操作，本次没有因此写入或擦除应用固件。

本次改用 `--no-stub`，先读经过故障地址的64KB，再完整读取16MB成功。它绕过默认临时读取程序，使用芯片自带读取功能；此结果支持读取路径兼容问题的可能性，但没有确认最终根因，也不能仅凭该报错判断Flash硬件损坏。上游有[类似读取故障记录](https://github.com/espressif/esptool/issues/1155)，不代表本次必然是同一问题。

**位置：Windows PowerShell。先确认实际串口，替换COM3与保存路径。** 文件名用新的，避免覆盖已有完整备份；关闭其他占用串口的程序，保持电脑不休眠、数据线稳定。

```powershell
python -m esptool --chip esp32s3 --port COM3 --baud 115200 --no-stub read-flash --flash-size 16MB 0x0 0x1000000 "cores3-private-backup-nostub.bin"
```

本次实际用时2244秒，约37分24秒，不是几分钟。不同设备、连接和读取方式的速度会不同；正常前进时不要仅因较慢就拔线。成功输出包含：

```text
Read 16777216 bytes from 0x00000000 ...
Hard resetting via RTS pin...
```

核对备份文件大小为16777216字节，再记录SHA-256。完整备份可能含Wi-Fi和令牌，不上传GitHub。若这个方式仍失败，保留末尾报错，先检查连接、供电和工具版本，不跳过备份直接擦除或刷写。

本次后续应用写入使用默认stub成功，用时约19秒，并出现 `Hash of data verified`；读取失败不等于写入必然失败，也不要求把备份用的所有参数照搬到刷写命令。

## 18. 读取或刷写后出现黄脸、配网画面，是否设置没了

串口操作结束可能自动重启。先确认原来使用的热点或Wi-Fi仍开启，并给设备启动、重连留出时间，暂时不要触摸屏幕。黄脸可以是启动时的原生界面，不能仅凭外观判断设置已丢失。

本次进入配网模式时，有一次确认是手机热点被关闭；重新打开原热点后再检查。不要因此立刻改网关令牌、重新刷机或清空设置。若原网络开启后仍不能恢复，再按设备日志和已安装固件的配网说明排查。

公开版只更新应用，保留原设置区，所以本次设备能继续使用原Wi-Fi、网关地址和令牌；这不代表公开固件内写入了作者的配置。新设备使用者仍须填写自己的配置。

## 19. 刷好后会眨眼，但糯叽机调用超时

眨眼说明此前开启过动画，不保证此刻设备与网关仍连接。本次出现过 `keepalive ping timeout`，设备重启后服务器重新出现 `ESP32 ready`，随后字幕和拍照调用恢复成功；根因没有确认，不宣称重启能解决所有超时。

先保持热点开启，在VPS终端查看新连接事件：

```bash
sudo journalctl -u stackchan-mcp -f -n 0 -o cat |
grep --line-buffered -E 'ESP32 ready|ESP32 disconnected|auth rejected'
```

本次通过重新启动设备恢复连接。出现新的 `ESP32 ready` 后按Ctrl+C只会停止日志查看，不会停止网关服务；再回客户端调用show_text或take_photo验证。

如果刚运行命令后没有输出，可能只是尚无新事件；这条命令只显示之后发生的匹配日志，不自动证明服务有故障。若持续不恢复或提示认证失败，继续检查对应日志，别把所有问题都归因于模型，也别无依据修改令牌。
