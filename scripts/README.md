# 可选独立外部识图脚本

按[外部识图教程](../docs/07-external-vision.md)逐步使用，不直接安装到已存在同名工具的网关。

| 文件 | 用途 |
| --- | --- |
| configure-external-vision.py | 私下配置模型Base URL、模型名、API Key和Node路径 |
| vision-client.mjs | 测试已有照片，或作为组合工具的Node识图工作进程 |
| external-vision.py | 只使用本次拍照回执、调用独立识图并返回文字 |
| install-external-vision.py | 对0.18.0做带备份的安装、检查或卸载 |

配置文件在用户主目录的.config/stackchan-vision下，不在仓库中。脚本不会自动重启服务或刷机，不会自动重试付费请求。

本独立版为本次教程修订新整理的辅助实现，本地验证覆盖请求格式、11项Python侧场景和安装/检查/卸载/重装；子进程及路径部分使用替身，尚未在真实VPS端到端复测。历史个人方案的成功不等于本版本已完成同样实测。

浅默有权授权的新增辅助脚本按根目录LICENSE和LICENSE-DOCS.md中的使用规则分享，第三方软件和代码保留原许可。
