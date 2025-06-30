import './App.css';
import { FuncTab } from './components/functab/functab';
import { MyEditor } from './components/myeditor/myeditor';

export function App() {
    return (
        <div className="main-content">
            <h1 className="main-header">Py2Cpp</h1>
            <FuncTab />
            <div className="editor">
                <MyEditor
                    defaultValue="# Paste your code here"
                    language="python"
                />
                <MyEditor
                    defaultValue="// Your generated code will be here\n"
                    language="cpp"
                />
            </div>
        </div>
    );
}
