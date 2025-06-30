import Prism from 'prismjs';
import './myeditor.css';
import Editor from 'react-simple-code-editor';
import { useState } from 'react';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/themes/prism-tomorrow.css';

export interface MyEditorProps {
    defaultValue?: string;
    language: 'python' | 'cpp';
}

export const MyEditor = ({ defaultValue, language }: MyEditorProps) => {
    const [code, setCode] = useState<string>(defaultValue || '');
    let mlanguages = null;
    if (language === 'python') {
        mlanguages = Prism.languages.python;
    }
    if (language === 'cpp') {
        mlanguages = Prism.languages.cpp;
    }

    if (mlanguages == null) {
        throw new Error('Unsupported language');
    }
    return (
        <div className="actual-editor">
            <Editor
                value={code}
                onValueChange={(code) => setCode(code)}
                highlight={(code) =>
                    Prism.highlight(code, mlanguages, language)
                }
                padding={10}
                style={{
                    fontFamily: '"Fira code", "Fira Mono", monospace',
                    fontSize: 16,
                    width: '100%',
                    height: '100%',
                }}
            />
        </div>
    );
};
