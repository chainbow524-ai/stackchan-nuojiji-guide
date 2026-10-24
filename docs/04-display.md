# 冷脸idle上的字幕和拍照预览

[返回首页](../README.md)

本章分成两个独立部分：VPS负责发送字幕文字；固件负责把字幕和相机预览摆到冷脸前面。**不能只改一边就认为所有显示问题都解决了。** 已经显示正常的用户无需重复修改。

## 1. 为什么冷脸会盖住文字和预览

个人自定义头像 `avatar_img_` 是全屏LVGL对象，显示表情时会提到前景。原有字幕条和拍照预览仍然存在，但可能被盖住。个人源码中三个对象挂在同一screen，显示字幕或预览时把对应对象再提到前景即可。

这不是所有版本都相同的对象结构。本章以个人2.2.6源码为参照，修改前核对函数和对象，不全局替换所有 `move_foreground`。

## 2. VPS 字幕工具需要哪些修改

先在糯叽机工具列表查 `show_text`。若已存在且能显示，直接跳到固件部分，不重复注册。

如果工具列表中没有 `show_text`，按下面步骤添加字幕工具；已经存在并正常使用的读者跳过本节。先查出当前网关实际使用的两个Python文件位置：

**位置：VPS终端。以下使用按第一章安装的uv工具。**

```bash
STACKCHAN_PY="$(uv tool dir)/stackchan-mcp/bin/python"
"$STACKCHAN_PY" - <<'PY'
import inspect
import stackchan_mcp.stdio_server as s
import stackchan_mcp.esp32_client as e
print('工具列表与分发文件：', s.__file__)
print('设备通信文件：', e.__file__)
print('Connection签名：', inspect.signature(e.ESP32Connection.send_tts_state))
print('Manager签名：', inspect.signature(e.ESP32Manager.send_tts_state))
PY
```

先复制这两个实际文件到带日期的私有备份目录。用 `nano 文件实际路径` 编辑时，只改下面对应函数和新注册项，保留其余代码。**这是维护说明，不是可直接粘贴整段替换整个文件的安装脚本。** 对不熟悉代码的读者，先让熟悉Python的人核对改动，再重启；本稿没有伪装成已经验证的通用一键补丁。

### 2.1 两层通信函数都支持可选text

`ESP32Connection.send_tts_state` 增加可选text参数；在原有message构造后、发送前加入text：

```python
async def send_tts_state(self, state: str, text: str | None = None) -> None:
    if not self._connected:
        raise ConnectionError("ESP32 not connected")
    message = {
        "session_id": self.session_id,
        "type": "tts",
        "state": state,
    }
    if text is not None:
        message["text"] = text
    await self._ws_send(json.dumps(message))
```

`ESP32Manager.send_tts_state` 同样增加text并转发：

```python
async def send_tts_state(self, state: str, text: str | None = None) -> None:
    if not self._connection or not self._connection.connected:
        raise ConnectionError("No ESP32 device connected")
    await self._connection.send_tts_state(state, text)
```

不要只改外层。原有不传text的调用仍使用默认None，保持原用法。

### 2.2 在工具分发处新增show_text

在 `stdio_server.py` 的 `_dispatch_mcp_tool` 内，沿用其他分支的缩进，新增：

```python
    if name == "show_text":
        text = arguments.get("text", "")
        if not isinstance(text, str) or not text.strip():
            return [TextContent(type="text", text=json.dumps({
                "ok": False, "error": "text is required"
            }))]
        await gateway.esp32.send_tts_state("sentence_start", text)
        return [TextContent(type="text", text=json.dumps({
            "ok": True, "text": text
        }, ensure_ascii=False))]
```

这里沿用固件已有文字消息，不发送音频，不需要调用 `say`。

在 `create_server()` 内 `list_tools()` 返回的工具列表里加入：

```python
            Tool(
                name="show_text",
                description="在StackChan屏幕显示文字，不播放语音；不要用say代替。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "minLength": 1},
                        "_actor": {},
                    },
                    "required": ["text"],
                },
            ),
```

