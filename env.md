# Gradio + Electron Windows 开发环境配置

本文档介绍如何在 Windows 上配置 Gradio + Electron 开发环境，用于打包成 exe 应用程序。

## 系统要求

-   Windows 10/11
-   管理员权限（用于安装某些工具）

## 1. 安装 Python 环境

### 1.1 安装 Python

```bash
# 下载并安装 Python 3.8+ (推荐 3.9-3.11)
# 从官网下载: https://www.python.org/downloads/
# 安装时确保勾选 "Add Python to PATH"
```

### 1.2 验证安装

```bash
python --version
pip --version
```

### 1.3 创建虚拟环境

```bash
python -m venv venv
venv\Scripts\activate
```

## 2. 安装 Node.js 环境

### 2.1 安装 Node.js

```bash
# 下载并安装 Node.js 16+ (推荐 LTS 版本)
# 从官网下载: https://nodejs.org/
```

### 2.2 验证安装

```bash
node --version
npm --version
```

## 3. 安装 Gradio

```bash
# 激活虚拟环境后安装
pip install gradio
```

## 4. 安装 Electron 相关工具

### 4.1 全局安装 Electron

```bash
npm install -g electron
```

### 4.2 安装 Electron Builder (用于打包)

```bash
npm install -g electron-builder
```

### 4.3 安装 Electron Packager (备选打包工具)

```bash
npm install -g electron-packager
```

## 5. 项目结构设置

创建项目目录结构：

```
your-project/
├── python-backend/          # Python Gradio 后端
│   ├── app.py              # 主要的 Gradio 应用
│   ├── requirements.txt    # Python 依赖
│   └── venv/              # 虚拟环境
├── electron-app/           # Electron 前端
│   ├── main.js            # Electron 主进程
│   ├── package.json       # Node.js 配置
│   ├── preload.js         # 预加载脚本
│   └── dist/              # 打包输出目录
└── build/                  # 最终构建文件
```

## 6. 配置 package.json

在 `electron-app` 目录下创建 `package.json`：

```json
{
	"name": "gradio-electron-app",
	"version": "1.0.0",
	"description": "Gradio Electron Application",
	"main": "main.js",
	"scripts": {
		"start": "electron .",
		"build": "electron-builder",
		"dist": "electron-builder --publish=never"
	},
	"devDependencies": {
		"electron": "^latest",
		"electron-builder": "^latest"
	},
	"build": {
		"appId": "com.yourcompany.gradio-app",
		"productName": "Gradio App",
		"directories": {
			"output": "dist"
		},
		"files": [
			"**/*",
			"!**/node_modules/*/{CHANGELOG.md,README.md,README,readme.md,readme}",
			"!**/node_modules/*/{test,__tests__,tests,powered-test,example,examples}",
			"!**/node_modules/*.d.ts",
			"!**/node_modules/.bin",
			"!**/*.{iml,o,hprof,orig,pyc,pyo,rbc,swp,csproj,sln,xproj}",
			"!.editorconfig",
			"!**/._*",
			"!**/{.DS_Store,.git,.hg,.svn,CVS,RCS,SCCS,.gitignore,.gitattributes}",
			"!**/{__pycache__,thumbs.db,.flowconfig,.idea,.vs,.nyc_output}",
			"!**/{appveyor.yml,.travis.yml,circle.yml}",
			"!**/{npm-debug.log,yarn.lock,.yarn-integrity,.yarn-metadata.json}"
		],
		"win": {
			"target": "nsis",
			"icon": "assets/icon.ico"
		},
		"nsis": {
			"oneClick": false,
			"allowToChangeInstallationDirectory": true
		}
	}
}
```

## 7. 开发工作流

### 7.1 开发阶段

```bash
# 1. 启动 Python 虚拟环境
venv\Scripts\activate

# 2. 运行 Gradio 应用 (在后台)
cd python-backend
python app.py

# 3. 启动 Electron 应用 (新终端)
cd electron-app
npm start
```

### 7.2 构建阶段

```bash
# 1. 确保 Gradio 应用可以独立运行
cd python-backend
python app.py

# 2. 构建 Electron 应用
cd electron-app
npm run build
```

## 8. 可选工具和依赖

### 8.1 Python 打包工具 (将 Python 代码打包成 exe)

```bash
pip install pyinstaller
# 或
pip install cx_Freeze
```

### 8.2 Gradio 相关扩展

```bash
pip install gradio[oauth]  # 如需要 OAuth 支持
```

### 8.3 调试工具

```bash
npm install -g electron-debug
```

## 9. 环境变量配置

在项目根目录创建 `.env` 文件：

```env
# Python 相关
PYTHONPATH=./python-backend
GRADIO_SERVER_PORT=7860
GRADIO_SERVER_NAME=127.0.0.1

# Electron 相关
ELECTRON_DISABLE_SECURITY_WARNINGS=true
```

## 10. 常见问题解决

### 10.1 Python 路径问题

确保在 Electron 中正确设置 Python 解释器路径：

```javascript
const pythonPath = path.join(__dirname, "../python-backend/venv/Scripts/python.exe");
```

### 10.2 端口冲突

在 `main.js` 中检查 Gradio 服务是否已启动：

```javascript
const checkServer = async (url) => {
	try {
		const response = await fetch(url);
		return response.ok;
	} catch {
		return false;
	}
};
```

### 10.3 打包大小优化

-   排除不必要的 Python 包
-   使用 `electron-builder` 的文件过滤功能
-   考虑使用 `asar` 打包

## 11. 部署检查清单

-   [ ] Python 环境已正确配置
-   [ ] Node.js 和 Electron 已安装
-   [ ] Gradio 应用可以独立运行
-   [ ] Electron 应用可以启动并连接到 Gradio
-   [ ] 打包配置已正确设置
-   [ ] 图标和资源文件已准备
-   [ ] 在目标 Windows 机器上测试过

## 12. 参考资源

-   [Gradio 官方文档](https://gradio.app/docs/)
-   [Electron 官方文档](https://www.electronjs.org/docs)
-   [Electron Builder 文档](https://www.electron.build/)
-   [Python 虚拟环境文档](https://docs.python.org/3/tutorial/venv.html)
    python -m PyInstaller --onefile --name resume_analyzer --distpath dist --workpath build --hidden-import=gradio --hidden-import=pdfplumber --hidden-import=fastapi --hidden-import=uvicorn --hidden-import=websockets --hidden-import=httpx --hidden-import=gradio_client --hidden-import=starlette --hidden-import=anyio --hidden-import=aiofiles --hidden-import=orjson --hidden-import=safehttpx --hidden-import=groovy --hidden-import=ffmpy --hidden-import=pydub --hidden-import=typer --hidden-import=rich --hidden-import=semantic_version --hidden-import=tomlkit --hidden-import=ruff --hidden-import=python_multipart --hidden-import=pypdfium2 --hidden-import=pdfminer--console app.py
