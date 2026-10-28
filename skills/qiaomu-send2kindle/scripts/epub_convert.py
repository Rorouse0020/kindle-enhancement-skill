"""Kindle 专有格式（AZW3 / AZW / MOBI / PRC）→ EPUB 转换（本地增强补丁）。

背景
----
上游技能只做「EPUB → AZW3」以便 Kindle 原生阅读器使用；KOReader 模式要求源文件
本身是 EPUB。而 KOReader **不支持 KF8/AZW3**（其格式注册表只有 azw/mobi/prc），
所以直接把 AZW3 传过去会打不开。

本模块补上反方向：在 KOReader 模式发送前，用外部的 KindleUnpack（GPL）把
Kindle 专有格式解开并重打包成 EPUB，再由上层 `kindle_convert.prepare()` 交给原有
的上传/回读校验流程。

设计要点
--------
* KindleUnpack 不随技能分发，单独安装在状态目录（GPL 与技能许可证隔离），
  可用环境变量 QIAOMU_KINDLEUNPACK_DIR 覆盖位置。
* KF8/AZW3：KindleUnpack 直接产出 epub（out/mobi8/*.epub）。
* MOBI7/AZW/MOBI：KindleUnpack 产出 book.html + Images + OPF（out/mobi7/），
  这里把它重新打包成合法 EPUB（mimetype 置首、container.xml 指向该 OPF）。
* 产物会做结构校验；任何失败都抛 KindleError，绝不留下"看似成功"的结果。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path

from kindle_store import KindleError
from runtime_paths import state_root

# 需要转换的 Kindle 专有格式扩展名
KINDLE_FORMATS = {'.azw3', '.azw', '.mobi', '.prc', '.kf8'}
# KOReader 原生支持、不需要转换的格式（直传即可）
PASSTHROUGH_FORMATS = {'.epub', '.pdf', '.txt', '.fb2', '.cbz', '.cbr', '.djvu',
                       '.djv', '.rtf', '.chm', '.doc', '.docx', '.html', '.htm'}

_CONTAINER_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<container version="1.0" '
    'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
    '  <rootfiles>\n'
    '    <rootfile full-path="{opf}" media-type="application/oebps-package+xml"/>\n'
    '  </rootfiles>\n'
    '</container>\n'
)


def unpack_root() -> Path:
    """定位 KindleUnpack 安装目录（含 lib/kindleunpack.py）。"""
    candidates = []
    env = os.environ.get('QIAOMU_KINDLEUNPACK_DIR')
    if env:
        candidates.append(Path(env).expanduser())
    try:
        candidates.append(state_root() / 'tools' / 'kindleunpack')
    except Exception:
        pass
    candidates.append(Path.home() / 'Library/Application Support/Qiaomu/Kindle/tools/kindleunpack')
    candidates.append(Path.home() / '.local/share/qiaomu/kindleunpack')
    for root in candidates:
        if (root / 'lib' / 'kindleunpack.py').is_file():
            return root
    raise KindleError(
        'converter-missing',
        'KindleUnpack is not installed; AZW3/MOBI to EPUB conversion is unavailable. '
        'Install it under "~/Library/Application Support/Qiaomu/Kindle/tools/kindleunpack" '
        'or set QIAOMU_KINDLEUNPACK_DIR. EPUB files transfer directly and need no converter.')


def validate_epub(path: Path) -> None:
    """确保是 KOReader 能打开的基本合法 EPUB。"""
    try:
        with zipfile.ZipFile(path) as book:
            names = book.namelist()
            if not names or names[0] != 'mimetype':
                raise KindleError('conversion', 'Converted EPUB has an invalid mimetype entry.')
            if book.read('mimetype').strip() != b'application/epub+zip':
                raise KindleError('conversion', 'Converted output is not an EPUB container.')
            if 'META-INF/container.xml' not in names:
                raise KindleError('conversion', 'Converted EPUB is missing container.xml.')
            if not any(n.lower().endswith(('.opf',)) for n in names):
                raise KindleError('conversion', 'Converted EPUB is missing its OPF package.')
            if not any(n.lower().endswith(('.xhtml', '.html', '.htm')) for n in names):
                raise KindleError('conversion', 'Converted EPUB has no readable content.')
            if book.testzip() is not None:
                raise KindleError('conversion', 'Converted EPUB archive is corrupt.')
    except zipfile.BadZipFile:
        raise KindleError('conversion', 'Converted output is not a readable EPUB archive.') from None


def _bundle_mobi7(workdir: Path, out_epub: Path) -> None:
    """把 KindleUnpack 的 mobi7 产物（book.html + Images + *.opf）重新打包成 EPUB。"""
    mobi7 = workdir / 'mobi7'
    if not mobi7.is_dir():
        raise KindleError('conversion', 'Converter produced no EPUB and no MOBI7 payload.')
    opfs = sorted(mobi7.glob('*.opf'))
    if not opfs:
        raise KindleError('conversion', 'Converter produced no OPF package for this MOBI file.')
    opf_rel = opfs[0].name
    files = sorted(p for p in mobi7.rglob('*') if p.is_file())
    if not files:
        raise KindleError('conversion', 'Converter produced an empty MOBI7 payload.')
    with zipfile.ZipFile(out_epub, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype 必须是第一个条目且不压缩
        zi = zipfile.ZipInfo('mimetype')
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, 'application/epub+zip')
        zf.writestr('META-INF/container.xml', _CONTAINER_XML.format(opf=opf_rel))
        for f in files:
            zf.write(f, f.relative_to(mobi7).as_posix())


@contextmanager
def convert_kindle_to_epub(book: dict, mode: str):
    """把 Kindle 专有格式转换为 EPUB 并暂存；yield 的 book 结构与 inspect_book 兼容。"""
    src = Path(book['path'])
    if mode == 'native':
        raise KindleError('conversion', 'Native mode does not need EPUB conversion.')
    if not src.is_file():
        raise KindleError('file', 'The source book is missing.')
    if book['bytes'] > 512 * 1024 * 1024:
        raise KindleError('conversion-size', 'Kindle format conversion accepts up to 512 MiB.')

    with tempfile.TemporaryDirectory(prefix='qiaomu-kindle-epub-') as tmp:
        workdir = Path(tmp) / 'unpacked'
        workdir.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(unpack_root() / 'lib' / 'kindleunpack.py'), str(src), str(workdir)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise KindleError('conversion-timeout',
                              'Kindle format conversion timed out; no book was uploaded.') from None
        except OSError:
            raise KindleError('converter-runtime',
                              'Could not start the Kindle format converter; no book was uploaded.') from None
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or '').strip().splitlines()[-1:] or ['unknown error']
            raise KindleError('conversion',
                              f'Kindle format conversion failed ({tail[0][:120]}); no book was uploaded.')

        produced = sorted(workdir.glob('mobi8/*.epub')) or sorted(workdir.glob('**/*.epub'))
        target = Path(tmp) / (Path(book['name']).stem + '.epub')
        if produced:
            shutil.copyfile(produced[0], target)
            engine = 'kindleunpack-mobi8'
        else:
            _bundle_mobi7(workdir, target)
            engine = 'kindleunpack-mobi7'

        if not target.is_file() or target.stat().st_size <= 0:
            raise KindleError('conversion', 'Converter produced no EPUB output.')
        validate_epub(target)

        # 源文件在转换期间不得变化
        import hashlib
        digest = hashlib.sha256()
        with src.open('rb') as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != book['sha256']:
            raise KindleError('changed', 'The source book changed during conversion; no book was uploaded.')

        converted_path = Path(tmp) / target.name
        yield {
            'path': str(converted_path),
            'name': target.name,
            'bytes': converted_path.stat().st_size,
            'sha256': hashlib.sha256(converted_path.read_bytes()).hexdigest(),
            'converted': True,
            'engine': engine,
        }
