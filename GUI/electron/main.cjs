// electron/main.cjs
const { app, BrowserWindow, shell, ipcMain, Menu, dialog } = require('electron');
const path = require('node:path');
const fs = require('node:fs');

let mainWindow = null;

const isDev = !app.isPackaged && (process.env.NODE_ENV === 'development' || !process.env.PROD);

function sendMenuAction(action) {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('menu-action', action);
  }
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1080,
    minHeight: 700,
    backgroundColor: '#090d16',
    title: 'NL2SQL Studio',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open external links in user's default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http:') || url.startsWith('https:')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  // In dev mode, load Vite dev server; otherwise load dist/index.html
  const devUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173';
  const distHtml = path.join(__dirname, '../dist/index.html');

  if (isDev && !fs.existsSync(distHtml)) {
    loadWithRetry(mainWindow, devUrl);
  } else if (fs.existsSync(distHtml)) {
    mainWindow.loadFile(distHtml);
  } else {
    loadWithRetry(mainWindow, devUrl);
  }

  // Application Menu (Fully Functional)
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Query',
          accelerator: 'CmdOrCtrl+N',
          click: () => sendMenuAction('menu-new-query'),
        },
        {
          label: 'Switch to Query Intake',
          accelerator: 'CmdOrCtrl+1',
          click: () => sendMenuAction('menu-view-query'),
        },
        {
          label: 'Switch to Approval Gate',
          accelerator: 'CmdOrCtrl+2',
          click: () => sendMenuAction('menu-view-approval'),
        },
        { type: 'separator' },
        {
          label: 'Toggle Dark / Light Theme',
          accelerator: 'CmdOrCtrl+T',
          click: () => sendMenuAction('menu-toggle-theme'),
        },
        {
          label: 'Clear Query History',
          click: () => sendMenuAction('menu-clear-history'),
        },
        { type: 'separator' },
        { role: 'quit', label: 'Exit NL2SQL Studio' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo', label: 'Undo' },
        { role: 'redo', label: 'Redo' },
        { type: 'separator' },
        { role: 'cut', label: 'Cut' },
        { role: 'copy', label: 'Copy' },
        { role: 'paste', label: 'Paste' },
        { role: 'selectAll', label: 'Select All' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload', label: 'Reload Window' },
        { role: 'forceReload', label: 'Force Reload' },
        { role: 'toggleDevTools', label: 'Toggle Developer Tools' },
        { type: 'separator' },
        { role: 'resetZoom', label: 'Actual Size' },
        { role: 'zoomIn', label: 'Zoom In' },
        { role: 'zoomOut', label: 'Zoom Out' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: 'Toggle Full Screen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Keyboard Shortcuts',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'Keyboard Shortcuts',
              message: 'NL2SQL Studio Shortcuts',
              detail:
                '• Ctrl+Enter: Run natural language query\n' +
                '• Ctrl+N: Start a new query\n' +
                '• Ctrl+1: Switch to Query Intake\n' +
                '• Ctrl+2: Switch to Approval Gate\n' +
                '• Ctrl+T: Toggle Dark / Light Theme\n' +
                '• Ctrl+R: Reload application',
            });
          },
        },
        {
          label: 'Documentation (GitHub)',
          click: () => {
            shell.openExternal('https://github.com/VanshikaKritiSingh/NL2SQL');
          },
        },
        {
          label: 'About NL2SQL Studio',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About NL2SQL Studio',
              message: 'NL2SQL Studio',
              detail:
                'Natural Language to SQL Workspace & Schema Safety Gate.\n' +
                'Author: Vanshika Kriti Singh (GUI Team Lead)\n' +
                'PBL Project 2026',
            });
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function loadWithRetry(win, url, retries = 20, delayMs = 500) {
  win.loadURL(url).catch((err) => {
    if (retries > 0) {
      setTimeout(() => loadWithRetry(win, url, retries - 1, delayMs), delayMs);
    } else {
      console.error('Failed to load dev server:', err);
    }
  });
}

// Window control IPC handlers
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

// App lifecycle
app.whenReady().then(() => {
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
