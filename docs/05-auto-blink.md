# 连接成功后自动眨眼

[返回首页](../README.md)

个人固件中自动眨眼初始关闭，网关会话初始化后原本只设置idle头像。我们改成：默认头像设置成功后，再调用固件已有的 `self.display.set_blink`，enabled为true。

**本章的方法是在连上VPS后自动开启眨眼，不需要重新刷机，也不增加工具数量。** 固件也可以改成在头像初始化后默认开启自动眨眼，不必等待VPS发出开启指令；这需要修改固件、重新编译并验证头像帧和启动流程。个人版与公开版v2.2.6-qianmo.1均保持前一种方法，本教程不修改为离线启动默认开启。

## 1. 先试现有工具

在糯叽机发：

> 请只调用 set_blink，enabled=true。不要调用其他工具。

观察约10秒。该工具开启的是随机约3～6秒的自动眨眼，不是立刻眨一次、指定次数或单眼眨眼。若素材不含对应眼睛帧，单靠设置开关不能补出素材。

若你只需要本次开机期间眨眼，这样就足够。下面才是每次新连接自动开启的修改。

## 2. 核对版本和现有方法

**位置：VPS终端。**

```bash
STACKCHAN_PY="$(uv tool dir)/stackchan-mcp/bin/python"
"$STACKCHAN_PY" - <<'PY'
import inspect
import importlib.metadata
import stackchan_mcp.esp32_client as m
print('版本：', importlib.metadata.version('stackchan-mcp'))
print('文件：', m.__file__)
print(inspect.getsource(m.ESP32Manager._auto_render_idle_avatar))
PY
```

本章针对0.18.0且具有该方法的个人源码结构。若版本不同、方法不存在或已经有自动眨眼代码，停止套用，不重复添加。

## 3. 备份并添加自动开启

**下面修改VPS安装包中的Python代码，但不自动重启服务。**

```bash
"$STACKCHAN_PY" - <<'PY'
import ast
from pathlib import Path
from datetime import datetime
import shutil
import importlib.metadata
import stackchan_mcp.esp32_client as m
if importlib.metadata.version('stackchan-mcp') != '0.18.0':
    raise SystemExit('不是本文核对的0.18.0，停止。')
p = Path(m.__file__)
text = p.read_text()
if 'BEGIN STACKCHAN_AUTO_BLINK' in text:
    raise SystemExit('已添加过，未重复修改。')
tree = ast.parse(text)
classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ESP32Manager']
if len(classes) != 1:
    raise SystemExit('找不到唯一ESP32Manager，停止。')
methods = [n for n in classes[0].body if isinstance(n, ast.AsyncFunctionDef) and n.name == '_auto_render_idle_avatar']
if len(methods) != 1:
    raise SystemExit('找不到唯一头像初始化方法，停止。')
fn = methods[0]
if [a.arg for a in fn.args.args] != ['self', 'connection', 'device_id']:
    raise SystemExit('方法参数不同，停止。')
segment = ast.get_source_segment(text, fn)
if '_SET_AVATAR_TOOL' not in segment or 'if error:' not in segment:
    raise SystemExit('头像初始化逻辑不同，停止。')
addition = '''
        # BEGIN STACKCHAN_AUTO_BLINK
        if error:
            return
        try:
            _blink_result, blink_error = await connection.call_tool(
                "self.display.set_blink", {"enabled": True}
            )
            if blink_error:
                logger.warning("auto-blink failed: device=%s error=%s", device_id, blink_error)
            else:
                logger.info("auto-blink enabled: device=%s", device_id)
        except Exception as exc:
            logger.warning("auto-blink failed: device=%s error=%s", device_id, exc)
        # END STACKCHAN_AUTO_BLINK
'''
lines = text.splitlines(keepends=True)
lines.insert(fn.end_lineno, addition)
updated = ''.join(lines)
compile(updated, str(p), 'exec')
backup = Path.home() / 'stackchan-backups' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-auto-blink')
backup.mkdir(parents=True)
shutil.copy2(p, backup / p.name)
temporary = p.with_suffix('.py.blink-new')
temporary.write_text(updated)
temporary.chmod(p.stat().st_mode)
temporary.replace(p)
print('修改成功，语法检查通过；服务尚未重启。备份：', backup)
PY
```

显示修改成功才继续。该方法原有“已经显式设置头像则跳过默认头像”的逻辑保留；本文没有改成无论任何状态都强行重置用户表情。

## 4. 重启网关验证

**会短暂断开设备和客户端，不重启其他服务。**

```bash
sudo systemctl restart stackchan-mcp
sudo systemctl is-active stackchan-mcp
```

保持设备电源和热点开启，等连接恢复及头像出现，再观察约10秒。此时不用让角色再调用set_blink。个人设备已验证自动开始眨眼。

必要时查看：

```bash
sudo journalctl -u stackchan-mcp --since "3 minutes ago" --no-pager -o cat |
grep -E 'ESP32 ready|auto-blink' |
tail -10
```

`auto-blink enabled`表示网关调用未收到协议错误，最终仍以设备实际行为确认。动画设置不是通过本补丁写进设备NVS；如果用户本次调用set_blink(false)，下一次新的默认头像初始化仍可能重新开启。

## 5. 撤销和升级

临时停止本次眨眼：调用 `set_blink(enabled=false)`。想永久撤销本章自动开启逻辑，需在服务代码中只移除 `BEGIN STACKCHAN_AUTO_BLINK` 至 `END STACKCHAN_AUTO_BLINK` 的整个标记区块，再语法检查和重启服务。

如果使用备份整文件恢复，先确认这份备份之后没有字幕或其他新修改；有的话不要整文件覆盖。升级或重装Python包可能覆盖本补丁，升级后需要重新检查，不重复盲装。
