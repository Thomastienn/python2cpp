import './App.css';
import { FuncTab } from './components/functab/functab';
import { MyEditor } from './components/myeditor/myeditor';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { PresetSelector } from './components/presetselector/presetselector';
import { Analytics } from '@vercel/analytics/react';

import { useState } from 'react';

export interface ConvertCodeResponse {
    code?: string;
    detail?: string;
    status?: string;
}
export interface FixCodeResponse {
    fix_code?: string;
    detail?: string;
    status?: string;
}

// Security configuration
const SECURITY_CONFIG = {
    MAX_INPUT_SIZE: 30 * 1024, // 30KB max Python code input
    MAX_FILE_SIZE: 50 * 1024, // 50KB max file upload size
    ALLOWED_FILE_TYPES: ['.py'],
    DANGEROUS_IMPORTS: [
        'os',
        'sys',
        'subprocess',
        'eval',
        'exec',
        '__import__',
    ],
};

// Security validation functions
const validateInputSize = (content: string): boolean => {
    return new Blob([content]).size <= SECURITY_CONFIG.MAX_INPUT_SIZE;
};

// const validateFileType = (fileName: string): boolean => {
//     const extension = fileName
//         .toLowerCase()
//         .substring(fileName.lastIndexOf('.'));
//     return SECURITY_CONFIG.ALLOWED_FILE_TYPES.includes(extension);
// };
//
// const validateFileSize = (file: File): boolean => {
//     return file.size <= SECURITY_CONFIG.MAX_FILE_SIZE;
// };

const validatePythonCode = (code: string): string | null => {
    // Check for dangerous imports (basic heuristic)
    const lines = code.toLowerCase().split('\n');
    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('import ') || trimmed.startsWith('from ')) {
            for (const dangerous of SECURITY_CONFIG.DANGEROUS_IMPORTS) {
                if (trimmed.includes(dangerous)) {
                    return `Potentially unsafe import detected: ${dangerous}`;
                }
            }
        }
    }
    return null;
};

const sanitizeErrorMessage = (error: string): string => {
    // Remove potentially sensitive information from error messages
    // const sensitivePatterns = [/File ".*?"/g, /line \d+/g, /Traceback.*?:/g];
    //
    // let sanitized = error;
    // sensitivePatterns.forEach((pattern) => {
    //     sanitized = sanitized.replace(pattern, '[REDACTED]');
    // });

    // return sanitized;
    return error;
};

