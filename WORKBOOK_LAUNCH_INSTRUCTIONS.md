# How to Launch the Workbook Extension

## ✅ EASIEST METHOD - Use F5 in VS Code/Cursor

1. **Make sure you have `/home/jdehart/working/ODRAS` open in VS Code/Cursor**
   - File → Open Folder → Select `/home/jdehart/working/ODRAS`

2. **Open the Run and Debug panel:**
   - Click the Run icon in the left sidebar (▷ with bug icon)
   - OR press `Ctrl+Shift+D` (Windows/Linux) or `Cmd+Shift+D` (Mac)

3. **Select the configuration:**
   - At the top of the panel, you'll see a dropdown
   - Select **"Run Workbook Extension"**

4. **Press F5** (or click the green play button ▷)
   - This will build and launch the extension
   - A new window called "Extension Development Host" will open

5. **In the Extension Development Host window:**
   - Open Output panel: `View → Output` (or `Ctrl+Shift+U`)
   - Select **"Log (Extension Host)"** from the dropdown
   - Look for the message: `Insight Workbooks activated`

6. **Test the workbook:**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type: `Insight: Create New Workbook`
   - Enter a name and press Enter

## Alternative: Direct VS Code Command

If F5 doesn't work, try this from Windows terminal (not WSL):

```cmd
code --extensionDevelopmentPath="\\wsl$\Ubuntu\home\jdehart\working\ODRAS\insight-platform\extensions\vscode"
```

## Troubleshooting

**Problem:** No "Run Workbook Extension" option
- **Fix:** The `.vscode/launch.json` file should be in `/home/jdehart/working/ODRAS/.vscode/`
- Check it exists: `ls -la /home/jdehart/working/ODRAS/.vscode/launch.json`

**Problem:** Extension doesn't activate
- **Check logs:** Output → "Log (Extension Host)"
- Share any errors you see

**Problem:** F5 does nothing
- **Fix:** Make sure the ODRAS workspace folder is open, not just a file
- File → Open Folder → `/home/jdehart/working/ODRAS`
