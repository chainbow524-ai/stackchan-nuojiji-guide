'''Install/check/remove only the standalone optional vision tool for version 0.18.0.'''
import argparse
import ast
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
import shutil

DISPATCH = '''    # BEGIN QIANMO_EXTERNAL_VISION_DISPATCH
    if name == "take_photo_and_analyze":
        from ._qianmo_external_vision import handle
        return await handle(arguments, gateway, _dispatch_mcp_tool)
    # END QIANMO_EXTERNAL_VISION_DISPATCH

'''
SCHEMA = '''            # BEGIN QIANMO_EXTERNAL_VISION_SCHEMA
            Tool(
                name="take_photo_and_analyze",
                description="拍摄一张新照片并交给外部视觉模型识别，返回文字描述。一次工具调用完成；照片会发给已配置的识图服务商。不播放语音或显示字幕。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "minLength": 1, "maxLength": 2000},
                        "_actor": {},
                    },
                    "required": ["question"],
                },
            ),
            # END QIANMO_EXTERNAL_VISION_SCHEMA
'''


def tool_names(source):
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Tool':
            for keyword in node.keywords:
                if keyword.arg == 'name' and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    names.append(keyword.value.value)
    return names


def patch(source):
    if 'take_photo_and_analyze' in tool_names(source) or 'QIANMO_EXTERNAL_VISION_' in source:
        raise ValueError('已存在同名工具或本补丁，停止；不会覆盖原扩展。')
    tree = ast.parse(source)
    functions = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == '_dispatch_mcp_tool']
    if len(functions) != 1 or [a.arg for a in functions[0].args.args] != ['name', 'arguments', 'gateway']:
        raise ValueError('工具分发结构不同，停止。')
    first = functions[0].body[0]
    line = first.end_lineno if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str) else first.lineno - 1
    lines = source.splitlines(keepends=True)
    lines.insert(line, DISPATCH)
    result = ''.join(lines)
    anchor = '            Tool(\n                name="take_photo",'
    if result.count(anchor) != 1:
        raise ValueError('找不到唯一拍照注册项，停止。')
    result = result.replace(anchor, SCHEMA + anchor, 1)
    compile(result, 'stdio_server.py', 'exec')
    if tool_names(result).count('take_photo_and_analyze') != 1:
        raise ValueError('新工具注册检查未通过。')
    if remove(result) != source:
        raise ValueError('补丁撤销检查未通过。')
    return result


def remove(source):
    if source.count(DISPATCH) != 1 or source.count(SCHEMA) != 1:
        raise ValueError('本独立版标记不匹配，停止；不会覆盖其他版本或后续改动。')
    result = source.replace(DISPATCH, '', 1).replace(SCHEMA, '', 1)
    compile(result, 'stdio_server.py', 'exec')
    return result


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    import stackchan_mcp
    if importlib.metadata.version('stackchan-mcp') != '0.18.0':
        raise SystemExit('仅适用于核对过的0.18.0源码结构；未修改。')
    package = Path(stackchan_mcp.__file__).resolve().parent
    path = package / 'stdio_server.py'
    helper = package / '_qianmo_external_vision.py'
    worker = package / '_qianmo_vision_client.mjs'
    before = path.read_text()
    if args.check:
        assert before.count(DISPATCH) == 1 and before.count(SCHEMA) == 1, '未找到本独立版两个接入区块'
        compile(before, str(path), 'exec')
        compile(helper.read_text(), str(helper), 'exec')
        assert worker.is_file(), 'Node工作文件缺失'
        cfg_path = Path.home() / '.config/stackchan-vision/config.json'
        cfg = json.loads(cfg_path.read_text())
        assert all(cfg.get(k) for k in ('api_key', 'model', 'base_url', 'node')), '配置不完整'
        assert Path(cfg['node']).is_file(), 'Node路径不存在'
        names = tool_names(before)
        assert names.count('take_photo_and_analyze') == 1 and names.count('take_photo') == 1
        print('CHECK PASSED：独立版接入、工作文件和配置已核对；未调用API。工具数：', len(names))
        return
    after = remove(before) if args.uninstall else patch(before)
    bundle = Path(__file__).resolve().parent
    if not args.uninstall:
        for installed, supplied in ((helper, bundle / 'external-vision.py'), (worker, bundle / 'vision-client.mjs')):
            if installed.exists() and installed.read_bytes() != supplied.read_bytes():
                raise SystemExit('已有不同版本的工作文件，停止；未覆盖。')
        compile((bundle / 'external-vision.py').read_text(), str(helper), 'exec')
        if not (bundle / 'vision-client.mjs').is_file():
            raise SystemExit('安装材料缺少Node工作文件，停止。')
        cfg = json.loads((Path.home() / '.config/stackchan-vision/config.json').read_text())
        if not all(cfg.get(k) for k in ('api_key', 'model', 'base_url', 'node')) or not Path(cfg['node']).is_file():
            raise SystemExit('请先配置独立识图；未修改。')
    backup = Path.home() / 'stackchan-backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-standalone-vision')
    backup.mkdir(parents=True)
    shutil.copy2(path, backup / path.name)
    retained = {item: item.read_bytes() if item.exists() else None for item in (helper, worker)}
    try:
        if not args.uninstall:
            shutil.copy2(bundle / 'external-vision.py', helper)
            shutil.copy2(bundle / 'vision-client.mjs', worker)
        temporary = path.with_suffix('.py.vision-new')
        temporary.write_text(after)
        shutil.copymode(path, temporary)
        temporary.replace(path)
    except BaseException:
        path.write_text(before)
        if not args.uninstall:
            for item, contents in retained.items():
                if contents is None:
                    item.unlink(missing_ok=True)
                else:
                    item.write_bytes(contents)
        raise
    print('已撤下独立识图工具接入。' if args.uninstall else '已安装独立识图工具接入。')
    print('备份：', backup)
    print('未重启服务；原拍照、字幕、表情、自动眨眼及配置未被删除。')
    if args.uninstall:
        print('独立配置和工作文件保留供恢复，不自动删除密钥或其他目录。')


if __name__ == '__main__':
    main()
