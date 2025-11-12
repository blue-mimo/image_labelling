import { authToken } from './auth.js';
import { loadImages } from './imageList.js';
import { logActivity } from './utils.js';

export function setupUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    fileInput.addEventListener('change', handleFileUpload);
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('uploadArea').style.borderColor = '#007cba';
    document.getElementById('uploadArea').style.backgroundColor = '#f0f8ff';
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('uploadArea').style.borderColor = '#ddd';
    document.getElementById('uploadArea').style.backgroundColor = '#f9f9f9';
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('uploadArea').style.borderColor = '#ddd';
    document.getElementById('uploadArea').style.backgroundColor = '#f9f9f9';

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        document.getElementById('fileInput').files = files;
        handleFileUpload();
    }
}

async function handleFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const files = Array.from(fileInput.files);
    if (files.length === 0) return;

    const uploadContent = document.getElementById('uploadContent');
    const uploadArea = document.getElementById('uploadArea');

    uploadArea.onclick = null;
    uploadContent.innerHTML = '<div class="spinner"></div><div style="margin-top: 10px;">Uploading...</div>';

    let successful = 0;
    let failed = 0;

    for (const file of files) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${window.API_BASE}/upload_image`, {
                method: 'POST',
                headers: { 'Authorization': authToken },
                body: formData
            });

            if (response.ok) {
                successful++;
            } else {
                failed++;
                if (response.status === 413) {
                    logActivity(`Upload of ${file.name} failed due to file being too large`, 'error');
                } else if (response.status === 401 || response.status === 403) {
                    logActivity(`Upload of ${file.name} failed due to authentication error`, 'error');
                } else {
                    logActivity(`Upload of ${file.name} failed due to server error`, 'error');
                }
            }
        } catch (error) {
            failed++;
            if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                logActivity(`Upload of ${file.name} failed due to network error`, 'error');
            } else {
                logActivity(`Upload of ${file.name} failed due to unexpected error`, 'error');
            }
        }
    }

    if (failed > 0) {
        logActivity(`Failed to upload ${failed} image${failed > 1 ? 's' : ''}`, 'error');
    }
    if (successful > 0) {
        logActivity(`Uploaded ${successful} image${successful > 1 ? 's' : ''}`, 'success');
        loadImages();
    }

    fileInput.value = '';
    setupUpload();
    uploadContent.innerHTML = `
        <svg class="upload-icon" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect x="20" y="35" width="60" height="50" rx="5" fill="none" stroke="#667eea" stroke-width="3"/>
            <path d="M 50 15 L 50 60" stroke="#667eea" stroke-width="3" stroke-linecap="round"/>
            <path d="M 35 30 L 50 15 L 65 30" fill="none" stroke="#667eea" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="35" cy="55" r="8" fill="#667eea" opacity="0.3"/>
            <path d="M 30 70 L 40 60 L 50 65 L 65 50 L 75 60 L 75 75 L 25 75 Z" fill="#667eea" opacity="0.3"/>
        </svg>
        <div>Click or drag files to upload</div>
    `;
}
