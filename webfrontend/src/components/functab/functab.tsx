import './functab.css';
import { useState } from 'react';

export interface FuncTabProps {
    funcConvert: () => Promise<void>;
    funcFix: () => Promise<void>;
}

export const FuncTab = ({ funcConvert, funcFix }: FuncTabProps) => {
    const [isConverting, setIsConverting] = useState(false);
    const handleConvert = async () => {
        setIsConverting(true);
        await funcConvert();
        setIsConverting(false);
    };

    const handleFix = async () => {
        setIsConverting(true);
        await funcFix();
        setIsConverting(false);
    };

    return (
        <div className="func-tab">
            <button
                className="func-btn func-convert"
                onClick={handleConvert}
                disabled={isConverting}
                title="Convert from python to C++ using AST and LLM as fallback"
            >
                Convert
            </button>
            <button
                className="func-btn func-fix"
                onClick={handleFix}
                disabled={isConverting}
                title="Fix C++ code using LLM"
            >
                Fix
            </button>
        </div>
    );
};
