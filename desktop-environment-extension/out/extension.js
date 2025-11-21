"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const fileManager_1 = require("./fileManager");
class DesktopEnvironment {
    constructor(context) {
        this.windows = new Map();
        this.context = context;
    }
    createDesktop() {
        if (this.desktopPanel) {
            this.desktopPanel.reveal(vscode.ViewColumn.One);
            return;
        }
        this.desktopPanel = vscode.window.createWebviewPanel('desktop', 'Desktop', vscode.ViewColumn.One, {
            enableScripts: true,
            retainContextWhenHidden: true
        });
        this.desktopPanel.webview.html = this.getDesktopHTML();
        this.desktopPanel.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'getDesktopIcons':
                    const icons = this.getDesktopIcons();
                    this.desktopPanel?.webview.postMessage({
                        command: 'desktopIcons',
                        icons: icons
                    });
                    break;
                case 'openApplication':
                    if (message.appId === 'lattice-demo') {
                        await this.openLatticeDemoInDesktop();
                    }
                    break;
                case 'openFolder':
                    this.openFolderWindowInDesktop(message.path);
                    break;
                case 'saveLattice':
                    await this.saveLatticeToFile(message.data);
                    break;
                case 'folderWindowMessage':
                    await this.handleFolderWindowMessage(message);
                    break;
            }
        }, undefined, this.context.subscriptions);
        this.desktopPanel.onDidDispose(() => {
            this.desktopPanel = undefined;
        });
    }
    getDesktopIcons() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const icons = [];
        if (workspaceFolders && workspaceFolders.length > 0) {
            const workspaceRoot = workspaceFolders[0].uri.fsPath;
            const odrasPath = path.join(workspaceRoot, '.odras');
            if (fs.existsSync(odrasPath)) {
                icons.push({
                    id: 'projects',
                    name: 'Projects',
                    type: 'folder',
                    icon: '📁',
                    path: odrasPath
                });
            }
            icons.push({
                id: 'workspace',
                name: 'Workspace',
                type: 'folder',
                icon: '📂',
                path: workspaceRoot
            });
        }
        icons.push({
            id: 'lattice-demo',
            name: 'Lattice Demo',
            type: 'application',
            icon: '🔷',
            appId: 'lattice-demo'
        });
        return icons;
    }
    async openLatticeDemoInDesktop() {
        if (!this.desktopPanel) {
            this.createDesktop();
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        const windowId = `lattice-demo-${Date.now()}`;
        const demoUrl = 'http://localhost:8082/intelligent_lattice_demo.html';
        // Check if server is running
        try {
            const testResponse = await fetch(demoUrl);
            if (!testResponse.ok) {
                throw new Error(`Server not responding: ${testResponse.status}`);
            }
        }
        catch (error) {
            vscode.window.showWarningMessage('Demo server not running on port 8082. Start it with: cd scripts/demo && ./demo.sh start', 'OK');
            return;
        }
        // Create window with iframe
        this.desktopPanel?.webview.postMessage({
            command: 'createApplicationWindow',
            windowId: windowId,
            title: 'Lattice Demo',
            url: demoUrl
        });
        this.windows.set(windowId, {
            id: windowId,
            panel: this.desktopPanel,
            type: 'app',
            title: 'Lattice Demo'
        });
    }
    async openFolderWindowInDesktop(folderPath) {
        if (!this.desktopPanel) {
            this.createDesktop();
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        const folderName = path.basename(folderPath);
        const windowId = `folder-${Date.now()}`;
        let items = [];
        try {
            items = await fileManager_1.FileManager.readDirectory(folderPath);
        }
        catch (error) {
            vscode.window.showErrorMessage(`Error reading folder: ${error.message}`);
            return;
        }
        this.desktopPanel?.webview.postMessage({
            command: 'createFolderWindow',
            windowId: windowId,
            folderPath: folderPath,
            folderName: folderName,
            items: items.map(item => ({
                name: item.name,
                path: item.path,
                type: item.type,
                size: item.size,
                modified: item.modified?.toISOString()
            }))
        });
        this.windows.set(windowId, {
            id: windowId,
            panel: this.desktopPanel,
            type: 'folder',
            title: `Folder: ${folderName}`
        });
    }
    async handleFolderWindowMessage(message) {
        const { windowId, action, data } = message;
        // Handle folder window actions here
    }
    async saveLatticeToFile(data) {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }
        const workspaceRoot = workspaceFolders[0].uri.fsPath;
        const odrasDemoDir = path.join(workspaceRoot, '.odras', 'demo');
        // Create directory if it doesn't exist
        if (!fs.existsSync(odrasDemoDir)) {
            fs.mkdirSync(odrasDemoDir, { recursive: true });
        }
        // Save files
        const files = [
            { name: 'lattice.json', data: data.lattice },
            { name: 'projects.json', data: data.projects },
            { name: 'registry.json', data: data.registry },
            { name: 'workflow-history.json', data: data.workflowHistory },
            { name: 'llm-audit-trail.json', data: data.llmAuditTrail }
        ];
        for (const file of files) {
            if (file.data !== undefined && file.data !== null) {
                const filePath = path.join(odrasDemoDir, file.name);
                fs.writeFileSync(filePath, JSON.stringify(file.data, null, 2), 'utf8');
            }
        }
        vscode.window.showInformationMessage('✅ Saved lattice data to .odras/demo/');
    }
    getDesktopHTML() {
        return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-src http://localhost:8082 http://localhost:8083;">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            overflow: hidden;
        }
        .desktop {
            width: 100%;
            height: 100%;
            padding: 20px;
            display: flex;
            flex-wrap: wrap;
            align-content: flex-start;
            gap: 20px;
        }
        .desktop-icon {
            width: 80px;
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            padding: 10px;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .desktop-icon:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: scale(1.05);
        }
        .icon-image {
            font-size: 48px;
            margin-bottom: 8px;
        }
        .icon-label {
            color: white;
            font-size: 12px;
            text-align: center;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        }
        .window {
            position: absolute;
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            min-width: 400px;
            min-height: 300px;
            z-index: 1000;
            transition: all 0.2s ease;
        }
        .window.maximized {
            border-radius: 0;
            transition: none;
        }
        .window.resizing {
            transition: none;
        }
        .window-resize-handle {
            position: absolute;
            background: transparent;
        }
        .window-resize-handle:hover {
            background: rgba(102, 126, 234, 0.2);
        }
        .window-titlebar {
            background: #2d2d2d;
            color: white;
            padding: 8px 12px;
            display: flex;
            justify-content: space-between;
            cursor: move;
            border-radius: 8px 8px 0 0;
        }
        .window-controls {
            display: flex;
            gap: 8px;
        }
        .window-control {
            width: 24px;
            height: 24px;
            border: none;
            background: transparent;
            color: white;
            cursor: pointer;
            border-radius: 4px;
        }
        .window-control:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        .window-content {
            flex: 1;
            overflow: hidden;
            padding: 0;
        }
    </style>
</head>
<body>
    <div class="desktop" id="desktop"></div>
    
    <script>
        const vscode = acquireVsCodeApi();
        let windows = [];
        let zIndex = 1000;

        // Request icons
        vscode.postMessage({ command: 'getDesktopIcons' });

        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.command) {
                case 'desktopIcons':
                    renderIcons(message.icons);
                    break;
                case 'createApplicationWindow':
                    createApplicationWindow(message);
                    break;
                case 'createFolderWindow':
                    createFolderWindow(message);
                    break;
            }
        });

        function renderIcons(icons) {
            const desktop = document.getElementById('desktop');
            desktop.innerHTML = '';

            icons.forEach(icon => {
                const iconEl = document.createElement('div');
                iconEl.className = 'desktop-icon';
                iconEl.innerHTML = \`
                    <div class="icon-image">\${icon.icon}</div>
                    <div class="icon-label">\${icon.name}</div>
                \`;

                iconEl.addEventListener('dblclick', () => {
                    if (icon.type === 'application') {
                        vscode.postMessage({
                            command: 'openApplication',
                            appId: icon.appId
                        });
                    } else if (icon.type === 'folder') {
                        vscode.postMessage({
                            command: 'openFolder',
                            path: icon.path
                        });
                    }
                });

                desktop.appendChild(iconEl);
            });
        }

        function createApplicationWindow(data) {
            const { windowId, title, url } = data;
            
            const win = document.createElement('div');
            win.className = 'window';
            win.id = windowId;
            win.style.zIndex = zIndex++;
            win.style.left = '100px';
            win.style.top = '100px';
            win.style.width = '1200px';
            win.style.height = '800px';

            win.innerHTML = \`
                <div class="window-titlebar">
                    <div>\${title}</div>
                    <div class="window-controls">
                        <button class="window-control" onclick="minimizeWindow('\${windowId}')" title="Minimize">_</button>
                        <button class="window-control" onclick="maximizeWindow('\${windowId}')" title="Maximize/Restore">□</button>
                        <button class="window-control" onclick="closeWindow('\${windowId}')" title="Close">×</button>
                    </div>
                </div>
                <div class="window-content">
                    <iframe id="\${windowId}-iframe" style="width: 100%; height: 100%; border: none;" src="\${url}" sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"></iframe>
                </div>
                <div class="window-resize-handle window-resize-e" style="position: absolute; right: 0; top: 40px; bottom: 40px; width: 5px; cursor: ew-resize;"></div>
                <div class="window-resize-handle window-resize-s" style="position: absolute; left: 40px; right: 40px; bottom: 0; height: 5px; cursor: ns-resize;"></div>
                <div class="window-resize-handle window-resize-w" style="position: absolute; left: 0; top: 40px; bottom: 40px; width: 5px; cursor: ew-resize;"></div>
                <div class="window-resize-handle window-resize-n" style="position: absolute; left: 40px; right: 40px; top: 28px; height: 5px; cursor: ns-resize;"></div>
                <div class="window-resize-handle window-resize-se" style="position: absolute; right: 0; bottom: 0; width: 20px; height: 20px; cursor: nwse-resize;"></div>
                <div class="window-resize-handle window-resize-sw" style="position: absolute; left: 0; bottom: 0; width: 20px; height: 20px; cursor: nesw-resize;"></div>
                <div class="window-resize-handle window-resize-ne" style="position: absolute; right: 0; top: 28px; width: 20px; height: 20px; cursor: nesw-resize;"></div>
                <div class="window-resize-handle window-resize-nw" style="position: absolute; left: 0; top: 28px; width: 20px; height: 20px; cursor: nwse-resize;"></div>
            \`;

            makeDraggable(win);
            document.body.appendChild(win);
            windows.push(windowId);

            // Listen for messages from iframe
            window.addEventListener('message', (event) => {
                if (event.data && event.data.source === 'lattice-demo-iframe') {
                    // Forward to extension host
                    vscode.postMessage({
                        command: event.data.command,
                        data: event.data.data
                    });
                }
            });
        }

        function createFolderWindow(data) {
            const { windowId, folderName, items } = data;
            
            const win = document.createElement('div');
            win.className = 'window';
            win.id = windowId;
            win.style.zIndex = zIndex++;
            win.style.left = '150px';
            win.style.top = '150px';
            win.style.width = '700px';
            win.style.height = '500px';

            const itemsHTML = items.map(item => \`
                <div style="padding: 8px; cursor: pointer;">
                    \${item.type === 'directory' ? '📁' : '📄'} \${item.name}
                </div>
            \`).join('');

            win.innerHTML = \`
                <div class="window-titlebar">
                    <div>📁 \${folderName}</div>
                    <div class="window-controls">
                        <button class="window-control" onclick="minimizeWindow('\${windowId}')" title="Minimize">_</button>
                        <button class="window-control" onclick="maximizeWindow('\${windowId}')" title="Maximize/Restore">□</button>
                        <button class="window-control" onclick="closeWindow('\${windowId}')" title="Close">×</button>
                    </div>
                </div>
                <div class="window-content" style="padding: 16px; overflow: auto;">
                    \${itemsHTML}
                </div>
                <div class="window-resize-handle window-resize-e" style="position: absolute; right: 0; top: 40px; bottom: 40px; width: 5px; cursor: ew-resize;"></div>
                <div class="window-resize-handle window-resize-s" style="position: absolute; left: 40px; right: 40px; bottom: 0; height: 5px; cursor: ns-resize;"></div>
                <div class="window-resize-handle window-resize-w" style="position: absolute; left: 0; top: 40px; bottom: 40px; width: 5px; cursor: ew-resize;"></div>
                <div class="window-resize-handle window-resize-n" style="position: absolute; left: 40px; right: 40px; top: 28px; height: 5px; cursor: ns-resize;"></div>
                <div class="window-resize-handle window-resize-se" style="position: absolute; right: 0; bottom: 0; width: 20px; height: 20px; cursor: nwse-resize;"></div>
                <div class="window-resize-handle window-resize-sw" style="position: absolute; left: 0; bottom: 0; width: 20px; height: 20px; cursor: nesw-resize;"></div>
                <div class="window-resize-handle window-resize-ne" style="position: absolute; right: 0; top: 28px; width: 20px; height: 20px; cursor: nesw-resize;"></div>
                <div class="window-resize-handle window-resize-nw" style="position: absolute; left: 0; top: 28px; width: 20px; height: 20px; cursor: nwse-resize;"></div>
            \`;

            makeDraggable(win);
            makeResizable(win);
            document.body.appendChild(win);
            windows.push(windowId);
        }

        function makeDraggable(element) {
            const titlebar = element.querySelector('.window-titlebar');
            let isDragging = false;
            let startX, startY, startLeft, startTop;

            titlebar.addEventListener('mousedown', (e) => {
                if (e.target.classList.contains('window-control')) return;
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                startLeft = element.offsetLeft;
                startTop = element.offsetTop;
                element.style.zIndex = zIndex++;
            });

            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                element.style.left = (startLeft + e.clientX - startX) + 'px';
                element.style.top = (startTop + e.clientY - startY) + 'px';
            });

            document.addEventListener('mouseup', () => {
                isDragging = false;
            });
        }

        function minimizeWindow(windowId) {
            const win = document.getElementById(windowId);
            if (win) {
                win.style.display = 'none';
                // TODO: Add to taskbar's minimized windows
            }
        }

        function maximizeWindow(windowId) {
            const win = document.getElementById(windowId);
            if (!win) return;
            
            const isMaximized = win.classList.contains('maximized');
            
            if (isMaximized) {
                // Restore to previous size
                win.classList.remove('maximized');
                win.style.width = win.dataset.prevWidth || '1200px';
                win.style.height = win.dataset.prevHeight || '800px';
                win.style.left = win.dataset.prevLeft || '100px';
                win.style.top = win.dataset.prevTop || '100px';
            } else {
                // Save current size and maximize
                win.dataset.prevWidth = win.style.width;
                win.dataset.prevHeight = win.style.height;
                win.dataset.prevLeft = win.style.left;
                win.dataset.prevTop = win.style.top;
                
                win.classList.add('maximized');
                win.style.width = '100%';
                win.style.height = '100%';
                win.style.left = '0';
                win.style.top = '0';
            }
        }

        function closeWindow(windowId) {
            const win = document.getElementById(windowId);
            if (win) {
                win.remove();
                windows = windows.filter(id => id !== windowId);
            }
        }

        function makeResizable(element) {
            const handles = element.querySelectorAll('.window-resize-handle');
            
            handles.forEach(handle => {
                let isResizing = false;
                let startX, startY, startWidth, startHeight, startLeft, startTop;
                let resizeDirection = '';
                
                // Determine resize direction from class
                if (handle.classList.contains('window-resize-e')) resizeDirection = 'e';
                else if (handle.classList.contains('window-resize-s')) resizeDirection = 's';
                else if (handle.classList.contains('window-resize-w')) resizeDirection = 'w';
                else if (handle.classList.contains('window-resize-n')) resizeDirection = 'n';
                else if (handle.classList.contains('window-resize-se')) resizeDirection = 'se';
                else if (handle.classList.contains('window-resize-sw')) resizeDirection = 'sw';
                else if (handle.classList.contains('window-resize-ne')) resizeDirection = 'ne';
                else if (handle.classList.contains('window-resize-nw')) resizeDirection = 'nw';
                
                handle.addEventListener('mousedown', (e) => {
                    isResizing = true;
                    startX = e.clientX;
                    startY = e.clientY;
                    startWidth = element.offsetWidth;
                    startHeight = element.offsetHeight;
                    startLeft = element.offsetLeft;
                    startTop = element.offsetTop;
                    element.classList.add('resizing');
                    e.preventDefault();
                    e.stopPropagation();
                });
                
                document.addEventListener('mousemove', (e) => {
                    if (!isResizing) return;
                    
                    const deltaX = e.clientX - startX;
                    const deltaY = e.clientY - startY;
                    
                    let newWidth = startWidth;
                    let newHeight = startHeight;
                    let newLeft = startLeft;
                    let newTop = startTop;
                    
                    // Calculate new dimensions based on resize direction
                    if (resizeDirection.includes('e')) {
                        newWidth = startWidth + deltaX;
                    }
                    if (resizeDirection.includes('w')) {
                        newWidth = startWidth - deltaX;
                        newLeft = startLeft + deltaX;
                    }
                    if (resizeDirection.includes('s')) {
                        newHeight = startHeight + deltaY;
                    }
                    if (resizeDirection.includes('n')) {
                        newHeight = startHeight - deltaY;
                        newTop = startTop + deltaY;
                    }
                    
                    // Apply minimum size constraints
                    if (newWidth >= 400 && newHeight >= 300) {
                        element.style.width = newWidth + 'px';
                        element.style.height = newHeight + 'px';
                        element.style.left = newLeft + 'px';
                        element.style.top = newTop + 'px';
                    }
                });
                
                document.addEventListener('mouseup', () => {
                    if (isResizing) {
                        isResizing = false;
                        element.classList.remove('resizing');
                    }
                });
            });
        }
    </script>
</body>
</html>`;
    }
}
let desktop;
function activate(context) {
    desktop = new DesktopEnvironment(context);
    // Auto-open desktop if workspace is open
    if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
        desktop.createDesktop();
    }
    // Register command
    const disposable = vscode.commands.registerCommand('desktop.openDesktop', () => {
        desktop?.createDesktop();
    });
    // Add status bar button
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = '$(desktop) Desktop';
    statusBarItem.command = 'desktop.openDesktop';
    statusBarItem.tooltip = 'Open Desktop Environment';
    statusBarItem.show();
    context.subscriptions.push(disposable, statusBarItem);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map