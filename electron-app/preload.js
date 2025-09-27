const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 在这里可以暴露需要的 API 给渲染进程
});