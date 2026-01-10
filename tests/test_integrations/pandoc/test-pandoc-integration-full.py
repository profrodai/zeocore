# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/test-pandoc-integration-full.py
# role: tests
# neighbors: __init__.py, conftest.py, mocks.py, test_config.py, test_converter.py, test_models.py (+4 more)
# exports: fs_stub, test_verify_pandoc_success, test_verify_pandoc_import_error, test_prepare_pandoc_args_defaults, test_util_get_file_info_success, test_util_get_file_info_not_found, test_post_process_markdown, test_validate_html_structure_valid (+13 more)
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

import os
import sys
import time
import types
from types import SimpleNamespace

import pytest
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.config import (
    PandocConfig,
    PandocConfigProvider,
)
from quack_core.integrations.pandoc.converter import DocumentConverter
from quack_core.integrations.pandoc.models import (
    ConversionTask,
    FileInfo,
)
from quack_core.integrations.pandoc.operations.html_to_md import (
    post_process_markdown,
    validate_html_structure,
)
from quack_core.integrations.pandoc.operations.utils import (
    get_file_info as util_get_file_info,
)
from quack_core.integrations.pandoc.operations.utils import (
    prepare_pandoc_args,
    verify_pandoc,
)
from quack_core.integrations.pandoc.service import PandocIntegration
from quack_core.core.errors import QuackIntegrationError


# Fixtures for monkeypatching filesystem service
@pytest.fixture(autouse=True)
def fs_stub(monkeypatch):
    """
    Stub out the quack_core.core.fs.service.standalone methods for file operations.
    """
    import quack_core.core.fs.service as fs_service
    stub = SimpleNamespace()
    # Default get_file_info returns success, exists, size, modified
    stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100, modified=time.time()
    )
    stub.create_directory = lambda path, exist_ok: SimpleNamespace(success=True)
    # match os.path.join signature: first arg required, then *paths
    stub.join_path = lambda a, *parts: os.path.join(a, *parts)
    stub.split_path = lambda path: path.split(os.sep)
    stub.write_text = lambda path, content, encoding=None: SimpleNamespace(
        success=True, bytes_written=len(content)
    )
    stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=True, content="dummy content"
    )
    stub.get_extension = lambda path: SimpleNamespace(data=path.split('.')[-1])
    stub.get_path_info = lambda path: SimpleNamespace(success=True)
    stub.is_valid_path = lambda path: True
    stub.normalize_path = lambda p: SimpleNamespace(success=True, path=os.path.abspath(p))
    stub.normalize_path_with_info = stub.normalize_path
    stub.get_file_size_str = lambda size: f"{size}B"
    monkeypatch.setattr(fs_service, 'standalone', stub)
    yield stub


# Tests for verify_pandoc
def test_verify_pandoc_success(monkeypatch):
    # Create a dummy pypandoc module
    dummy = types.ModuleType('pypandoc')
    dummy.get_pandoc_version = lambda: '2.11'
    monkeypatch.setitem(sys.modules, 'pypandoc', dummy)

    ver = verify_pandoc()
    assert ver == '2.11'


def test_verify_pandoc_import_error(monkeypatch):
    # Ensure pypandoc not in modules to trigger ImportError
    monkeypatch.delitem(sys.modules, 'pypandoc', raising=False)
    with pytest.raises(QuackIntegrationError) as excinfo:
        verify_pandoc()
    assert 'pypandoc module is not installed' in str(excinfo.value)


# Tests for prepare_pandoc_args
def test_prepare_pandoc_args_defaults():
    config = PandocConfig()
    args = prepare_pandoc_args(config, 'html', 'markdown', None)
    # Check core flags present
    assert '--wrap=none' in args
    assert '--standalone' in args
    assert '--markdown-headings=atx' in args
    # HTML to markdown extra args default
    assert '--strip-comments' in args
    assert '--no-highlight' in args


# Tests for util_get_file_info
def test_util_get_file_info_success():
    info = util_get_file_info('test.html', format_hint=None)
    assert isinstance(info, FileInfo)
    assert info.format == 'html'
    assert info.size == 100


def test_util_get_file_info_not_found(monkeypatch):
    quack_core.core.fs.service.standalone.get_file_info = lambda p: SimpleNamespace(success=False, exists=False)
    with pytest.raises(QuackIntegrationError):
        util_get_file_info('missing.md')


# Tests for post_process_markdown
@pytest.mark.parametrize('raw,expected_sub', [
    ('Text {remove} here', 'Text  here'),
    ('Hello <!-- comment -->World', 'Hello World'),
    ('<div>x</div>', 'x'),
])
def test_post_process_markdown(raw, expected_sub):
    cleaned = post_process_markdown(raw)
    assert expected_sub in cleaned


# Tests for validate_html_structure
def test_validate_html_structure_valid():
    html = '<html><body><h1>Title</h1><p>Text</p></body></html>'
    valid, errors = validate_html_structure(html, check_links=False)
    assert valid and not errors


def test_validate_html_structure_missing_body():
    html = '<html><head></head></html>'
    valid, errors = validate_html_structure(html, check_links=False)
    assert not valid
    assert 'missing body' in errors[0].lower()


def test_validate_html_structure_empty_links():
    html = '<html><body><a href=""></a></body></html>'
    valid, errors = validate_html_structure(html, check_links=True)
    assert not valid
    assert 'empty links' in errors[0]