`_actor` 是为了接收实际调用中可能附带的元数据，本工具不使用它。不要把整个arguments不加筛选地转给设备。工具列表与分发分支必须一起存在。

### 2.3 检查后重启

针对刚才查到的两个实际文件，用服务的Python执行 `python实际路径 -m py_compile 文件1 文件2`，检查成功通常无输出。若语法报错，先用备份恢复，不重启运行中的服务。

检查通过后：

```bash
sudo systemctl restart stackchan-mcp
sudo systemctl is-active stackchan-mcp
```

会短暂断开设备和客户端；刷新糯叽机MCP工具列表。先让它调用一次 `show_text`；若文字已发送但冷脸下仍看不到，再继续固件层级修复。

## 3. 准备固件源码

下面需要Docker编译环境，仅在确实需要固件修复时准备：

**位置：VPS终端。新建源码目录，不覆盖已有源码。**

```bash
git clone --recurse-submodules https://github.com/kisaragi-mochi/stackchan-mcp.git ~/stackchan-source
```

上游代码可能继续更新。编译前检查 `firmware/CMakeLists.txt` 中的应用版本及StackChan板型配置，并记录所下载的版本。本文修复对应2.2.6参考源码；如果目标函数或板型设置明显不同，先核对该版本说明，不强行套用。

若使用已有且适配本稿的源码，沿用它，不拉新主分支覆盖旧定制。自定义头像素材也先备份；本稿不打包个人素材。

下载源码ZIP可能缺少子模块。必须确认 `firmware/components/smooth_ui_toolkit` 不为空。Git克隆路线使用：

```bash
cd ~/stackchan-source
git submodule update --init --recursive
```

优先使用父仓库记录的子模块提交。历史救急曾单独克隆组件，但那样不能精确锁定原提交，不作为可复现的标准安装方式。

## 4. 修改显示层级

**位置：VPS终端，先进入实际源码的firmware目录。**

```bash
cd ~/stackchan-source/firmware
```

把下面整段复制运行。它会核对锚点、保留换行格式、备份源码，已加过的修改会跳过；锚点不符合预期时不会写入。

```bash
python3 - <<'PY'
from pathlib import Path
from datetime import datetime
import shutil
p = Path('main/display/lcd_display.cc')
before = p.read_bytes()
after = before
newline = b'\r\n' if b'\r\n' in before else b'\n'
changes = [
    (b'            lv_obj_remove_flag(bottom_bar_, LV_OBJ_FLAG_HIDDEN);',
     b'            lv_obj_move_foreground(bottom_bar_);'),
    (b'    lv_obj_remove_flag(preview_image_, LV_OBJ_FLAG_HIDDEN);',
     b'    lv_obj_move_foreground(preview_image_);'),
]
for anchor, added in changes:
    if added.strip() in after:
        print('已有：', added.strip().decode())
        continue
    if after.count(anchor) != 1:
        raise SystemExit('源码锚点不唯一或不存在，未写入。请核对当前版本。')
    after = after.replace(anchor, anchor + newline + added, 1)
if after == before:
    raise SystemExit('两项修复都已存在，无需重复修改。')
backup = p.with_name(p.name + '.before-display-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
shutil.copy2(p, backup)
p.write_bytes(after)
print('源码修改完成，尚未编译或刷机。备份：', backup)
PY
```

期望结果是：有文字时显示并提起字幕条；显示预览时提起预览图。没有修改预览大小和时间；参考源码的预览时长为约5秒，预览结束隐藏后露出头像。

## 5. 安装Docker并编译

**位置：VPS终端。**

```bash
command -v docker
```

已有Docker就跳过安装。没有时在Ubuntu运行：

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo docker pull espressif/idf:v5.5.2
```

看到 `Downloaded newer image` 或已存在的状态后，才算镜像可用。`Download complete` / `Extracting` 只是中间进度，不是失败。

### 第一次为该源码目录编译

仍在firmware目录，使用项目的板型构建脚本：

```bash
sudo docker run --rm --cpus=1 --memory=1400m --memory-swap=2800m \
  --ulimit nofile=65536:65536 \
  -e CMAKE_BUILD_PARALLEL_LEVEL=1 \
  -v "$PWD":/project -w /project \
  espressif/idf:v5.5.2 \
  python ./scripts/release.py stackchan
