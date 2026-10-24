'''Create private, standalone vision settings. Does not change gateway settings.'''
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime
import getpass
import json
import shutil


def main():
    path = Path.home() / '.config/stackchan-vision/config.json'
    previous = {}
    if path.exists():
        previous = json.loads(path.read_text())
    node = shutil.which('node')
    if not node:
        raise SystemExit('找不到Node.js。按教程安装Node22或24后再配置。')
    print('只填写外部识图配置；不要填写StackChan的/capture上传地址。')
    base = input('Base URL（服务商提供的HTTPS地址，一般以/v1结尾）：').strip() or previous.get('base_url', '')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SystemExit('Base URL格式不符，未保存。')
    if parsed.path.rstrip('/').endswith(('/chat/completions', '/capture')):
        raise SystemExit('请填API Base URL，不要包含/chat/completions或/capture。未保存。')
    model = input('可识图模型的完整名称：').strip() or previous.get('model', '')
    prompt = 'API Key（隐藏输入；已有配置时留空保留）：' if previous.get('api_key') else 'API Key（隐藏输入）：'
    key = getpass.getpass(prompt).strip() or previous.get('api_key', '')
    if not model or not key:
        raise SystemExit('模型名或API Key为空，未保存。')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    if path.exists():
        backup = path.with_name('config.before-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
        shutil.copy2(path, backup)
        backup.chmod(0o600)
    content = json.dumps({'base_url': base.rstrip('/'), 'model': model, 'api_key': key, 'node': node}, ensure_ascii=False, indent=2) + '\n'
    temporary = path.with_suffix('.json.new')
    with temporary.open('w', opener=lambda name, flags: __import__('os').open(name, flags, 0o600)) as f:
        f.write(content)
    temporary.chmod(0o600)
    temporary.replace(path)
    print('配置已私下保存：', path)
    print('不会输出密钥；本步骤未调用模型、未安装工具、未重启服务。')


if __name__ == '__main__':
    main()
