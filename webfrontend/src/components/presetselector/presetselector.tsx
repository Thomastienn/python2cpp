import React from 'react';
import { pythonPresets } from '../../utils/presets';
import './presetselector.css';

interface PresetSelectorProps {
    onSelectPreset: (code: string) => void;
}

export const PresetSelector: React.FC<PresetSelectorProps> = ({ onSelectPreset }) => {
    const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const selectedPresetName = event.target.value;
        const selectedPreset = pythonPresets.find(preset => preset.name === selectedPresetName);
        if (selectedPreset) {
            onSelectPreset(selectedPreset.code);
        }
    };

    return (
        <div className="preset-selector-container">
            <label htmlFor="preset-select">Load Preset:</label>
            <select id="preset-select" onChange={handleChange} defaultValue="">
                <option value="" disabled>Select a preset</option>
                {pythonPresets.map((preset) => (
                    <option key={preset.name} value={preset.name}>
                        {preset.name}
                    </option>
                ))}
            </select>
        </div>
    );
};
