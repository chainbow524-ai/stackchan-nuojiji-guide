# 可选：准备自己的头像素材

[返回首页](../README.md)

已经喜欢现有头像的人可以跳过。**本教程和公开固件都不提供浅默个人的冷脸素材**；当前教程包也没有收录效果截图。公开版使用新生成的14帧几何表情，素材许可见公开固件说明。自己制作或取得适当授权的素材后，可按本章替换。

将图片编译进固件也属于把素材随文件提供给下载者。只隐藏原图或不上传 `avatar_images.local.cc`，不能保证固件中的图像无法被提取；因此公开版必须从不含私人素材的源码重新构建。

## 1. 六种表情和完整动画帧

本文所参考的本地转换脚本支持14张PNG。下面名字必须与脚本一致，使用相同画布、背景、人物位置和4:3比例，避免切换时跳动：

| 分组 | 文件名 |
| --- | --- |
| 六种表情 | idle.png、happy.png、thinking.png、sad.png、surprised.png、embarrassed.png |
| 眨眼 | eyes_open.png、eyes_half.png、eyes_closed.png |
| 五种嘴形 | mouth_closed.png、mouth_half.png、mouth_open.png、mouth_e.png、mouth_u.png |

参考画布为320×240；该本地脚本默认缩小到160×120，转成RGB565。这里的眼睛帧和嘴形帧是**完整头像画面**，不是只放两只透明眼睛的小贴片；脚本和固件通过整帧切换显示。

即使本教程不配置机器人语音，按这条14帧转换路线仍要准备脚本要求的五张嘴形文件。它们不会因为存在就自动播放声音。

## 2. 转成固件本地覆盖文件

这是**编译进固件**的路线，修改素材后要重新编译刷入。另一种动态load_avatar_set路线见第4节，两者不要混为一谈。

先在VPS准备 `~/stackchan-avatar/` 并上传14张PNG。它们不是写进教程仓库的必需文件，公开分享前另核对素材权利。

**位置：VPS终端。假设源码目录为第四章的~/stackchan-source。**

```bash
cd ~/stackchan-source
ls firmware/scripts/avatar_convert/convert_avatars.py
```

如果所选版本没有该脚本或参数不同，停止照抄，核对对应上游版本。脚本存在时查看帮助：

```bash
python3 firmware/scripts/avatar_convert/convert_avatars.py --help
```

为转换工具准备独立环境，避免修改网关依赖：

```bash
sudo apt-get install -y python3-venv
python3 -m venv ~/stackchan-image-tools
~/stackchan-image-tools/bin/python -m pip install Pillow
```

先备份已有的 `firmware/main/boards/stackchan/avatar_images.local.cc` 和 `.h`；若不存在则不需要备份这两个文件。确认后再执行转换：

```bash
~/stackchan-image-tools/bin/python firmware/scripts/avatar_convert/convert_avatars.py \
  --src "$HOME/stackchan-avatar" \
  --out-dir firmware/main/boards/stackchan
```

默认输出为 `avatar_images.local.cc` 和 `avatar_images.local.h`。不要加 `--tracked` 去覆盖公共占位文件。若缺图片，脚本会提示missing source，补齐后再运行，不把不完整输出当成功。

默认14×160×120×2，总像素数据为537600字节。这个数是像素数据，不是生成的C++文本文件大小，也不是最终固件体积；.cc文本大很多属于正常情况。

## 3. 编译和设备验证

确认所用版本的CMake确实支持 `avatar_images.local` 本地覆盖，再按[显示修复章](04-display.md)用stackchan板型编译、检查分区容量、校验下载、备份和更新。

逐项测试六种表情、自动眨眼、字幕和相机预览。素材全帧位置不一致时，眨眼可能像换了整张脸；这是素材设计问题，不通过乱改眨眼开关解决。

## 4. 已有动态换脸工具怎么办

0.18.0本地schema还包含 `load_avatar_set`，可让设备通过网关暂存接口下载头像数据。它要求VPS上的raw RGB565包，不接受PNG目录、.cc文件或普通ZIP直接冒充：

- layered：14帧，537600字节。
- matrix：90帧，3456000字节。

需要按该版本文档和协议规定的顺序打包，且 `archive_path` 是服务器路径。不能凭文件后缀改名就转换格式。

上游实现把下载数据放进PSRAM，因此不应未经核对就承诺动态换脸在断电后仍保持。希望开机不依赖再次下载时，应核对编译内置素材或另行验证自动重载机制。本稿不提供一个未经复测的动态打包一键脚本。

个人历史曾先动态换脸，后来编译源码中也带有本地素材。新读者应选择明确的一条路线，并记录素材究竟来自哪一层，不拿某次冷脸出现推断所有装法都能永久保存。