```

本资源限制取自个人2GB内存＋约2GB交换空间环境，不是适合所有机器的固定配置。`--cpus`约束CPU资源；环境变量是否控制某个生成器的全部任务并行，还受构建工具影响，不保证所有任务严格串行。

必须选 `stackchan`：预期芯片esp32s3、BOARD_TYPE_STACKCHAN、Quad PSRAM、GC0308相机。不要直接用缺少板型配置的 `idf.py set-target esp32s3 && idf.py build` 替代。

### 已有正确CoreS3配置，只改了一两行

只有同一目录已成功构建过正确板型，且没有改变配置，才使用增量构建：

```bash
sudo docker run --rm --cpus=1 --memory=1400m --memory-swap=2800m \
  --ulimit nofile=65536:65536 \
  -e CMAKE_BUILD_PARALLEL_LEVEL=1 \
  -v "$PWD":/project -w /project \
  espressif/idf:v5.5.2 \
  idf.py -DBOARD_NAME=stackchan -DBOARD_TYPE=stackchan build
```

正常会出现 `Project build complete`，并生成 `build/xiaozhi.bin`。只看“Project Version”或“name: stackchan”不足以判断成功，还要确认没有set-target failed等错误。

`[700/2000多] Building...` 通常是编译任务进度，不是下载两千个文件，也不是按任务数线性计算剩余时间。初次编译较慢，增量修改通常快些。

若上次配置失败导致build目录不完整，只在**已核对当前确实为目标firmware目录**后，保留改名：

```bash
pwd
sudo mv build "build-failed-$(date +%Y%m%d-%H%M%S)"
```

不要随手递归删除不明路径；这条命令也不是每次编译都要运行。

## 6. 校验并下载应用固件

**位置：VPS终端。**

```bash
ls -lh build/xiaozhi.bin
sha256sum build/xiaozhi.bin
```

保存这次输出，通过WebShell下载该文件到Windows电脑。旧文件同名时核对是否覆盖，尤其注意下载器可能变成 `xiaozhi (1).bin` 或 `xiaozhi .bin`。

**位置：Windows PowerShell。下面路径换成真实下载位置。**

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\实际下载目录\xiaozhi.bin'
```

必须与本次服务器哈希完全一致才继续。十六进制大小写不同不影响比较。个人某次修复镜像大小约3.5MiB，应用槽剩余约487KiB；那是该次构建数据，不是今后所有固件固定大小，也不是设备运行内存剩余量。

## 7. 备份并只更新应用

会重启设备。先按[设备章](02-device.md)完成备份，确认16MB设备、实际串口、当前分区与活动启动槽、所下载固件适配。以下地址只适用于已经确认的个人v2分区的活动ota_0，不是所有设备通用地址。

**位置：Windows PowerShell。替换端口和文件位置。**

```powershell
esptool --chip esp32s3 --port COM3 --baud 460800 write-flash 0x20000 'C:\实际下载目录\xiaozhi.bin'
```

写入期间不要断电或拔USB。正常结尾应有 `Hash of data verified` 和自动复位提示。本条只更新应用槽；不主动写分区表、NVS、OTA数据或素材区。它不保证不同固件之间所有配置和素材格式都兼容。

不要因为构建输出列出完整flash命令，就照抄包括0x0、0xd000、0x800000在内的所有写入项。

## 8. 验证与撤销

等待设备重新联网，确认：

1. 自定义头像正常。
2. `show_text`字幕显示在头像前方。
3. `take_photo`能返回图片，预览短暂出现后隐藏。
4. 原来的相机与其他已用功能仍可运行。

同轮切换表情再显示字幕时，先 `set_avatar`，后 `show_text`；换脸仍可能重新提起头像。拍照预览是短暂预览，不把这一行修改说成实时视频流或永久全屏。

撤销源码修改时先核对那份备份之后有没有其他改动，再恢复并重新编译。VPS字幕扩展则只恢复相关Python文件并重启网关；不要拿过旧备份覆盖后来新加的功能。
