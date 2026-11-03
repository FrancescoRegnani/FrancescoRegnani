"""Wrap web/index.html in a full HTML document for static hosting (GitHub Pages).

The claude.ai artifact adds this skeleton itself; a normal web host does not.
Usage: python scripts/build_site.py OUT_DIR
"""
import shutil
import sys
from pathlib import Path

web = Path(__file__).resolve().parent.parent / 'web'
out = Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
out.mkdir(parents=True, exist_ok=True)
body = (web / 'index.html').read_text(encoding='utf-8')
head = ('<!doctype html><html lang="it"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
        '<style>@media (prefers-color-scheme: dark){:root{color-scheme:dark}}</style></head><body>')
(out / 'index.html').write_text(head + body + '</body></html>', encoding='utf-8')
if (web / 'data.json').exists():
    shutil.copy(web / 'data.json', out / 'data.json')
(out / '.nojekyll').write_text('')
print('built', out)
