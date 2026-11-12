# 公开应用更新固件 v2.2.6-qianmo.2

整理与实测：浅默。AI协作：ChatGPT / Codex（教程、代码修改与排错协助）。
应用内版本仍显示2.2.6，qianmo.2是本次公开包的区分标识。整理日期：2026-11-12。

## 使用前先确认

适用硬件：本教程的官方StackChan/CoreS3，ESP32-S3、16MB Flash、8MB Quad PSRAM、GC0308。
本文件xiaozhi-public.bin是应用更新文件，不是全新设备首次刷入的完整镜像。必须已有匹配的引导程序、分区及资源文件，并确认当前活动应用槽。

实测分区：ota_0从0x20000开始、容量0x3f0000；ota_1从0x410000开始、容量0x3f0000；资源区从0x800000开始。不同设备或启动槽不能直接照抄地址。不要将应用文件写到0x0。

## 这次更新了什么

- 每次头像重绘后恢复显示顺序：头像在下，可见拍照预览在中，可见字幕在上。眨眼、换脸和恢复idle不会再把仍可见的字幕盖住。
- 非idle表情显示约5秒后自动恢复idle，新表情重新计时；眨眼不重置这个计时。关闭头像off会取消自动恢复。
- assistant字幕独立显示约8秒，新字幕重新计时；空状态消息及待命清理不提前结束该字幕，非空系统提示仍可替换它。
- 触摸表情也使用相同的5秒计时，取消旧的额外3秒恢复调用。
- 临时表情显示期间跳过自动眨眼，取消已开始的眨眼步骤，避免完整眨眼帧短暂替换表情；约5秒后恢复idle并按原设置继续眨眼。
- 保留原眨眼开关设置。恢复idle不代表强制打开已关闭的眨眼；连接后自动开启仍由VPS网关配置。
- 保留14帧公开几何表情，不包含私人冷脸。默认网关地址、备用地址和令牌仍为空，不强制覆盖使用者配置。
- 拍照预览仍保留原来的大小和约5秒时长；show_text仍属于VPS网关工具，固件不会代替网关注册工具。

计时由固件管理，不要求聊天AI等待5秒或8秒，也不需要结束后反复调用idle、show_text或say。

## 校验值

xiaozhi-public.bin：3630960字节

SHA-256：

28c9c2289d06b8b1264a2c03e04845a32f8086da76af8db1e406678241b8739b

公开版使用几何表情；包含私人头像的其他固件不能替代它发布。

## 备份和应用更新

在Windows PowerShell操作，COM3仅为本次设备串口。先关闭占用串口的程序，确认硬件、活动槽和分区，完成备份并校验大小。备份含私人设置，不公开。

本次历史环境esptool 5.3.1默认读取曾在固定位置中断，用--no-stub完成16MB备份，耗时约37分钟。不是所有设备都需要此选项：

    python -m esptool --chip esp32s3 --port COM3 --baud 115200 --no-stub read-flash --flash-size 16MB 0x0 0x1000000 "cores3-private-backup.bin"

在本附件所在目录，确认当前活动槽为0x20000且分区匹配后：

    Get-FileHash -LiteralPath ".\xiaozhi-public.bin" -Algorithm SHA256
    python -m esptool --chip esp32s3 --port COM3 --baud 460800 write-flash 0x20000 ".\xiaozhi-public.bin"

应显示Hash of data verified。保持原Wi-Fi/热点开启，重启时暂时不碰屏幕。仅写应用不会主动擦除设置区，可继续使用自己的原网络和网关配置。

## 功能测试与边界

- 2026-11-12公开几何版已在现有设备刷入并通过happy表情测试：显示期间不被眨眼打断，约5秒后恢复idle并继续眨眼。私人冷脸版随后同步修复、刷入并验证；私人文件不随本包公开。
- 本次显示计时版本在增加“临时表情暂停眨眼”前，已验证happy约5秒恢复、字幕独立约8秒消失且不被眨眼和换脸遮挡。最后一次眨眼补丁只改变板级眨眼条件；最终二进制没有再次完整重测所有相机、字幕和其他功能。
- 此前qianmo.1已验证连接、字幕、拍照预览和图片回传；不把历史测试等同于本版每项都重新测试。
- 同轮两工具调用曾出现设备已执行、客户端工具卡片长时间等待并报网络错误；单独调用字幕和表情可正常返回。并发结果或网络根因未确定，本包不宣称修复客户端或网关通信问题。
- 个人设备无触摸时曾自行摇头，关闭摸头感应后停止。该现象与本次显示修复分开记录，不声称为所有设备的共同故障，也没有修改舵机控制或触摸阈值。
- 全新设备首次安装、所有硬件和网络组合、全部六种表情及嘴形未逐一验证。不宣称解决此前所有WebSocket心跳超时。
- 8秒字幕功能针对本教程的非微信气泡UI、StackChan板型。其他源码结构应先核对，不盲目套补丁。

## 完整对应源码及构建

附件stackchan-public-v2.2.6-qianmo.2-source.tar.gz包含完整固件源码、实际sdkconfig、dependencies.lock、components、managed_components与各自许可。
11503个构建输入文件以11月8日VPS核对过的公开源码快照为基础，应用本次眨眼补丁；修改后的stackchan.cc与VPS编译前核对的SHA-256一致。另附发布说明、素材许可和文件哈希清单。省去旧失败构建和临时文件，不删减构建所需依赖。

来源：kisaragi-mochi/stackchan-mcp的firmware 2.2.6源码快照。历史父提交号未记录，不能据此推断某个上游tag。构建使用espressif/idf:v5.5.2，未承诺字节级重现。

在完整源码的firmware目录中，用Docker运行：

    docker run --rm --cpus=1 --memory=1400m --memory-swap=2800m --ulimit nofile=65536:65536 -e CMAKE_BUILD_PARALLEL_LEVEL=1 -v "$PWD":/project -w /project espressif/idf:v5.5.2 python ./scripts/release.py stackchan

已有本教程正确板型构建缓存时，本次增量命令为：

    idf.py -DBOARD_NAME=stackchan -DBOARD_TYPE=stackchan build

该命令应在上述IDF Docker环境内运行，不是Windows直接运行。完整镜像merged-binary.bin的首次安装没有在本次验证，不作为本包已测试成品提供。

GitHub自动生成的Source code(zip/tar.gz)只打包教程仓库，不能代替本附件的完整固件源码。

## 许可

上游和依赖保留原许可。新几何素材按LICENSE-GEOMETRIC-AVATAR-MIT.txt授权，教程非商业规则不覆盖它和既有软件的许可证。
本次仍选择CONFIG_STACKCHAN_SERVO_FEETECH=y，保留原SCServo_lib源码及其GPL文本，并使用对应的Feetech驱动构建分支。不能将所有第三方依赖统一声明为MIT。
发布时应用与完整对应源码共同提供，并保留许可与通知。只核查配置与文件不能代替实际功能测试。


[返回首页](../README.md)
