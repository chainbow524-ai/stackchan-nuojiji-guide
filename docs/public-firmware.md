# 公开固件 v2.2.6-qianmo.1

整理：浅默。应用内版本仍显示2.2.6；qianmo.1区分本次公开包，不代表上游新增版本。整理日期：2026-10-25。

## 适用范围

实测硬件：M5Stack官方StackChan/CoreS3，ESP32-S3、16MB Flash、8MB Quad PSRAM、GC0308相机。

本包提供应用更新文件xiaozhi-public.bin，不是首次安装所需的完整整片镜像。仅适用于已有匹配引导程序、分区和资源文件的设备。不要写到0x0。其他型号及全新设备首次安装未实测。

实测设备ota_0起点0x20000、容量0x3f0000；ota_1起点0x410000、容量0x3f0000；资源区起点0x800000。须确认当前活动启动槽，不能仅凭“都是CoreS3”照搬地址。

## 内容与改动

- 字幕bottom_bar_及拍照预览preview_image_显示时提到前景，保留原有预览大小和时长。
- 使用14帧程序绘制的几何表情，包含六种表情、眼睛和嘴形帧，不包含浅默私人冷脸素材。
- 默认网关地址、备用地址及令牌为空，不强制覆盖设备已有网关配置。读者须配置自己的Wi-Fi、网关和令牌。
- 眨眼启动逻辑保持原样，本次实测由VPS网关连接后开启。仅刷此固件不代表断网开机就会眨眼。
- show_text属于VPS网关工具，固件显示修复不能代替网关添加字幕工具的步骤。

## 实测结果

2026-10-24浅默在现有设备更新应用后确认：连接网关、自动眨眼、happy/idle表情切换、字幕显示、拍照预览、take_photo图片回传及聊天模型识图成功；触摸后出现脸红反应。

未逐一测试全部六种表情、所有嘴形、运动参数或断线恢复场景。本次曾发生WebSocket心跳超时断线，重启设备后恢复ready并通过调用；未确定根因，不宣称已修复所有连接问题。

完整新装、所有硬件与网络组合尚未实测。现有VPS的字幕与自动眨眼补丁不是应用固件的一部分，须按教程另行配置。

## 校验与更新

应用文件3630304字节，SHA-256：

d4afc04337a846f4c47771992208355a93fc441a5207a8bc36fe6f175e137462

先确认硬件、分区、活动槽及备份。COM3只是本次实测串口，其他电脑须替换。在Windows PowerShell、固件所在目录中操作。

先备份；完整备份可能含Wi-Fi和令牌，不能上传。本次esptool 5.3.1默认读取在固定位置中断，改用--no-stub后成功读取16MB。该方式较慢，不表示所有设备都需要：

    python -m esptool --chip esp32s3 --port COM3 --baud 115200 --no-stub read-flash --flash-size 16MB 0x0 0x1000000 "cores3-private-backup.bin"

确认备份成功且大小16777216字节。仅当活动槽确认为0x20000且分区匹配时：

    Get-FileHash -LiteralPath ".\xiaozhi-public.bin" -Algorithm SHA256
    python -m esptool --chip esp32s3 --port COM3 --baud 460800 write-flash 0x20000 ".\xiaozhi-public.bin"

应出现Hash of data verified。保持原Wi-Fi/热点开启，重启时不触摸屏幕。只写应用不主动擦除NVS；这也是本次保留旧连接配置的原因，不代表固件内含个人配置。需要恢复外观时，用保留的个人应用更新同一已确认槽位，不用其他人的整片备份恢复。

## 源码、构建与许可

来源：[kisaragi-mochi/stackchan-mcp](https://github.com/kisaragi-mochi/stackchan-mcp)的firmware源码快照，PROJECT_VER 2.2.6。历史父提交号未记录，不声称对应某个精确上游tag。

同附stackchan-public-v2.2.6-qianmo.1-source.tar.gz包含本次实际构建源码、sdkconfig、dependencies.lock、components与managed_components，保留许可证。剔除旧失败构建日志和临时产物，未改变本次构建代码、素材或配置；添加发布说明、几何头像许可及文件哈希清单。

解压进入firmware目录，用Docker espressif/idf:v5.5.2运行上游脚本：

    docker run --rm --cpus=1 --memory=1400m --memory-swap=2800m --ulimit nofile=65536:65536 -e CMAKE_BUILD_PARALLEL_LEVEL=1 -v "$PWD":/project -w /project espressif/idf:v5.5.2 python ./scripts/release.py stackchan

镜像按版本tag记录，未保留本次digest，不承诺字节级重现。脚本可能生成merged-binary.bin；本次未验证其初次安装，不将它作为已测试成品发布。

各上游与依赖保留原许可证。原SCServo_lib文件仍随源码保存，并保留其GPL文本；本次CONFIG_STACKCHAN_SERVO_FEETECH=y对应CMake分支排除SCS.cc、SCSCL.cc、SCSerial.cc，使用components/feetech_scs（MIT）驱动。不据此把全部依赖统一标作MIT。

新几何头像按LICENSE-GEOMETRIC-AVATAR-MIT.txt授权。教程非商业规则不覆盖这些软件、固件和素材原有的授权。发布应用时同时提供本包对应源码和许可；大源码包应作为GitHub Release附件提供，而不是省略。

## 核查范围

实际构建配置中的默认WebSocket地址和令牌为空。已扫描成品与源码中的已知个人部署标记及常见密钥形式，未发现匹配；对照14帧私人冷脸像素，公开应用中未发现相同完整帧；公开头像像素已在应用中找到。此检查与源码隔离构建共同用于核查，不把一次字符串扫描称为绝对无泄露证明。



[返回首页](../README.md)
