import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

/**
 * VS Code Extension for ODRAS Intelligent Lattice Demo
 * 
 * This extension provides a webview panel that hosts the intelligent lattice demo.
 * Results can be saved as files in the workspace for indexing and version control.
 */

let currentPanel: vscode.WebviewPanel | undefined = undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('ODRAS Intelligent Lattice Demo extension is now active');

    // Register command to open the demo
    const disposable = vscode.commands.registerCommand('odras.openLatticeDemo', async () => {
        try {
            // Ensure workspace folder is open
            await ensureWorkspaceFolderOpen();
            createOrShowWebviewPanel(context);
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to open demo: ${error}`);
            console.error('Error opening demo:', error);
        }
    });

    context.subscriptions.push(disposable);
}

/**
 * Ensure a workspace folder is open, auto-opening ODRAS root if needed
 */
async function ensureWorkspaceFolderOpen(): Promise<void> {
    let workspaceFolders = vscode.workspace.workspaceFolders;
    
    // If no workspace folder is open, try to auto-open ODRAS root
    if (!workspaceFolders || workspaceFolders.length === 0) {
        const odrasRoot = getSuggestedWorkspaceFolder();
        
        if (odrasRoot && fs.existsSync(odrasRoot)) {
            // Automatically add ODRAS root to workspace
            await vscode.workspace.updateWorkspaceFolders(0, 0, { uri: vscode.Uri.file(odrasRoot) });
            vscode.window.showInformationMessage(`Opened workspace: ${odrasRoot}`);
        } else {
            // If we can't detect ODRAS root, prompt user
            const action = await vscode.window.showWarningMessage(
                'No workspace folder open. Select the ODRAS project folder to continue.',
                'Select Folder',
                'Cancel'
            );
            
            if (action === 'Select Folder') {
                const folderUri = await vscode.window.showOpenDialog({
                    canSelectFiles: false,
                    canSelectFolders: true,
                    canSelectMany: false,
                    openLabel: 'Select ODRAS Project Folder',
                    title: 'Select folder where .odras/demo/ will be created'
                });
                
                if (folderUri && folderUri.length > 0) {
                    await vscode.workspace.updateWorkspaceFolders(0, 0, { uri: folderUri[0] });
                } else {
                    throw new Error('No folder selected. Please open a workspace folder.');
                }
            } else {
                throw new Error('Workspace folder required. Please open a folder in VS Code.');
            }
        }
    }
}

export function deactivate() {}

/**
 * Create or show the webview panel for the lattice demo
 */
function createOrShowWebviewPanel(context: vscode.ExtensionContext) {
    const columnToShowIn = vscode.window.activeTextEditor
        ? vscode.ViewColumn.Beside
        : vscode.ViewColumn.One;

    if (currentPanel) {
        // If panel already exists, reveal it
        currentPanel.reveal(columnToShowIn);
        return;
    }

    // Create new panel
    currentPanel = vscode.window.createWebviewPanel(
        'odrasLatticeDemo',
        'ODRAS Intelligent Lattice Demo',
        columnToShowIn,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [
                vscode.Uri.file(path.join(context.extensionPath, 'media')),
                vscode.Uri.file(path.join(context.extensionPath, '..', 'static'))
            ]
        }
    );

    // Set webview content
    try {
        const htmlContent = getWebviewContent(context, currentPanel.webview);
        currentPanel.webview.html = htmlContent;
        console.log('Webview HTML content set successfully');
    } catch (error) {
        console.error('Error setting webview content:', error);
        currentPanel.webview.html = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error</title>
                <style>
                    body { font-family: sans-serif; padding: 20px; }
                    .error { color: red; }
                </style>
            </head>
            <body>
                <h1>Error Loading Demo</h1>
                <p class="error">${error}</p>
                <p>Check the Developer Console (Help > Toggle Developer Tools) for details.</p>
            </body>
            </html>
        `;
    }

    // Handle messages from webview
    currentPanel.webview.onDidReceiveMessage(
        async (message) => {
            switch (message.command) {
                case 'saveLattice':
                    await saveLatticeToFile(message.data);
                    break;
                case 'saveWorkflowHistory':
                    await saveWorkflowHistory(message.data);
                    break;
                case 'saveLLMAuditTrail':
                    await saveLLMAuditTrail(message.data);
                    break;
                case 'loadWorkspaceData':
                    const workspaceData = await loadWorkspaceData();
                    currentPanel?.webview.postMessage({
                        command: 'workspaceDataLoaded',
                        data: workspaceData
                    });
                    break;
                case 'alert':
                    vscode.window.showInformationMessage(message.text);
                    break;
                case 'error':
                    vscode.window.showErrorMessage(message.text);
                    break;
            }
        },
        undefined,
        context.subscriptions
    );

    // Clean up when panel is closed
    currentPanel.onDidDispose(
        () => {
            currentPanel = undefined;
        },
        null,
        context.subscriptions
    );
}

/**
 * Get webview HTML content - loads the existing demo HTML and adapts it for VS Code
 */
function getWebviewContent(context: vscode.ExtensionContext, webview: vscode.Webview): string {
    // Get paths to static resources
    // Extension path: scripts/demo/vscode-extension
    // Static path: scripts/demo/static
    const staticPath = path.join(context.extensionPath, '..', 'static');
    const htmlPath = path.join(staticPath, 'intelligent_lattice_demo.html');
    const cssPath = vscode.Uri.file(path.join(staticPath, 'lattice_demo.css'));
    const jsPath = vscode.Uri.file(path.join(staticPath, 'intelligent_lattice.js'));
    
    // Convert to webview URIs
    const cssUri = webview.asWebviewUri(cssPath);
    const jsUri = webview.asWebviewUri(jsPath);
    
    // Debug: Log paths
    console.log('Extension path:', context.extensionPath);
    console.log('Static path:', staticPath);
    console.log('HTML path:', htmlPath);
    console.log('HTML exists:', fs.existsSync(htmlPath));
    
    // Read the existing HTML file
    let htmlContent = '';
    if (!fs.existsSync(htmlPath)) {
        const errorMsg = `HTML file not found at: ${htmlPath}`;
        console.error(errorMsg);
        throw new Error(errorMsg);
    }
    
    try {
        htmlContent = fs.readFileSync(htmlPath, 'utf8');
        
        // Inject VS Code API and message handling
        htmlContent = htmlContent.replace(
            '</head>',
            `
    <script>
        const vscode = acquireVsCodeApi();
        
        // Override alert/console to use VS Code messages
        const originalAlert = window.alert;
        window.alert = function(message) {
            vscode.postMessage({ command: 'alert', text: String(message) });
        };
        
        // Add save/load functions after IntelligentLatticeGenerator is initialized
        window.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                if (window.intelligentLattice) {
                    // Add save to workspace button functionality
                    const saveButton = document.createElement('button');
                    saveButton.textContent = '💾 Save to Workspace';
                    saveButton.className = 'btn';
                    saveButton.style.marginLeft = '12px';
                    saveButton.onclick = () => {
                        const data = {
                            lattice: window.intelligentLattice.currentLattice,
                            projects: window.intelligentLattice.createdProjects,
                            registry: window.intelligentLattice.projectRegistry,
                            workflowHistory: window.intelligentLattice.workflowHistory,
                            llmAuditTrail: window.intelligentLattice.llmAuditTrail
                        };
                        vscode.postMessage({ command: 'saveLattice', data: data });
                    };
                    
                    const loadButton = document.createElement('button');
                    loadButton.textContent = '📂 Load from Workspace';
                    loadButton.className = 'btn';
                    loadButton.style.marginLeft = '8px';
                    loadButton.onclick = () => {
                        vscode.postMessage({ command: 'loadWorkspaceData' });
                    };
                    
                    // Find header controls and add buttons
                    const headerControls = document.querySelector('.header-controls');
                    if (headerControls) {
                        headerControls.appendChild(saveButton);
                        headerControls.appendChild(loadButton);
                    }
                }
            }, 1000);
        });
        
        // Listen for messages from extension
        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.command) {
                case 'workspaceDataLoaded':
                    if (window.intelligentLattice && message.data) {
                        // Restore lattice data
                        if (message.data.lattice) {
                            window.intelligentLattice.currentLattice = message.data.lattice;
                            window.intelligentLattice.loadLattice(message.data.lattice);
                        }
                        if (message.data.registry) {
                            window.intelligentLattice.projectRegistry = message.data.registry;
                        }
                        if (message.data.workflowHistory) {
                            window.intelligentLattice.workflowHistory = message.data.workflowHistory;
                        }
                        if (message.data.llmAuditTrail) {
                            window.intelligentLattice.llmAuditTrail = message.data.llmAuditTrail;
                        }
                    }
                    break;
            }
        });
    </script>
</head>`
        );
        
        // Update script src to use webview URI
        htmlContent = htmlContent.replace(
            /src="([^"]*intelligent_lattice\.js[^"]*)"/g,
            `src="${jsUri}"`
        );
        
        // Update CSS link to use webview URI
        htmlContent = htmlContent.replace(
            /href="([^"]*lattice_demo\.css[^"]*)"/g,
            `href="${cssUri}"`
        );
        
        return htmlContent;
    } catch (error) {
        console.error('Error processing HTML:', error);
        // Return error page instead of throwing
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error Loading Demo</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1e1e1e; color: #fff; }
        .error { color: #f48771; background: #3c1f1f; padding: 15px; border-radius: 5px; margin: 10px 0; }
        code { background: #2d2d2d; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Error Loading Demo</h1>
    <div class="error">
        <strong>Error:</strong> ${error}<br>
        <strong>HTML Path:</strong> <code>${htmlPath}</code><br>
        <strong>Extension Path:</strong> <code>${context.extensionPath}</code>
    </div>
    <p>Check the Developer Console (Help > Toggle Developer Tools) for more details.</p>
</body>
</html>`;
    }
}

/**
 * Get suggested workspace folder based on extension location
 */
function getSuggestedWorkspaceFolder(): string | undefined {
    // Try to detect ODRAS project root from extension path
    // Extension is at: ~/working/ODRAS/scripts/demo/vscode-extension
    // ODRAS root should be: ~/working/ODRAS
    
    // Get extension context path (where extension is installed)
    // In development: extensionPath is the extension folder
    // In production: might be different, so we try multiple approaches
    
    // Approach 1: Try to get from extension path
    try {
        // Extension context gives us the extension path
        // We need to navigate up: vscode-extension -> demo -> scripts -> ODRAS root
        const extensionPath = path.resolve(__dirname, '..', '..', '..', '..');
        
        // Check if this looks like ODRAS root (has scripts/, backend/, frontend/, etc.)
        const scriptsDir = path.join(extensionPath, 'scripts');
        const backendDir = path.join(extensionPath, 'backend');
        
        if (fs.existsSync(scriptsDir) && fs.existsSync(backendDir)) {
            return extensionPath;
        }
    } catch (e) {
        // Fall through to next approach
    }
    
    // Approach 2: Try common ODRAS locations
    const homeDir = process.env.HOME || process.env.USERPROFILE;
    if (homeDir) {
        const commonPaths = [
            path.join(homeDir, 'working', 'ODRAS'),
            path.join(homeDir, 'ODRAS'),
            path.join(homeDir, 'projects', 'ODRAS'),
        ];
        
        for (const possiblePath of commonPaths) {
            const scriptsDir = path.join(possiblePath, 'scripts');
            const backendDir = path.join(possiblePath, 'backend');
            if (fs.existsSync(scriptsDir) && fs.existsSync(backendDir)) {
                return possiblePath;
            }
        }
    }
    
    return undefined;
}

/**
 * Save lattice data to workspace files
 */
async function saveLatticeToFile(data: any) {
    // Ensure workspace folder is open
    await ensureWorkspaceFolderOpen();
    
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('Cannot save: No workspace folder open');
        return;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const odrasDir = path.join(workspaceRoot, '.odras');
    const demoDir = path.join(odrasDir, 'demo');

    // Create directories if they don't exist
    if (!fs.existsSync(odrasDir)) {
        fs.mkdirSync(odrasDir, { recursive: true });
    }
    if (!fs.existsSync(demoDir)) {
        fs.mkdirSync(demoDir, { recursive: true });
    }

    // Save lattice structure
    const latticePath = path.join(demoDir, 'lattice.json');
    fs.writeFileSync(latticePath, JSON.stringify(data.lattice || {}, null, 2));

    // Save projects data
    const projectsPath = path.join(demoDir, 'projects.json');
    fs.writeFileSync(projectsPath, JSON.stringify(data.projects || [], null, 2));

    // Save registry
    const registryPath = path.join(demoDir, 'registry.json');
    fs.writeFileSync(registryPath, JSON.stringify(data.registry || {}, null, 2));

    // Save workflow history
    if (data.workflowHistory) {
        const workflowPath = path.join(demoDir, 'workflow-history.json');
        fs.writeFileSync(workflowPath, JSON.stringify(data.workflowHistory, null, 2));
    }

    // Save LLM audit trail
    if (data.llmAuditTrail) {
        const auditPath = path.join(demoDir, 'llm-audit-trail.json');
        fs.writeFileSync(auditPath, JSON.stringify(data.llmAuditTrail, null, 2));
    }

    // Show success message with option to reveal files
    const action = await vscode.window.showInformationMessage(
        `✅ Saved lattice data to .odras/demo/`,
        'Reveal in Explorer'
    );
    
    if (action === 'Reveal in Explorer') {
        // Open the demo directory in explorer
        const demoUri = vscode.Uri.file(demoDir);
        await vscode.commands.executeCommand('revealFileInOS', demoUri);
    }
}

/**
 * Save workflow history to file
 */
async function saveWorkflowHistory(data: any) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        return;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const demoDir = path.join(workspaceRoot, '.odras', 'demo');
    
    if (!fs.existsSync(demoDir)) {
        fs.mkdirSync(demoDir, { recursive: true });
    }

    const filePath = path.join(demoDir, 'workflow-history.json');
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

/**
 * Save LLM audit trail to file
 */
async function saveLLMAuditTrail(data: any) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        return;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const demoDir = path.join(workspaceRoot, '.odras', 'demo');
    
    if (!fs.existsSync(demoDir)) {
        fs.mkdirSync(demoDir, { recursive: true });
    }

    const filePath = path.join(demoDir, 'llm-audit-trail.json');
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

/**
 * Load workspace data
 */
async function loadWorkspaceData(): Promise<any> {
    // Ensure workspace folder is open
    await ensureWorkspaceFolderOpen();
    
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        return null;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const demoDir = path.join(workspaceRoot, '.odras', 'demo');

    if (!fs.existsSync(demoDir)) {
        return null;
    }

    const data: any = {};

    // Load lattice
    const latticePath = path.join(demoDir, 'lattice.json');
    if (fs.existsSync(latticePath)) {
        data.lattice = JSON.parse(fs.readFileSync(latticePath, 'utf8'));
    }

    // Load projects
    const projectsPath = path.join(demoDir, 'projects.json');
    if (fs.existsSync(projectsPath)) {
        data.projects = JSON.parse(fs.readFileSync(projectsPath, 'utf8'));
    }

    // Load registry
    const registryPath = path.join(demoDir, 'registry.json');
    if (fs.existsSync(registryPath)) {
        data.registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
    }

    // Load workflow history
    const workflowPath = path.join(demoDir, 'workflow-history.json');
    if (fs.existsSync(workflowPath)) {
        data.workflowHistory = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
    }

    // Load LLM audit trail
    const auditPath = path.join(demoDir, 'llm-audit-trail.json');
    if (fs.existsSync(auditPath)) {
        data.llmAuditTrail = JSON.parse(fs.readFileSync(auditPath, 'utf8'));
    }

    return data;
}
