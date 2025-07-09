import './functab.css';
import { useState } from 'react';

export interface FuncTabProps {
    funcConvert: () => Promise<void>;
}

export const FuncTab = ({
    funcConvert,
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
            
            
        </div>
    );
};
