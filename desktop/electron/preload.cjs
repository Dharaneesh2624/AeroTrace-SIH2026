const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('aero', {
  api: (method, path, body) => ipcRenderer.invoke('aero:api', method, path, body),
  importCSV: () => ipcRenderer.invoke('aero:import'),
  exportReport: id => ipcRenderer.invoke('aero:export', id),
  info: () => ipcRenderer.invoke('aero:info')
});
