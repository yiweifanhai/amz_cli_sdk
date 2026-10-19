#!/usr/bin/env python3
"""Distribution-only SIF setup. Account login is always a user action."""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import secrets
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, quote, urlparse
import webbrowser

from amz import setup_web as base
from amz.config import config

LOGIN_URL = 'https://www.sif.com/api/user/login'


def check_token(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 16384 or '\r' in value or '\n' in value:
        raise ValueError('Token 为空或格式无效，请重新复制完整 Token。')
    return value


def token_path() -> Path:
    return config.sif_token_file


def save_token(value: str) -> None:
    value = check_token(value)
    target = token_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f'.{target.name}.{secrets.token_hex(8)}.tmp')
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def status() -> dict:
    result = base.saved_status()
    try:
        result['sif_token'] = token_path().is_file() and token_path().stat().st_size > 0
    except OSError:
        result['sif_token'] = False
    return result


def login(phone: str, password: str) -> str:
    """One explicit login request. Never load or persist account credentials."""
    if not phone.strip() or not password:
        raise ValueError('请填写 SIF 手机号和密码。')
    request = urllib.request.Request(
        LOGIN_URL, data=json.dumps({'phone': phone.strip(), 'password': password}).encode(),
        headers={'Content-Type': 'application/json', 'Origin': 'https://www.sif.com',
                 'Referer': 'https://www.sif.com/login'}, method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            token = response.headers.get('authorization')
            payload = json.load(response)
    except (OSError, ValueError):
        raise ValueError('SIF 登录未完成，请检查网络或稍后手动重试。不会自动重试。') from None
    if not isinstance(payload, dict):
        raise ValueError('SIF 返回了无法识别的登录结果。')
    data = payload.get('data')
    if payload.get('code') not in (None, 1) or (isinstance(data, dict) and data.get('isSuccess') is False):
        raise ValueError('SIF 未接受此次登录，请检查账号、密码或账号状态。')
    if not isinstance(token, str) or not token:
        raise ValueError('SIF 未返回 Token，请检查账号或在 SIF 网站完成所需验证。')
    return check_token(token)


def render_form(session: str, error: str = '') -> str:
    page = base.render_form(session, error=error)
    marker = '    <fieldset>\n      <legend>大模型服务</legend>'
    if marker not in page:
        raise RuntimeError('当前 CLI 配置页版本不兼容，请更新发行包。')
    badge = base._badge(status()['sif_token'])
    panel = f'''    <fieldset>
      <legend>SIF 广告数据</legend>
      <label><span>SIF Token {badge}</span>
        <input id="sif-token" type="password" name="sif_token" autocomplete="off"
               placeholder="粘贴管理员提供的 Token；留空保留已有值">
      </label>
      <p>默认使用老板或管理员统一提供的 Token。过期后联系管理员更新。</p>
      <button id="copy-sif" type="button">复制填写的 Token</button>
      <details style="margin:18px 0">
        <summary style="cursor:pointer">用账号生成 Token（老板 / 管理员）</summary>
        <p>由一人统一生成并分发。普通使用者无需填写账号；此处不会保存账号密码。</p>
        <label><span>SIF 手机号</span><input id="sif-phone" type="tel" autocomplete="off"></label>
        <label><span>SIF 密码</span><input id="sif-password" type="password" autocomplete="off"></label>
        <button id="generate-sif" type="button">生成并填入 Token</button>
        <p>生成后立即自动保存，可复制给同事。同一配置页面会复用已生成的 Token。</p>
      </details>
      <p id="sif-message" role="status" aria-live="polite"></p>
    </fieldset>
'''
    script = '<script nonce="' + html.escape(session, quote=True) + '">' + AUTOSAVE_SCRIPT + '</script>'
    page = page.replace('<button type="submit">安全保存配置</button>',
        '<p id="save-message" role="status" aria-live="polite">填写后自动保存，无需点击保存。</p>'
        '<button id="retry-save" type="button" hidden>重试未保存的配置</button>')
    page = page.replace('保存后会自动关闭服务。', '修改后自动保存；看到“已自动保存”后即可关闭页面。页面有效期 15 分钟。')
    return page.replace(marker, panel + marker, 1).replace('</body>', script + '</body>')


AUTOSAVE_SCRIPT = r'''
const tokenField = document.getElementById('sif-token');
const message = document.getElementById('sif-message');
const generateButton = document.getElementById('generate-sif');
const saveMessage = document.getElementById('save-message');
const retryButton = document.getElementById('retry-save');
const form = document.querySelector('form');
const fields = [...form.querySelectorAll('input[name]:not([type="hidden"]), select[name]')];
const sessionToken = form.elements.session_token.value;
const savedValues = new Map(fields.map(field => [field, field.value]));
const timers = new Map();
const errors = new Set();
const notes = new Map();
let queue = Promise.resolve();
let saving = 0;
let generating = false;
let requestId = null;
function showStatus() {
  const dirty = fields.some(field => field.value !== savedValues.get(field));
  saveMessage.textContent = saving ? '正在自动保存…' : errors.size ? '部分配置未保存，请检查对应输入后重试。' : dirty ? '有修改待保存…' : '已自动保存，可以关闭页面。';
  retryButton.hidden = errors.size === 0;
}
function markSaved(field, value) {
  savedValues.set(field, value);
  errors.delete(field);
  notes.get(field).textContent = value.trim() ? '已自动保存' : '留空，保留已有配置';
  const badge = field.closest('label').querySelector('.badge');
  if (badge && value.trim()) { badge.textContent = '已配置'; badge.className = 'badge ok'; }
}
function saveField(field) {
  clearTimeout(timers.get(field));
  const value = field.value;
  if (field === tokenField && generating) return queue;
  queue = queue.then(async () => {
    if (field.value !== value) return;
    if (value === savedValues.get(field)) {
      errors.delete(field); notes.get(field).textContent = ""; showStatus(); return;
    }
    if (!value.trim()) { markSaved(field, value); showStatus(); return; }
    if (!field.checkValidity()) {
      errors.add(field); notes.get(field).textContent = '输入格式无效，尚未保存'; showStatus(); return;
    }
    saving++; showStatus(); notes.get(field).textContent = '正在保存…';
    try {
      const response = await fetch('/save', {method: 'POST', body: new URLSearchParams({session_token: sessionToken, [field.name]: value})});
      const data = await response.json();
      if (!response.ok || !data.saved) throw new Error(data.error || '自动保存失败');
      markSaved(field, value);
      if (field.name === 'sellersprite_action' && value === 'clear') {
        const sellerField = form.elements.sellersprite_token;
        sellerField.value = ''; savedValues.set(sellerField, '');
        notes.get(sellerField).textContent = '已清除';
        const badge = sellerField.closest('label').querySelector('.badge');
        badge.textContent = '未配置'; badge.className = 'badge missing';
        field.value = 'keep'; savedValues.set(field, 'keep');
      }
    } catch (_) {
      errors.add(field); notes.get(field).textContent = '未保存，请检查输入和连接后重试；页面过期时需重新打开。';
    } finally { saving--; showStatus(); }
  });
  return queue;
}
for (const field of fields) {
  const note = document.createElement('small');
  note.setAttribute('aria-live', 'polite'); field.after(note); notes.set(field, note);
  field.addEventListener('input', () => {
    clearTimeout(timers.get(field));
    notes.get(field).textContent = '等待自动保存…'; showStatus();
    timers.set(field, setTimeout(() => saveField(field), 900));
  });
  field.addEventListener('change', () => saveField(field));
  field.addEventListener('blur', () => saveField(field));
}
retryButton.addEventListener('click', () => fields.forEach(saveField));
form.addEventListener('submit', event => { event.preventDefault(); fields.forEach(saveField); });
window.addEventListener('beforeunload', event => {
  if (saving || generating || fields.some(field => field.value !== savedValues.get(field))) {
    event.preventDefault(); event.returnValue = '';
  }
});
generateButton.addEventListener('click', async () => {
  generateButton.disabled = true;
  clearTimeout(timers.get(tokenField));
  await saveField(tokenField);
  generating = true; tokenField.disabled = true;
  message.textContent = '正在生成并自动保存，请勿重复操作…';
  if (!requestId) requestId = crypto.randomUUID();
  try {
    const body = new URLSearchParams({session_token: sessionToken, request_id: requestId,
      phone: document.getElementById('sif-phone').value, password: document.getElementById('sif-password').value});
    const response = await fetch('/sif/generate', {method: 'POST', body});
    const data = await response.json();
    if (!response.ok || !data.saved) {
      requestId = null;
      throw new Error(data.error || '生成或自动保存失败');
    }
    tokenField.value = data.token;
    markSaved(tokenField, data.token); showStatus();
    message.textContent = 'Token 已生成并自动保存，可复制给同事。';
    generateButton.textContent = '重新填入本次 Token';
  } catch (error) { message.textContent = error.message; }
  finally {
    document.getElementById('sif-password').value = '';
    generating = false; tokenField.disabled = false; generateButton.disabled = false;
  }
});
document.getElementById('copy-sif').addEventListener('click', async () => {
  if (!tokenField.value) { message.textContent = '请先填写或生成 Token。'; return; }
  try {
    await navigator.clipboard.writeText(tokenField.value);
    message.textContent = 'Token 已复制。请由管理员统一分发。';
  } catch (_) {
    message.textContent = '浏览器不允许复制，请在 Token 输入框中全选后手动复制。';
    tokenField.focus(); tokenField.select();
  }
});

'''


class SetupServer(base._SetupServer):
    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.session_token = secrets.token_urlsafe(24)
        self.generated_token: str | None = None
        self.login_results: dict[str, tuple[dict, int]] = {}
        self.saved = False

    def generate(self, form: dict) -> tuple[dict, int]:
        request_id = form.get('request_id', '')
        if not request_id or len(request_id) > 100:
            return {'error': '请求标识无效，请重新打开配置页。'}, 400
        if not self.generated_token:
            if request_id in self.login_results:
                return self.login_results[request_id]
            try:
                self.generated_token = login(form.get('phone', ''), form.get('password', ''))
            except ValueError as exc:
                result = ({'error': str(exc)}, 400)
                self.login_results[request_id] = result
                return result
        try:
            save_token(self.generated_token)
        except (OSError, ValueError):
            return {'error': 'Token 已生成，但自动保存失败。请检查文件权限后点击生成按钮重试；不会再次登录。'}, 400
        self.saved = True
        return {'token': self.generated_token, 'saved': True}, 200



class Handler(base._Handler):
    def _send(self, body: str, code: int = 200, content_type: str = 'text/html; charset=utf-8') -> None:
        payload = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy',
            f"default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-{self.server.session_token}'; "
            "connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        session = parse_qs(parsed.query).get('session', [''])[0]
        if parsed.path != '/' or not secrets.compare_digest(session, self.server.session_token):
            self._send('<h1>链接无效或已过期</h1>', 403)
            return
        self._send(render_form(self.server.session_token))

    def do_POST(self):
        if self.path not in ('/save', '/sif/generate'):
            self._send('<h1>页面不存在</h1>', 404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError()
            raw = self.rfile.read(length).decode()
        except (ValueError, UnicodeError):
            self._send('{}', 400, 'application/json')
            return
        form = {k: v[-1] for k, v in parse_qs(raw, keep_blank_values=True).items()}
        if not secrets.compare_digest(form.pop('session_token', ''), self.server.session_token):
            self._send('{"error":"链接无效或已过期"}', 403, 'application/json')
            return
        if self.path == '/sif/generate':
            result, code = self.server.generate(form)
            self._send(json.dumps(result, ensure_ascii=False), code, 'application/json')
            return
        try:
            token = form.pop('sif_token', '').strip()
            if token:
                check_token(token)
            base.save_form(form)
            if token:
                save_token(token)
        except (OSError, ValueError, base.yaml.YAMLError):
            self._send(json.dumps({'error': '自动保存失败，请检查输入和本机文件权限后重试。'}, ensure_ascii=False), 400, 'application/json')
            return
        self.server.saved = True
        self._send(json.dumps({'saved': True, 'status': status()}, ensure_ascii=False), 200, 'application/json')



def run_web_setup(open_browser: bool = True, timeout_seconds: int = 900) -> int:
    server = SetupServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{server.server_port}/?session={quote(server.session_token)}'
    print('amz 分发版配置页面已准备好。', flush=True)
    print(url, flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            pass
    timer = threading.Timer(timeout_seconds, server.shutdown)
    timer.daemon = True
    timer.start()
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        timer.cancel()
        server.generated_token = None
        server.login_results.clear()
        server.server_close()
    if server.saved:
        print(json.dumps(status(), ensure_ascii=False), flush=True)
        return 0
    print('配置页面已关闭或超时，请重新打开。', flush=True)
    return 1


def main(argv=None) -> int:
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ['--dispatch']:
        executable, args = args[1], args[2:]
        if args[:1] != ['setup'] or not any(flag in args for flag in ('--web', '--status')):
            os.execv(executable, [executable, *args])
        args = args[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--no-open', action='store_true')
    options = parser.parse_args(args)
    if options.status:
        result = status()
        if options.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print('AMZ 数据 Token：' + ('已配置' if result['data_api_token'] else '未配置'))
            print('SIF Token：' + ('已配置' if result['sif_token'] else '未配置'))
            print('COSMO 图片关键词抽取：' + ('开启' if result['cosmo_use_images'] else '关闭'))
            for name, configured in result['api_keys'].items():
                print(name + '：' + ('已配置' if configured else '未配置'))
        return 0
    if options.web:
        return run_web_setup(open_browser=not options.no_open)
    parser.error('请选择 --web 或 --status')


if __name__ == '__main__':
    raise SystemExit(main())
