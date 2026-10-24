# 来源与致谢

教程整理、个人部署和实测：**浅默**。AI编程助手协助代码修改、排错及教程编写。本教程不把上游软硬件及其原有功能声明为浅默原创。

## 上游软硬件

- [stack-chan](https://github.com/stack-chan/stack-chan)：原始社区机器人项目，Shinya Ishikawa于2021年发起的项目背景由stackchan-mcp上游说明介绍。
- [M5Stack StackChan](https://docs.m5stack.com/en/StackChan)：硬件平台。
- [M5Stack CoreS3](https://docs.m5stack.com/en/core/CoreS3)：设备硬件参数参考。
- [kisaragi-mochi/stackchan-mcp](https://github.com/kisaragi-mochi/stackchan-mcp)：MCP网关、设备适配、相机和表情等主要上游功能来源。
- [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32)：固件基础。
- [Forairaaaaa/smooth_ui_toolkit](https://github.com/Forairaaaaa/smooth_ui_toolkit)：个人源码引用的子模块，应按父仓库记录的提交及自身许可使用。
- [LVGL](https://github.com/lvgl/lvgl)：显示界面库。
- [Caddy](https://caddyserver.com/)与[uv](https://docs.astral.sh/uv/)：教程部署所用工具。

## 这份实践记录包含什么

- 在个人设备和网络环境中部署、验证并整理新手操作顺序。
- 在既有网关上添加并验证静音字幕工具。
- 修改字幕及拍照预览的LVGL前景顺序，并编译刷入验证。
- 在个人网关中让默认头像初始化成功后开启自动眨眼。
- 实测直接通过take_photo返回MCP图片，并由糯叽机当前聊天模型识别。
- 历史上添加过可单独撤下的拍照＋外部识图工具，现作为可选备用说明。

为让读者独立配置备用识图，本次修订另整理了仓库scripts目录中的独立配置和安装脚本；它们与历史个人实现分开标明验证范围。

这些属于基于上游的配置、修改及实践整理，不代表整个项目或相关算法由浅默独立原创。

## 许可边界

本稿核对的本地stackchan-mcp许可文本说明：仓库主体采用MIT，并对若干SCServo_lib文件作GPL-3.0例外说明。上游同时存在驱动替换和构建配置演进，不能仅凭同名固件版本就判断某个二进制实际链接了哪些组件。

本版配套提供公开应用更新固件v2.2.6-qianmo.1和本次实际构建对应源码包；须同时上传至GitHub发布页并保留其中上游及各依赖的许可。固件说明记录实际选择的Feetech驱动配置，不能只附教程许可替代软件许可。新几何头像的MIT许可另附，不受教程非商业条款限制。

[本地所参考上游许可文本副本](licenses/stackchan-mcp-LICENSE.txt)仅为本稿记录，不代表所有后续版本。实际使用以上游相应版本为准。

用户个人头像与照片未打包到本稿，不推定拥有对其中所有角色、商标、人物等元素的公开再授权。界面截图正式收录前需遮去私人信息并核对使用范围。

## 写作方式

本文采用准备材料、分步操作、预期结果、错误分流和验证范围的组织方式；读者只需本教程及其配套文件即可阅读，不要求取得另一份教程。

## 在线参考

- [stackchan-mcp上游说明](https://github.com/kisaragi-mochi/stackchan-mcp)：硬件目标、工具和设备配置。
- [Caddy反向代理](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)：反向代理与WebSocket支持。
- [uv安装文档](https://docs.astral.sh/uv/getting-started/installation/)：uv安装方式。
- [CC BY-NC 4.0说明](https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans)：本次核对过其仍要求标明修改，因此未直接采用该名称标注本自定义教程许可。

在线页面可能更新；个人版本和实测结果另按README记录。
