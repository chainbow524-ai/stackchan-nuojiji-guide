# 可选：独立外部识图的配置、安装与停用

[返回首页](../README.md)

**已经能用take_photo直接看图的人可以跳过本章。** 只有希望保留备用路线，或者当前聊天模型不能直接读取MCP图片时，才需要独立识图服务。

本章所有材料都在本教程仓库中，不需要另一份教程、其他网关或别的项目代码。新增的 `take_photo_and_analyze` 在一次工具调用内完成拍照和外部识图，返回文字给糯叽机的聊天AI。

**验证范围：旧的个人方案已在设备上成功运行；本章重新整理的独立版经过本地模拟检查，尚未在真实VPS和付费接口上完成端到端复测。** 本地检查覆盖了11项Python侧场景、临时目录中的安装/检查/卸载/重装，以及Node请求格式、图片输入和错误处理；未调用真实付费API。Python子进程和路径检查部分在Windows受限环境采用替身，Linux服务权限与真实接口仍需VPS验证。因此请分步检查输出，不直接覆盖你已经正常工作的同名旧工具。下面安装器遇到已有同名工具会停止。

## 1. 先准备三项资料

| 资料 | 填什么 | 注意 |
| --- | --- | --- |
| Base URL | 服务商提供的兼容API基础地址，常见形式为 `https://你的服务商域名/v1` | 不填StackChan的/capture，也不要重复加/chat/completions |
| 模型名 | 你账户中实际可用、支持图片输入的完整名称 | 名称及权限以你正在用的接口为准，不只是模型家族名称 |
| API Key | 该识图服务商生成的密钥 | 不发给AI、不放到截图、不上传GitHub |

可以使用自己已经成功识图的服务，但不要求大家使用浅默同一家平台。外部识图会把拍到的照片发送给你配置的服务商，可能产生额外接口费用。

主路线take_photo不使用这把外部Key。VPS原来的 `VISION_URL=https://你的域名/capture` 保持不变，那是相机照片上传入口。

## 2. 把配套文件放到VPS

**位置：VPS文件管理器及终端。**

把本仓库文件上传/解压到 `~/stackchan-nuojiji-guide/`。目录名可以不同，但下面命令必须对应实际目录。不要用旧安装包覆盖正在运行的网关。

检查这四个文件：

```bash
cd ~/stackchan-nuojiji-guide
ls -l scripts/configure-external-vision.py scripts/vision-client.mjs \
  scripts/external-vision.py scripts/install-external-vision.py
```

找不到文件时先检查上传位置，不继续安装。这里的脚本属于可选工具扩展，VPS基础网关和设备连接应先按前面章节完成。

## 3. 检查Node和网关用户

**位置：VPS终端。**

```bash
node --version
command -v node
sudo systemctl show stackchan-mcp -p User
whoami
```

本独立版以Node22或24为参考，复用Node内置fetch，不需要额外npm安装识图库。系统已有合适版本就不要重新安装。

