const {app, BrowserWindow, protocol, net, ipcMain, dialog, session} = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const {pathToFileURL} = require('node:url');
const {spawn} = require('node:child_process');
const {randomBytes} = require('node:crypto');
const {allowedRequest, trustedURL} = require('./policy.cjs');
protocol.registerSchemesAsPrivileged([{scheme:'aerotrace', privileges:{standard:true, secure:true, supportFetchAPI:true, stream:true}}]);
const smokeAt = process.argv.indexOf('--smoke-test');
const smokeDir = smokeAt >= 0 ? path.resolve(process.argv[smokeAt+1]) : null;
if (smokeDir) app.setPath('userData', path.join(smokeDir, 'app-data'));
const ownsLock = app.requestSingleInstanceLock();
if (!ownsLock) app.quit();
let window, child, endpoint, startup, shuttingDown = false;
const token = randomBytes(32).toString('hex');
function authorize(event) { if (!event.senderFrame || event.sender !== window?.webContents || !trustedURL(event.senderFrame.url)) throw new Error('Untrusted request'); }
function privateRequest(method, route, body) {
  return fetch(endpoint+route, {method, headers:{'X-API-Key':token, 'Content-Type':'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body), signal:AbortSignal.timeout(120000)})
    .then(async r => {const payload = await r.json(); if (!r.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail)); return payload;});
}
function startBackend() {
  return new Promise((resolve, reject) => {
    const root = path.resolve(__dirname, '../..');
    const resources = app.isPackaged ? process.resourcesPath : path.join(root, 'desktop/backend-bundle/aerotrace-server');
    const exe = app.isPackaged ? path.join(resources,'backend/aerotrace-server.exe') : path.join(resources,'aerotrace-server.exe');
    if (!fs.existsSync(exe)) return reject(new Error('Bundled backend is missing. Run the backend packaging step.'));
    const dataDir = path.join(app.getPath('userData'), 'data');
    fs.mkdirSync(dataDir, {recursive:true});
    const log = fs.createWriteStream(path.join(app.getPath('userData'), 'backend.log'), {flags:'a'});
    child = spawn(exe, ['--data-dir',dataDir], {windowsHide:true, stdio:['pipe','pipe','pipe'],
      env:{...process.env,AEROTRACE_DESKTOP_TOKEN:token,PYTHONUNBUFFERED:'1'}});
    let buffer='', settled=false;
    const timer = setTimeout(() => {if (!settled) {settled=true; reject(new Error('Backend startup timed out. See backend.log.')); child.stdin.end();}},90000);
    child.stderr.on('data', data => log.write(data));
    child.stdout.on('data', async data => {
      buffer += data.toString();
      const lines=buffer.split('\n'); buffer=lines.pop();
      for (const line of lines) {
        if (line.startsWith('AEROTRACE_READY:') && !settled) {
          try {
            const {port}=JSON.parse(line.slice(16));
            if (!Number.isInteger(port)||port<1||port>65535) throw new Error('Invalid backend port');
            endpoint=`http://127.0.0.1:${port}`;
            for (let i=0;i<50;i++) {
              try { await privateRequest('GET','/health'); settled=true; clearTimeout(timer); resolve(); return; }
              catch {await new Promise(r=>setTimeout(r,100));}
            }
            throw new Error('Backend did not become healthy');
          } catch (e) {settled=true;clearTimeout(timer);reject(e);}
        } else log.write(line+'\n');
      }
    });
    child.on('error', e => {clearTimeout(timer);reject(e);});
    child.on('exit', code => {clearTimeout(timer);log.end(); if (!settled) reject(new Error(`Backend stopped (${code}). See backend.log.`));
      else if (!shuttingDown && window) window.webContents.send('backend-stopped');});
  });
}
async function stopBackend() {
  if (!child || child.exitCode !== null) return;
  await new Promise(resolve => {
    const timer=setTimeout(()=>{child.kill();resolve();},4000);
    child.once('exit',()=>{clearTimeout(timer);resolve();});
    child.stdin.end();
  });
}
if (ownsLock) app.whenReady().then(async () => {
  const dist = path.resolve(__dirname,'../dist');
  protocol.handle('aerotrace', request => {
    const url = new URL(request.url);
    if (url.host !== 'app') return new Response('Not found',{status:404});
    let target;
    try {target=path.resolve(dist,'.'+decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname));} catch {return new Response('Bad path',{status:400});}
    if (!target.startsWith(dist+path.sep)) return new Response('Forbidden',{status:403});
    return net.fetch(pathToFileURL(target).toString());
  });
  session.defaultSession.setPermissionRequestHandler((_w,_p,callback)=>callback(false));
  session.defaultSession.setPermissionCheckHandler(()=>false);
  ipcMain.handle('aero:info', event => {authorize(event);return {version:app.getVersion(),platform:process.platform,offline:true};});
  startup=startBackend();
  startup.catch(()=>{});
  ipcMain.handle('aero:api', async (event, method, route, body) => {
    authorize(event);
    if (!allowedRequest(method,route) || JSON.stringify(body??null).length>20000) throw new Error('Request not permitted');
    await startup;
    return privateRequest(method,route,body);
  });
  ipcMain.handle('aero:import', async event => {
    authorize(event);await startup;
    const choice=await dialog.showOpenDialog(window,{title:'Import AustroView CSV',filters:[{name:'AustroView CSV',extensions:['csv']}],properties:['openFile']});
    if(choice.canceled) return null;
    const file=choice.filePaths[0];
    if(path.extname(file).toLowerCase()!=='.csv'||fs.statSync(file).size>10_000_000) throw new Error('Choose a CSV smaller than 10 MB');
    return privateRequest('POST','/v1/desktop/import',{filename:path.basename(file),content:fs.readFileSync(file,'utf8')});
  });
  ipcMain.handle('aero:export', async (event,id) => {
    authorize(event);await startup;
    if(typeof id!=='string'||!/^[a-f0-9]{32}$/.test(id))throw new Error('Invalid session');
    const report=await privateRequest('GET',`/v1/desktop/sessions/${id}/report`);
    const choice=await dialog.showSaveDialog(window,{title:'Export research report',defaultPath:'AeroTrace-session-report.json',filters:[{name:'JSON report',extensions:['json']}]});
    if(choice.canceled||!choice.filePath)return false;
    fs.writeFileSync(choice.filePath,JSON.stringify(report,null,2),'utf8'); return true;
  });
  window=new BrowserWindow({width:1500,height:1000,minWidth:1120,minHeight:780,title:'AeroTrace | Engine Health Lab',backgroundColor:'#0a101b',
    icon:path.join(__dirname,'../dist/app-icon.png'),show:false,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,webSecurity:true}});
  window.setMenuBarVisibility(false);
  window.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  window.webContents.on('will-navigate',(event,url)=>{if(!trustedURL(url))event.preventDefault();});
  window.once('ready-to-show',()=>{if(!smokeDir)window.show();});
  await window.loadURL('aerotrace://app/index.html');
  if(smokeDir) {
    fs.mkdirSync(smokeDir,{recursive:true});
    try {
      await startup;
      for(let i=0;i<120;i++) {
        const ready=await window.webContents.executeJavaScript('Boolean(document.querySelector("[data-app-ready=true]"))');
        if(ready)break;
        await new Promise(r=>setTimeout(r,500));
      }
      await new Promise(r=>setTimeout(r,4000));
      const status=await window.webContents.executeJavaScript('({title:document.title,ready:Boolean(document.querySelector("[data-app-ready=true]")),canvas:document.querySelectorAll("canvas").length,text:document.body.innerText})');
      fs.writeFileSync(path.join(smokeDir,'app-smoke.json'),JSON.stringify(status,null,2));
      fs.writeFileSync(path.join(smokeDir,'app-preview.png'),(await window.webContents.capturePage()).toPNG());
      if(!status.ready)throw new Error('Dashboard did not become ready');
    }catch(e){fs.writeFileSync(path.join(smokeDir,'smoke-error.txt'),String(e));process.exitCode=1;}
    app.quit();
  }
}).catch(error=>{dialog.showErrorBox('AeroTrace could not start',String(error));app.quit();});
app.on('second-instance',()=>{if(window){window.show();window.focus();}});
app.on('window-all-closed',()=>app.quit());
app.on('before-quit',event=>{if(!shuttingDown){event.preventDefault();shuttingDown=true;stopBackend().finally(()=>app.quit());}});
