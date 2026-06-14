import { useRef, useState } from 'react';
import { FiUploadCloud } from 'react-icons/fi';

const ACCEPTED = '.pdf,.csv,.xlsx,.json';

export default function ImportDropzone({ uploading, progress, onUpload }) {
    const inputRef = useRef(null);
    const [dragActive, setDragActive] = useState(false);

    const handleFiles = (files) => {
        const file = files?.[0];
        if (file) onUpload(file);
    };

    return (
        <div
            className={`apt-dropzone ${dragActive ? 'drag-active' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => {
                event.preventDefault();
                setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(event) => {
                event.preventDefault();
                setDragActive(false);
                handleFiles(event.dataTransfer.files);
            }}
            role="button"
            tabIndex={0}
        >
            <input ref={inputRef} type="file" accept={ACCEPTED} hidden onChange={(event) => handleFiles(event.target.files)} />
            <FiUploadCloud />
            <h3>{uploading ? 'Uploading dataset...' : 'Drop a dataset here or click to upload'}</h3>
            <p>Accepted formats are PDF, CSV, XLSX, and JSON.</p>
            <div className="formats">
                {['PDF', 'CSV', 'XLSX', 'JSON'].map((format) => <span key={format}>{format}</span>)}
            </div>
            {uploading && (
                <div className="apt-upload-progress">
                    <div className="progress-bar"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
                    <span>{progress}%</span>
                </div>
            )}
        </div>
    );
}