如果没有Node，在Ubuntu按[NodeSource官方说明](https://github.com/nodesource/distributions)安装。下面是Node22路线，已有其他Node部署时先评估，不为本教程随意覆盖：

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/stackchan-node-setup.sh
sudo bash /tmp/stackchan-node-setup.sh
sudo apt-get install -y nodejs
node --version
```

配置文件保存在当前用户的主目录；运行网关的User应与配置时的用户一致，例如都是ubuntu。不同用户的 `~` 不同，不能在root家目录生成密钥后，期待ubuntu服务自动读到。

## 4. 私下填写独立识图配置

**位置：VPS终端，仍在本教程目录。**

```bash
python3 scripts/configure-external-vision.py
```

依次输入Base URL、模型名和API Key。输入Key时不显示字符，这是正常的。已有配置时留空会保留对应旧值；第一次配置必须填完整。

脚本把资料写进：

```text
~/.config/stackchan-vision/config.json
```

该目录和文件只给当前用户访问；配置脚本会保存已有配置的私有备份。它不修改网关.env，不重启服务，也不会主动调用付费模型。不要把这个JSON文件上传或粘贴出来。

例：若服务商提供的Base URL是 `https://api.example.com/v1`，脚本随后请求的地址会是 `https://api.example.com/v1/chat/completions`。这是格式示例，运行时用你自己的真实接口，不直接填写示例域名。

## 5. 先用已有照片测试独立接口

先通过现有take_photo拍一张照片，确认VPS已收到相机JPEG。即使当前聊天模型不能看图，也可以先确认工具返回照片路径和大小。

下面只读取VPS里最新的一张**已有照片**做测试，不会重新拍照，会发出一次外部识图请求，可能计费：

```bash
node scripts/vision-client.mjs --latest
```

成功应返回类似：

```json
{"ok":true,"description":"这里是这张已有照片的识别描述。"}
```

描述应符合你刚才拍到的东西。若返回ok=false，先处理其中错误，不继续装组合工具。HTTP401要核对Key和权限，HTTP502要结合服务商记录排查，不能看到一个状态码就认定模型不支持图片。脚本不会自动重复收费请求。

本次测试读取的是已有照片；只有下一节安装后的组合工具才会在每次调用中拍摄新照片。

## 6. 安装独立组合工具

本步骤针对已核对源码结构的 `stackchan-mcp 0.18.0`。安装器会再核对版本、拍照注册项及分发函数，备份后只添加两个接入区块；不会重刷固件，也不删除字幕、表情或自动眨眼改动。

先找到实际工具Python：

```bash
STACKCHAN_PY="$(uv tool dir)/stackchan-mcp/bin/python"
test -x "$STACKCHAN_PY"
```

正常没有输出。若失败，先确认uv和安装位置，不拿系统Python代替该虚拟环境。

```bash
"$STACKCHAN_PY" scripts/install-external-vision.py
```

期望输出“已安装独立识图工具接入”和备份位置。安装器不会自动重启网关。

如果提示“已存在同名工具”，说明这份网关已经注册了take_photo_and_analyze。**先停止，不覆盖，不重复安装。** 已有版本能用就沿用；需要迁移到独立版时，先单独核对原来的备份与卸载办法，不通过删除整个程序目录解决。

然后做不调用模型的结构检查：

```bash
"$STACKCHAN_PY" scripts/install-external-vision.py --check
```

只有看到 `CHECK PASSED` 才继续。检查只能确认接入与配置存在，不能代替真实拍照识图验证。

## 7. 重启并在糯叽机测试

**此步骤会短暂断开设备和客户端的网关连接。**

```bash
sudo systemctl restart stackchan-mcp
sudo systemctl is-active stackchan-mcp
```

输出active后，保持设备热点、电源开启，等待重新连接；在糯叽机刷新/重连MCP工具列表。

移开相机遮挡，对准一个容易辨认的新物品，发送：

> 请只调用 take_photo_and_analyze，question="请描述这次新拍摄的画面。" 根据返回描述回答，不要再调用take_photo或其他识图工具。

看返回内容里的ok是否为true，description是否符合这次新画面。绿勾本身不能代替检查内容。客户端和模型的等待时间可能不同，完整用时取决于拍照上传、外部模型及网络，不承诺固定秒数。

组合工具只使用本次拍照回执中的有效路径。若上传失败，它会停止，不会拿上次的旧照片冒充新拍摄，也不会调用外部模型。_actor等附加元数据不会发给相机。

## 8. 以后单独撤下

如果直接传图已经满足需求，可以在人设中优先take_photo；想从服务端真正撤下本章独立版工具，运行：

```bash
cd ~/stackchan-nuojiji-guide
STACKCHAN_PY="$(uv tool dir)/stackchan-mcp/bin/python"
"$STACKCHAN_PY" scripts/install-external-vision.py --uninstall
```

看到已撤下后，再重启网关并刷新糯叽机工具列表：

```bash
sudo systemctl restart stackchan-mcp
sudo systemctl is-active stackchan-mcp
```

它只移除本独立版工具的两个接入区块，保留配置、工作文件和备份供恢复；不会删除原拍照工具、字幕、头像或自动眨眼，也不需要刷机。如果标记不匹配，安装器会停止，不拿旧文件强行覆盖其他版本。

不再需要的私有识图Key可以在服务商平台按需停用，但先确认它是否也被你自己的其他程序使用。备份和密钥文件不要作为公开仓库附件。

## 9. 快速排错

| 返回或现象 | 优先检查 |
| --- | --- |
| 尚未拍照，独立配置不完整 | 服务用户、配置路径、Node绝对路径、配套工作文件 |
| 未收到本次照片有效路径 | 原take_photo调用、设备到/capture的连接及网关日志 |
| 外部识图HTTP401/403 | 外部API Key、账户/模型权限，不是MCP令牌 |
| 外部识图HTTP502 | 服务商上游状态和同机实际请求差异，不直接断言模型无图片能力 |
| 45秒或55秒超时 | 模型和网络耗时、客户端等待范围；先查执行结果，不反复点击 |
| 客户端没有调用卡片 | 聊天AI是否发起工具调用、模型工具能力、角色启用设置；见排错章 |

本脚本不把服务商原始错误正文、Key或整张Base64图像写进返回结果，避免排错时泄露资料。修改独立配置后下一次调用会重新读取；更改工具代码则仍需重启网关并刷新客户端。
