from __future__ import annotations

import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.parse import urlencode

import pytest

SPEC = importlib.util.spec_from_file_location('release_setup', Path(__file__).resolve().parents[1] / 'setup_app.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


@pytest.fixture
def local_files(tmp_path, monkeypatch):
    token = tmp_path / 'sif-token'
    config = tmp_path / 'config.yaml'
    monkeypatch.setattr(setup, 'token_path', lambda: token)
    monkeypatch.setattr(setup.base, 'user_config_path', lambda: config)
    return token, config


def server():
    instance = object.__new__(setup.SetupServer)
    instance.session_token = 'test-session'
    instance.generated_token = None
    instance.login_results = {}
    instance.saved = False
    instance.shutdown = lambda: None
    return instance


def post(instance, path, form):
    request = object.__new__(setup.Handler)
    request.server = instance
    request.path = path
    raw = urlencode(form).encode()
    request.headers = {'Content-Length': str(len(raw))}
    request.rfile = BytesIO(raw)
    results = []
    request._send = lambda *args: results.append(args)
    request.do_POST()
    return results[0]


def test_default_form_is_token_first_with_closed_generation_panel(local_files):
    token, _ = local_files
    setup.save_token('existing-private-token')
    page = setup.render_form('session')
    assert 'existing-private-token' not in page
    assert page.index('name="sif_token"') < page.index('<details')
    assert '<details open' not in page
    assert 'type="button">生成并填入 Token' in page
    assert 'name="sif-password"' not in page
    assert setup.status()['sif_token'] is True
    assert 'existing-private-token' not in json.dumps(setup.status())


def test_save_existing_token_never_logs_in_or_stores_account(local_files, monkeypatch):
    token, config = local_files
    login = mock.Mock(side_effect=AssertionError('saving a token must never log in'))
    monkeypatch.setattr(setup, 'login', login)
    instance = server()
    result = post(instance, '/save', {
        'session_token': instance.session_token, 'sif_token': 'shared-token',
        'phone': 'test-phone', 'password': 'test-password', 'api_key_doubao': 'model-key',
    })
    assert token.read_text() == 'shared-token'
    assert instance.saved
    assert 'shared-token' not in result[0]
    assert 'test-phone' not in config.read_text()
    assert 'test-password' not in config.read_text()
    assert 'model-key' in config.read_text()
    login.assert_not_called()
    if os.name != 'nt':
        assert token.stat().st_mode & 0o777 == 0o600


def test_blank_preserves_token_and_invalid_token_preserves_old_config(local_files):
    token, config = local_files
    setup.save_token('original')
    post(server(), '/save', {'session_token': 'test-session', 'sif_token': ''})
    assert token.read_text() == 'original'
    before = config.read_text()
    result = post(server(), '/save', {'session_token': 'test-session', 'sif_token': 'bad\r\nvalue'})
    assert result[1] == 400
    assert token.read_text() == 'original'
    assert config.read_text() == before


def test_generate_is_explicit_autosaves_and_reuses_token(local_files, monkeypatch):
    token, config = local_files
    login = mock.Mock(return_value='new-generated-token')
    monkeypatch.setattr(setup, 'login', login)
    instance = server()
    form = {'session_token': instance.session_token, 'request_id': 'first', 'phone': 'phone', 'password': 'password'}
    first = post(instance, '/sif/generate', form)
    second = post(instance, '/sif/generate', {**form, 'request_id': 'second'})
    assert json.loads(first[0]) == json.loads(second[0]) == {'token': 'new-generated-token', 'saved': True}
    login.assert_called_once_with('phone', 'password')
    assert token.read_text() == 'new-generated-token'
    assert not config.exists()
    assert instance.saved


def test_duplicate_failed_request_does_not_retry_and_error_does_not_change_token(local_files, monkeypatch):
    token, _ = local_files
    setup.save_token('shared-old-token')
    login = mock.Mock(side_effect=ValueError('登录未成功'))
    monkeypatch.setattr(setup, 'login', login)
    instance = server()
    form = {'request_id': 'same', 'phone': 'phone', 'password': 'password'}
    assert instance.generate(form)[1] == 400
    assert instance.generate(form)[1] == 400
    login.assert_called_once()
    assert token.read_text() == 'shared-old-token'


def test_invalid_session_cannot_generate_or_save(local_files, monkeypatch):
    login = mock.Mock()
    monkeypatch.setattr(setup, 'login', login)
    for path in ['/save', '/sif/generate']:
        result = post(server(), path, {'session_token': 'wrong', 'sif_token': 'malicious', 'request_id': 'one'})
        assert result[1] == 403
    login.assert_not_called()
    assert not local_files[0].exists()


class Response(BytesIO):
    def __init__(self, payload, token=None):
        super().__init__(json.dumps(payload).encode())
        self.headers = {'authorization': token}


def test_login_uses_header_and_sends_credentials_only_to_sif(monkeypatch):
    seen = []
    def send(request, timeout):
        seen.append(request)
        return Response({'code': 1, 'data': {'isSuccess': True}}, 'header-token')
    monkeypatch.setattr(setup.urllib.request, 'urlopen', send)
    assert setup.login('phone', 'password') == 'header-token'
    assert len(seen) == 1
    assert seen[0].full_url == 'https://www.sif.com/api/user/login'
    assert json.loads(seen[0].data) == {'phone': 'phone', 'password': 'password'}


@pytest.mark.parametrize('payload,token', [
    ({'code': -5, 'message': 'private-password'}, 'sensitive-token'),
    ({'code': 1, 'data': {'isSuccess': False}}, 'sensitive-token'),
    ({'code': 1}, None), ([], 'sensitive-token'),
])
def test_login_rejects_errors_without_leaking_response(monkeypatch, payload, token):
    monkeypatch.setattr(setup.urllib.request, 'urlopen', lambda *a, **kw: Response(payload, token))
    with pytest.raises(ValueError) as error:
        setup.login('private-phone', 'private-password')
    assert 'private' not in str(error.value) and 'sensitive' not in str(error.value)


def test_login_timeout_has_no_automatic_retry(monkeypatch):
    request = mock.Mock(side_effect=TimeoutError('private-message'))
    monkeypatch.setattr(setup.urllib.request, 'urlopen', request)
    with pytest.raises(ValueError):
        setup.login('phone', 'password')
    request.assert_called_once()


def test_dispatch_only_overrides_web_and_status(monkeypatch):
    calls = []
    monkeypatch.setattr(setup.os, 'execv', lambda exe, args: (_ for _ in ()).throw(SystemExit((exe, args))))
    with pytest.raises(SystemExit) as result:
        setup.main(['--dispatch', '/bin/amz-real', 'setup', '--no-prompt'])
    assert result.value.code == ('/bin/amz-real', ['/bin/amz-real', 'setup', '--no-prompt'])
    monkeypatch.setattr(setup, 'run_web_setup', lambda **kw: calls.append(kw) or 0)
    assert setup.main(['--dispatch', '/bin/amz-real', 'setup', '--web', '--no-open']) == 0
    assert calls == [{'open_browser': False}]


def test_manager_wrapper_routes_setup_without_changing_other_commands(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('POSIX launcher execution')
    import subprocess
    import sys
    spec = importlib.util.spec_from_file_location('test_manager_wrapper', Path(__file__).resolve().parents[1] / 'manager.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    repository = tmp_path / 'release with spaces'
    repository.mkdir()
    (repository / 'setup_app.py').write_text('import sys\nprint("SETUP", *sys.argv[1:])\n')
    real = tmp_path / 'real amz'
    real.write_text('#!/bin/sh\nprintf "REAL %s\\n" "$*"\n')
    real.chmod(0o755)
    monkeypatch.setattr(manager, 'user_bin_dir', lambda: tmp_path / 'bin')
    monkeypatch.setattr(manager, '_tool_paths', lambda root: (root, Path(sys.executable), real))
    launcher, _ = manager._write_wrappers(tmp_path, repository)
    env = {**os.environ, 'AMZ_CLI_SKIP_UPDATE': '1'}
    version = subprocess.run([str(launcher), 'version', '--json'], capture_output=True, text=True, check=True, env=env)
    assert version.stdout.strip() == 'REAL version --json'
    status = subprocess.run([str(launcher), 'setup', '--status', '--json'], capture_output=True, text=True, check=True, env=env)
    assert status.stdout.strip() == f'SETUP --dispatch {real} setup --status --json'


def test_autosave_keeps_server_open_and_updates_only_submitted_fields(local_files):
    token, config = local_files
    setup.save_token('original-token')
    setup.base.save_form({'api_key_doubao': 'old-key', 'default_backend': 'doubao'})
    instance = server()
    instance.shutdown = mock.Mock()
    first = post(instance, '/save', {'session_token': 'test-session', 'api_key_doubao': 'new-key'})
    second = post(instance, '/save', {'session_token': 'test-session', 'default_backend': 'ark'})
    assert json.loads(first[0])['saved'] is True
    assert json.loads(second[0])['saved'] is True
    data = setup.base.load_saved_config()
    assert data['api_keys']['doubao'] == 'new-key'
    assert data['llm']['default_backend'] == 'ark'
    assert token.read_text() == 'original-token'
    instance.shutdown.assert_not_called()


def test_generation_save_failure_reuses_token_without_another_login(local_files, monkeypatch):
    login = mock.Mock(return_value='generated-token')
    monkeypatch.setattr(setup, 'login', login)
    write = setup.save_token
    monkeypatch.setattr(setup, 'save_token', mock.Mock(side_effect=PermissionError('private-path')))
    instance = server()
    form = {'request_id': 'first', 'phone': 'phone', 'password': 'password'}
    failure, code = instance.generate(form)
    assert code == 400 and 'private-path' not in failure['error']
    assert not instance.saved and not local_files[0].exists()
    monkeypatch.setattr(setup, 'save_token', write)
    result, code = instance.generate({**form, 'request_id': 'retry'})
    assert code == 200 and result['saved'] is True
    assert local_files[0].read_text() == 'generated-token'
    login.assert_called_once()


def test_autosave_failure_returns_json_without_secrets_and_keeps_server_open(local_files, monkeypatch):
    instance = server()
    instance.shutdown = mock.Mock()
    monkeypatch.setattr(setup.base, 'save_form', mock.Mock(side_effect=OSError('private-key')))
    response = post(instance, '/save', {'session_token': 'test-session', 'api_key_doubao': 'private-key'})
    assert response[1:] == (400, 'application/json')
    assert 'error' in json.loads(response[0]) and 'private-key' not in response[0]
    assert not instance.saved
    instance.shutdown.assert_not_called()


def test_cosmo_switch_autosaves_and_reopens_with_saved_choice(local_files):
    instance = server()
    instance.shutdown = mock.Mock()
    result = post(instance, '/save', {'session_token': 'test-session', 'cosmo_use_images': 'false'})
    assert json.loads(result[0])['status']['cosmo_use_images'] is False
    page = setup.render_form('test-session')
    assert 'name="cosmo_use_images"' in page
    assert '<option value="false" selected>' in page
    assert "select[name]" in page
    assert "field.addEventListener('change', () => saveField(field))" in page
    result = post(instance, '/save', {'session_token': 'test-session', 'cosmo_use_images': 'true'})
    assert json.loads(result[0])['status']['cosmo_use_images'] is True
    assert '<option value="true" selected>' in setup.render_form('next-session')
    instance.shutdown.assert_not_called()
