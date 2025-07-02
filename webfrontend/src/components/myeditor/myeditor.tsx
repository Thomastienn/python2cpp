import './myeditor.css';
import { Editor } from '@monaco-editor/react';
import { useState } from 'react';

export interface MyEditorProps {
    code?: string;
    setCode: (code: string) => void;
    language: 'python' | 'cpp';
    pending: boolean;
}

export const MyEditor = ({
    code,
    setCode,
    language,
    pending,
}: MyEditorProps) => {
    code = code || '';
    const [isDragOver, setIsDragOver] = useState(false);

    const handleDragEnter = (e: React.DragEvent) => {
        if (language === 'python') {
            e.preventDefault();
            e.stopPropagation();
            setIsDragOver(true);
        }
    };

    const handleDragLeave = (e: React.DragEvent) => {
        if (language === 'python') {
            e.preventDefault();
            e.stopPropagation();
            // Only hide if we're actually leaving the container
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX;
            const y = e.clientY;

            if (
                x < rect.left ||
                x > rect.right ||
                y < rect.top ||
                y > rect.bottom
            ) {
                setIsDragOver(false);
            }
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        if (language === 'python') {
            e.preventDefault();
            e.stopPropagation();
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        if (language === 'python') {
            e.preventDefault();
            e.stopPropagation();
            setIsDragOver(false);

            const files = Array.from(e.dataTransfer.files);
            if (files.length > 1) {
                alert('Please drop only one file at a time.');
                return;
            }
            
            if (files.length > 0) {
                const file = files[0];
                
                // Security validations for drag and drop
                const allowedTypes = ['.py'];
                const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
                
                if (!allowedTypes.includes(fileExtension)) {
                    alert(`Invalid file type. Only ${allowedTypes.join(', ')} files are allowed.`);
                    return;
                }
                
                const maxFileSize = 50 * 1024; // 50KB
                if (file.size > maxFileSize) {
                    alert(`File size exceeds maximum limit of ${maxFileSize / 1024}KB.`);
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = (event) => {
                    const content = event.target?.result as string;
                    
                    // Validate content size
                    const maxContentSize = 10 * 1024; // 10KB
                    if (new Blob([content]).size > maxContentSize) {
                        alert(`File content exceeds maximum size limit of ${maxContentSize / 1024}KB.`);
                        return;
                    }
                    
                    setCode(content);
                };
                
                reader.onerror = () => {
                    alert('Error reading file. Please try again.');
                };
                
                reader.readAsText(file);
            }
        }
    };
    return (
        <div
            className={`actual-editor ${pending ? 'pending' : ''} ${isDragOver && language === 'python' ? 'drag-over' : ''}`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
        >
            <Editor
                height="100%"
                language={language}
                value={code}
                onChange={(value) => setCode(value || '')}
                theme="vs-dark"
                options={{
                    fontSize: 16,
                    fontFamily:
                        'Fira Code, Monaco, Consolas, Ubuntu Mono, monospace',
                    lineHeight: 24,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: 'off',
                    automaticLayout: true,
                    lineNumbers: 'on',
                    glyphMargin: false,
                    folding: false,
                    lineDecorationsWidth: 0,
                    lineNumbersMinChars: 3,
                    renderLineHighlight: 'line',
                    selectOnLineNumbers: true,
                    roundedSelection: false,
                    readOnly: language === 'cpp',
                    cursorStyle: language === 'cpp' ? undefined : 'line',
                    cursorBlinking: language === 'cpp' ? undefined : 'blink',
                    hideCursorInOverviewRuler: language === 'cpp',
                    tabSize: 4,
                    insertSpaces: true,
                }}
            />
        </div>
    );
};