export function App() {
    const defaultPyCode =
        '# Python code goes here. Drag and drop if you need to';
    const defaultCppCode = '// C++ code will be generated here';

    // Backend URL: use env var if set, otherwise default to Vercel deployment
    // For local dev, create .env with VITE_BACKEND_URL=http://localhost:8000
    // For Vercel, the API lives at the same domain under /api
    const backendUrl = import.meta.env.VITE_BACKEND_URL || '';

    const [pyCode, setPyCode] = useState<string>(defaultPyCode);
    const [cppCode, setCppCode] = useState<string>(defaultCppCode);
    const [pending, setPending] = useState<boolean>(false);
    const [isOpenNoti, setIsOpenNoti] = useState<boolean>(false);
    const [currentNotiMess, setCurrentNotiMess] = useState<string>('');

    const fixCppCode = async () => {
        console.log('Fixing C++ code...');

        // Client-side security validations
        if (!cppCode.trim()) {
            setCppCode('// ERROR: C++ code cannot be empty');
            return;
        }

        if (!validateInputSize(cppCode)) {
            setIsOpenNoti(true);
            setCurrentNotiMess(
                `// ERROR: Code size exceeds maximum limit of ${SECURITY_CONFIG.MAX_INPUT_SIZE / 1024}KB`,
            );
            return;
        }

        const codeValidationError = validatePythonCode(pyCode);
        if (codeValidationError) {
            setIsOpenNoti(true);
            setCurrentNotiMess(`// ERROR: ${codeValidationError}`);
            return;
        }

        setPending(true);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes timeout

            const response = await fetch(
                `${backendUrl}/api/fix`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        cppcode: cppCode,
                    }),
                    signal: controller.signal,
                },
            );

            clearTimeout(timeoutId);
            const data: FixCodeResponse = await response.json();

            if (response.status !== 200) {
                let errorMessage = 'ERROR: Fix failed\n';

                if (response.status === 429) {
                    errorMessage +=
                        'Rate limit exceeded. Please wait before trying again.\n';
                } else if (response.status === 400) {
                    errorMessage += `Input validation error: ${data.detail || 'Invalid input'}\n`;
                } else if (response.status === 408) {
                    errorMessage +=
                        'Request timeout: Code processing took too long\n';
                } else {
                    errorMessage += `Server error (${response.status})\n`;
                }

                if (data.detail) {
                    // Sanitize error message before displaying
                    const sanitizedDetail = sanitizeErrorMessage(data.detail);
                    errorMessage += `Details: ${sanitizedDetail}`;
                }

                setIsOpenNoti(true);
                setCurrentNotiMess('//' + errorMessage.replace('\n', '\n// '));
            } else {
                // console.log('Fix response:', data, data.fix_code);
                setCppCode(data.fix_code || cppCode);
                console.log('Fix complete!');
            }
        } catch (error) {
            console.error('Error during fixing:', error);

            let errorMessage = '// ERROR: Failed to fix C++ code\n';
            if (error instanceof Error) {
                if (error.name === 'AbortError') {
                    errorMessage += '// Request timed out after 2 minutes\n';
                } else if (error.message.includes('fetch')) {
                    errorMessage +=
                        '// Network error - please check your connection\n';
                } else {
                    errorMessage += '// Unexpected error occurred\n';
                }
            } else {
                errorMessage += '// Unknown error occurred\n';
            }
            errorMessage += '// Check console for more details';

            setIsOpenNoti(true);
            setCurrentNotiMess(errorMessage);
        } finally {
            setPending(false);
        }
    };

    const convertPythonToCpp = async () => {
        console.log('Converting Python to C++...');

        // Client-side security validations
        if (!pyCode.trim()) {
            setCppCode('// ERROR: Python code cannot be empty');
            return;
        }

        if (!validateInputSize(pyCode)) {
            setCppCode(
                `// ERROR: Code size exceeds maximum limit of ${SECURITY_CONFIG.MAX_INPUT_SIZE / 1024}KB`,
            );
            return;
        }

        const codeValidationError = validatePythonCode(pyCode);
        if (codeValidationError) {
            setCppCode(`// ERROR: ${codeValidationError}`);
            return;
        }

        setPending(true);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes timeout

            const response = await fetch(
                `${backendUrl}/api/convert`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        pycode: pyCode,
                    }),
                    signal: controller.signal,
                },
            );

            clearTimeout(timeoutId);
            const data: ConvertCodeResponse = await response.json();

            if (response.status !== 200) {
                let errorMessage = 'ERROR: Conversion failed\n';

                if (response.status === 429) {
                    errorMessage +=
                        'Rate limit exceeded. Please wait before trying again.\n';
                } else if (response.status === 400) {
                    errorMessage += `Input validation error: ${data.detail || 'Invalid input'}\n`;
                } else if (response.status === 408) {
                    errorMessage +=
                        'Request timeout: Code processing took too long\n';
                } else {
                    errorMessage += `Server error (${response.status})\n`;
                }

                if (data.detail) {
                    // Sanitize error message before displaying
                    const sanitizedDetail = sanitizeErrorMessage(data.detail);
                    errorMessage += `Details: ${sanitizedDetail}`;
                }

                setCppCode('//' + errorMessage.replace('\n', '\n// '));
            } else {
                setCppCode(
                    data.code || '// ERROR: No code returned from server',
                );
                console.log('Conversion complete!');
            }
        } catch (error) {
            console.error('Error during conversion:', error);

            let errorMessage = '// ERROR: Failed to convert Python to C++\n';
            if (error instanceof Error) {
                if (error.name === 'AbortError') {
                    errorMessage += '// Request timed out after 2 minutes\n';
                } else if (error.message.includes('fetch')) {
                    errorMessage +=
                        '// Network error - please check your connection\n';
                } else {
                    errorMessage += '// Unexpected error occurred\n';
                }
            } else {
                errorMessage += '// Unknown error occurred\n';
            }
            errorMessage += '// Check console for more details';

            setCppCode(errorMessage);
        } finally {
            setPending(false);
        }
    };

    const resetEditors = () => {
        setPyCode(defaultPyCode);
        setCppCode(defaultCppCode);
    };

    useEffect(() => {
        // Warm up serverless function
        fetch(`${backendUrl}/api/`)
    }, []);

    return (
        <div className="main-content">
            <SpeedInsights />
            <Analytics />
            {isOpenNoti && (
                <div className="noti-bar">
                    {currentNotiMess}
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
            <FuncTab funcConvert={convertPythonToCpp} funcFix={fixCppCode} />
            <PresetSelector onSelectPreset={setPyCode} />
            <div className="editor">
                <MyEditor
                    code={pyCode}
                    setCode={setPyCode}
                    language="python"
                    pending={false}
                    funcReset={resetEditors}
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