# Tests for DocumentConverter.convert_file
@pytest.fixture
def converter(monkeypatch):
    # Inject our dummy pypandoc module for converter init
    dummy = types.ModuleType('pypandoc')
    dummy.get_pandoc_version = lambda: '2.11'
    monkeypatch.setitem(sys.modules, 'pypandoc', dummy)

    config = PandocConfig()
    return DocumentConverter(config)


def test_convert_file_html_to_md_success(converter, monkeypatch):
    # Stub file_info
    monkeypatch.setattr(
        'quack_core.integrations.pandoc.operations.utils.get_file_info',
        lambda path: FileInfo(
            path=path, format='html', size=100, modified=None, extra_args=[]
        )
    )
    # Stub conversion operation
    monkeypatch.setattr(
        'quack_core.integrations.pandoc.operations.html_to_md.convert_html_to_markdown',
        lambda i, o, cfg, m: IntegrationResult.success_result(['out.md'])
    )

    result = converter.convert_file('in.html', 'out.md', 'markdown')
    assert result.success
    assert result.content == 'out.md'


def test_convert_file_unsupported(converter):
    # Stub file_info to unsupported format
    def fake_get(path, _format_hint=None):
        return FileInfo(
            path=path, format='txt', size=0, modified=None, extra_args=[]
        )
    import quack_core.integrations.pandoc.operations.utils as utils_mod
    utils_mod.get_file_info = fake_get

    result = converter.convert_file('file.txt', 'out.md', 'markdown')
    assert not result.success
    assert 'Unsupported conversion' in result.error


# Tests for DocumentConverter.convert_batch
def test_convert_batch_all_success(converter):
    # Stub convert_file to always succeed
    converter.convert_file = lambda inp, out, fmt: IntegrationResult.success_result(out)

    tasks = [
        ConversionTask(
            source=FileInfo(
                path='a.html',
                format='html',
                size=0,
                modified=None,
                extra_args=[]
            ),
            target_format='markdown',
            output_path='a.md'
        ),
        ConversionTask(
            source=FileInfo(
                path='b.html',
                format='html',
                size=0,
                modified=None,
                extra_args=[]
            ),
            target_format='markdown',
            output_path='b.md'
        ),
    ]
    result = converter.convert_batch(tasks)
    assert result.success
    assert set(result.content) == {'a.md', 'b.md'}


def test_convert_batch_partial_failure(converter):
    # First succeeds, second fails
    def fake_convert(inp, out, _fmt=None):
        if inp.endswith('fail.html'):
            return IntegrationResult.error_result('err')
        return IntegrationResult.success_result(out)
    converter.convert_file = fake_convert

    tasks = [
        ConversionTask(
            source=FileInfo(
                path='ok.html',
                format='html',
                size=0,
                modified=None,
                extra_args=[]
            ),
            target_format='markdown',
            output_path='ok.md'
        ),
        ConversionTask(
            source=FileInfo(
                path='fail.html',
                format='html',
                size=0,
                modified=None,
                extra_args=[]
            ),
            target_format='markdown',
            output_path='fail.md'
        ),
    ]
    result = converter.convert_batch(tasks)
    assert result.success
    assert 'Partially successful' in result.message
    assert result.content == ['ok.md']


# Tests for PandocIntegration availability
def test_pandoc_integration_is_available(monkeypatch):
    import quack_core.integrations.pandoc.service as service_mod
    # inject dummy module
    monkeypatch.setattr(
        service_mod,
        'verify_pandoc',
        lambda: '2.11'
    )

    integration = PandocIntegration()
    assert integration.is_pandoc_available()
    assert integration.get_pandoc_version() == '2.11'


def test_pandoc_integration_not_available(monkeypatch):
    import quack_core.integrations.pandoc.service as service_mod
    from quack_core.core.errors import QuackIntegrationError
    monkeypatch.setattr(
        service_mod,
        'verify_pandoc',
        lambda: (_ for _ in ()).throw(QuackIntegrationError('fail', {}))
    )

    integration = PandocIntegration()
    assert not integration.is_pandoc_available()
    assert integration.get_pandoc_version() is None


# Tests for Config
def test_pandoc_config_default():
    config = PandocConfig()
    assert config.output_dir == './output'
    assert isinstance(config.pandoc_options.wrap, str)


def test_pandoc_config_validate_output_dir(monkeypatch):
    # Invalidate path
    quack_core.core.fs.service.standalone.get_path_info = lambda p: SimpleNamespace(success=False)
    with pytest.raises(ValueError):
        PandocConfig(output_dir='??invalid')


# Tests for ConfigProvider
def test_config_provider_validate_config(monkeypatch):
    provider = PandocConfigProvider()
    # valid schema
    assert provider.validate_config({'output_dir': '/tmp'}) is not False
    # test invalid path
    quack_core.core.fs.service.standalone.is_valid_path = lambda p: False
    assert not provider.validate_config({'output_dir': '/tmp'})


def test_config_provider_get_default_and_env(monkeypatch, tmp_path):
    provider = PandocConfigProvider()
    # normalize default
    cfg_default = provider.get_default_config()
    assert 'output_dir' in cfg_default

    # load from environment
    monkeypatch.setenv('QUACK_PANDOC_OUTPUT_DIR', str(tmp_path))
    cfg_env = provider.load_from_environment()
    assert cfg_env.get('output_dir') == os.path.abspath(str(tmp_path))
