const { app, BrowserWindow, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

let mainWindow;
let pythonProcess;

function findGradioExecutable() {
	const possiblePaths = [
		path.join(process.resourcesPath, "python-backend", "HireView_1.0.exe"),
		path.join(process.resourcesPath, "HireView_1.0.exe"),
		// 开发环境路径
		path.join(__dirname, "..", "python-backend", "HireView_1.0.exe"),
		path.join(__dirname, "..", "HireView_1.0.exe"),
		path.join(__dirname, "HireView_1.0.exe"),
		// 相对于主目录的路径
		path.join(process.cwd(), "HireView_1.0.exe"),
		path.join(process.cwd(), "python-backend", "HireView_1.0.exe"),
	];

	// 查找存在的可执行文件
	for (const exePath of possiblePaths) {
		if (fs.existsSync(exePath)) {
			console.log("Found Gradio executable at:", exePath);
			return exePath;
		}
	}

	return null;
}

function startPythonBackend() {
	return new Promise((resolve, reject) => {
		const gradioExe = findGradioExecutable();

		if (!gradioExe) {
			const error = new Error("HireView executable not found");
			console.error("Error:", error.message);
			reject(error);
			return;
		}

		console.log("Starting HireView backend:", gradioExe);

		// 启动 gradio 可执行文件
		pythonProcess = spawn(gradioExe, [], {
			stdio: ["pipe", "pipe", "pipe"],
		});

		// 处理标准输出
		pythonProcess.stdout.on("data", (data) => {
			const output = data.toString();
			console.log("Gradio output:", output);

			// 检查 HireView 是否已启动
			if (output.includes("Running on local URL:") || output.includes("http://127.0.0.1:7863") || output.includes("localhost:7863")) {
				console.log("HireView backend ready!");
				resolve();
			}
		});

		// 处理标准错误
		pythonProcess.stderr.on("data", (data) => {
			const errorOutput = data.toString();
			console.error("Gradio error:", errorOutput);

			// 有些正常的输出也可能出现在 stderr 中
			if (errorOutput.includes("Running on local URL:") || errorOutput.includes("http://127.0.0.1:7863") || errorOutput.includes("localhost:7863")) {
				console.log("HireView backend ready (from stderr)!");
				resolve();
			}
		});

		// 处理进程关闭
		pythonProcess.on("close", (code) => {
			console.log(`HireView process exited with code: ${code}`);
			if (code !== 0 && code !== null) {
				reject(new Error(`HireView process exited with code: ${code}`));
			}
		});

		// 处理进程错误
		pythonProcess.on("error", (error) => {
			console.error("Failed to start HireView backend:", error);
			reject(error);
		});

		// 设置启动超时（30秒）
		const timeout = setTimeout(() => {
			reject(new Error("HireView backend startup timeout (30s)"));
		}, 30000);

		// 清理超时定时器
		const originalResolve = resolve;
		resolve = () => {
			clearTimeout(timeout);
			originalResolve();
		};
	});
}

async function createWindow() {
	try {
		console.log("Starting HireView backend...");
		await startPythonBackend();
		console.log("HireView backend started successfully");

		// 等待服务器完全准备就绪
		await new Promise((resolve) => setTimeout(resolve, 2000));
	} catch (error) {
		console.error("Failed to start HireView backend:", error);

		// 显示错误对话框
		dialog.showErrorBox("Backend Error", `Failed to start HireView backend: ${error.message}\n\nPlease ensure HireView_1.0.exe is in the correct location.`);

		// 可以选择退出应用或继续（显示错误页面）
		// app.quit();
		// return;
	}

	// 创建主窗口
	mainWindow = new BrowserWindow({
		width: 1200,
		height: 800,
		webPreferences: {
			nodeIntegration: false,
			contextIsolation: true,
			preload: path.join(__dirname, "preload.js"),
		},
		show: false, // 先不显示，等加载完成后再显示
	});

	// 窗口准备好后显示
	mainWindow.once("ready-to-show", () => {
		mainWindow.show();
	});

	// 加载 HireView 应用程序
	try {
		await mainWindow.loadURL("http://127.0.0.1:7863");
		console.log("HireView UI loaded successfully");
	} catch (error) {
		console.error("Failed to load HireView UI:", error);

		// 加载本地错误页面或显示错误信息
		mainWindow.loadFile(path.join(__dirname, "error.html")).catch(() => {
			mainWindow.loadURL("data:text/html,<h1>Error</h1><p>Failed to load HireView application</p>");
		});
	}

	// 处理窗口关闭
	mainWindow.on("closed", () => {
		mainWindow = null;
	});

	// 处理导航错误
	mainWindow.webContents.on("did-fail-load", (event, errorCode, errorDescription, validatedURL) => {
		console.error("Failed to load URL:", validatedURL, errorDescription);
	});
}

// 应用程序准备就绪
app.whenReady().then(() => {
	createWindow();
});

// 所有窗口关闭时
app.on("window-all-closed", () => {
	// 关闭 Python 后端进程
	if (pythonProcess && !pythonProcess.killed) {
		console.log("Terminating HireView process...");
		pythonProcess.kill("SIGTERM");

		// 如果进程在5秒内没有关闭，强制终止
		setTimeout(() => {
			if (pythonProcess && !pythonProcess.killed) {
				console.log("Force killing HireView process...");
				pythonProcess.kill("SIGKILL");
			}
		}, 5000);

		pythonProcess = null;
	}

	if (process.platform !== "darwin") {
		app.quit();
	}
});

// 应用程序激活时
app.on("activate", () => {
	if (BrowserWindow.getAllWindows().length === 0) {
		createWindow();
	}
});

// 应用程序退出前
app.on("before-quit", () => {
	if (pythonProcess && !pythonProcess.killed) {
		console.log("Cleaning up HireView process before app exit...");
		pythonProcess.kill("SIGTERM");
		pythonProcess = null;
	}
});

// 处理未捕获的异常
process.on("uncaughtException", (error) => {
	console.error("Uncaught Exception:", error);
});

process.on("unhandledRejection", (reason, promise) => {
	console.error("Unhandled Rejection at:", promise, "reason:", reason);
});
