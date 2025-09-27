# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import safehttpx, groovy, gradio, gradio_client
import os
import glob

# 更全面地收集 gradio 和相关包的所有文件
datas = []

# 收集 gradio 的所有数据文件（包括 .py, .js, .css, .html 等）
datas += collect_data_files("gradio", include_py_files=True)
datas += collect_data_files("gradio_client", include_py_files=True)

# 手动添加 gradio 的关键目录
gradio_path = os.path.dirname(gradio.__file__)
critical_dirs = [
    "layouts",
    "components", 
    "templates",
    "themes",
    "processing_utils",
    "routes",
    "utils",
    "helpers",
    "flagging",
    "external",
    "examples"
]

for dir_name in critical_dirs:
    dir_path = os.path.join(gradio_path, dir_name)
    if os.path.exists(dir_path):
        # 收集该目录下的所有 .py 文件
        for py_file in glob.glob(os.path.join(dir_path, "*.py")):
            rel_path = os.path.relpath(py_file, gradio_path)
            datas.append((py_file, os.path.join("gradio", os.path.dirname(rel_path))))
        
        # 收集子目录
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith(('.py', '.js', '.css', '.html', '.json', '.txt')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, gradio_path)
                    datas.append((full_path, os.path.join("gradio", os.path.dirname(rel_path))))

# 收集 gradio_client 的关键文件
gradio_client_path = os.path.dirname(gradio_client.__file__)
for root, dirs, files in os.walk(gradio_client_path):
    for file in files:
        if file.endswith(('.py', '.js', '.css', '.html', '.json', '.txt')):
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, gradio_client_path)
            datas.append((full_path, os.path.join("gradio_client", os.path.dirname(rel_path))))

# 其他必要的数据文件
datas += [
    (os.path.join(os.path.dirname(safehttpx.__file__), "version.txt"), "safehttpx")
]
datas += [
    (os.path.join(os.path.dirname(groovy.__file__), "version.txt"), "groovy")
]

# 收集所有子模块
hiddenimports = collect_submodules('gradio')
hiddenimports += collect_submodules('gradio_client')

# 添加其他必要的隐藏导入
additional_imports = [
    "httpx",
    "websockets", 
    "websockets.legacy",
    "websockets.legacy.server",
    "starlette",
    "starlette.applications",
    "starlette.routing",
    "starlette.responses", 
    "starlette.staticfiles",
    "anyio",
    "aiofiles",
    "orjson",
    "pydub",
    "typer",
    "rich",
    "semantic_version",
    "tomlkit",
    "python_multipart",
    "jinja2",
    "markupsafe",
    "uvicorn",
    "uvicorn.server",
    "uvicorn.protocols",
    "fastapi",
    "pydantic",
    # Gradio 特定模块
    "gradio.layouts.accordion",
    "gradio.layouts.column", 
    "gradio.layouts.row",
    "gradio.layouts.tab",
    "gradio.layouts.group",
    "gradio.components",
    "gradio.processing_utils",
    "gradio.utils",
    "gradio.routes",
    "gradio.themes",
    "gradio.helpers",
    "gradio.flagging",
    "gradio.external",
    # 常见缺失的模块
    "altair",
    "matplotlib",
    "PIL",
    "numpy",
    "pandas"
]

hiddenimports.extend(additional_imports)

# 去重
hiddenimports = list(set(hiddenimports))

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gradio_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 调试时保持为 True
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='gradio_app'
)