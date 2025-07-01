import './App.css';
import { FuncTab } from './components/functab/functab';
import { MyEditor } from './components/myeditor/myeditor';

import { useState } from 'react';

export interface ConvertCodeResponse {
    code: string;
}

export function App() {
    const defaultPyCode = '# Python code goes here';
    const defaultCppCode = '// C++ code will be generated here';

    const [pyCode, setPyCode] = useState<string>(defaultPyCode);
    const [cppCode, setCppCode] = useState<string>(defaultCppCode);

    const convertPythonToCpp = async () => {
        console.log('Converting Python to C++...');
        const response = await fetch(
            'https://python2cpp.onrender.com/convert',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    pycode: pyCode,
                }),
            },
        );
        if (!response.ok) {
            console.error(
                'Error converting Python to C++:',
                response.statusText,
            );
            return;
        }
        const data: ConvertCodeResponse = await response.json();
        setCppCode(data.code || 'ERROR: No C++ code returned');
        console.log('Conversion complete!');
    };

    const resetEditors = () => {
        setPyCode(defaultPyCode);
        setCppCode(defaultCppCode);
    };

    const funcUpload = () => { };

    return (
        <div className="main-content">
            <h1 className="main-header">Py2Cpp</h1>
            <FuncTab
                funcConvert={convertPythonToCpp}
                funcUpload={funcUpload}
                funcReset={resetEditors}
            />
            <div className="editor">
                <MyEditor code={pyCode} setCode={setPyCode} language="python" />
                <MyEditor code={cppCode} setCode={setCppCode} language="cpp" />
            </div>
        </div>
    );
}
