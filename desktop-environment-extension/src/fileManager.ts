import * as fs from 'fs';
import * as path from 'path';

export interface FileItem {
    name: string;
    path: string;
    type: 'file' | 'directory';
    size?: number;
    modified?: Date;
}

export class FileManager {
    static async readDirectory(dirPath: string): Promise<FileItem[]> {
        const items: FileItem[] = [];
        const entries = fs.readdirSync(dirPath, { withFileTypes: true });
        
        for (const entry of entries) {
            const fullPath = path.join(dirPath, entry.name);
            const stats = fs.statSync(fullPath);
            
            items.push({
                name: entry.name,
                path: fullPath,
                type: entry.isDirectory() ? 'directory' : 'file',
                size: entry.isFile() ? stats.size : undefined,
                modified: stats.mtime
            });
        }
        
        return items.sort((a, b) => {
            if (a.type !== b.type) {
                return a.type === 'directory' ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
        });
    }
    
    static async pathExists(filePath: string): Promise<boolean> {
        return fs.existsSync(filePath);
    }
}
