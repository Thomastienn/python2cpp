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

    const [pending, setPending] = useState<boolean>(false);

    const convertPythonToCpp = async () => {
        console.log('Converting Python to C++...');
        setPending(true);
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
        setCppCode(data.code || '// ERROR: My bad, this too tough for me :(');
        console.log('Conversion complete!');
        setPending(false);
    };

    const resetEditors = () => {
        setPyCode(defaultPyCode);
        setCppCode(defaultCppCode);
    };

    const funcUpload = () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.py';
        input.onchange = async (event) => {
            const file = (event.target as HTMLInputElement).files?.[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (e) => {
                setPyCode(e.target?.result as string);
            };
            reader.readAsText(file);
        };
        input.click();
    };

    const [isOpenNoti, setIsOpenNoti] = useState<boolean>(true);

    return (
        <div className="main-content">
            {isOpenNoti && (
                <div className="noti-bar">
                    {' '}
                    If you wait for more half a minute, it could be my backend
                    is cold starting.
                    <span
                        className="close-noti"
                        onClick={() => {
                            setIsOpenNoti(false);
                        }}
                    >
                        X
                    </span>
                </div>
            )}
            <h1 className="main-header">Py2Cpp</h1>
            <FuncTab
                funcConvert={convertPythonToCpp}
                funcUpload={funcUpload}
                funcReset={resetEditors}
            />
            <div className="editor">
                <MyEditor
                    code={pyCode}
                    setCode={setPyCode}
                    language="python"
                    pending={false}
                />
                <MyEditor
                    code={cppCode}
                    setCode={setCppCode}
                    language="cpp"
                    pending={pending}
                />
            </div>
        </div>
    );
}
