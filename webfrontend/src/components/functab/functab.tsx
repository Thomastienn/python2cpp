import './functab.css';
import { useState } from 'react';

export interface FuncTabProps {
    funcConvert: () => Promise<void>;
    funcReset: () => void;
    funcUpload: () => void;
}

export const FuncTab = ({
    funcConvert,
    funcReset,
    funcUpload,
}: FuncTabProps) => {
    const [isConverting, setIsConverting] = useState(false);
    const handleConvert = async () => {
        setIsConverting(true);
        await funcConvert();
        setIsConverting(false);
    };
    return (
        <div className="func-tab">
            <button
                className="func-btn func-convert"
                onClick={handleConvert}
                disabled={isConverting}
            >
                Convert
            </button>
            <button className="func-btn func-upload" onClick={funcUpload}>
                Upload File
            </button>
            <button className="func-btn func-reset" onClick={funcReset}>
                Reset
            </button>
        </div>
    );
};
