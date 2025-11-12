import { authToken } from './auth.js';
import { loadImages } from './imageList.js';
import { logActivity, getConfidenceColor } from './utils.js';

export async function selectImage(imageName) {
    if (window.currentImageUrl) {
        URL.revokeObjectURL(window.currentImageUrl);
        window.currentImageUrl = null;
    }

    window.selectedImageName = imageName;
    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.image === imageName);
    });

    document.getElementById('imageDisplay').innerHTML = '<div class="spinner"></div>';
    document.getElementById('labelsDisplay').innerHTML = '<div class="spinner"></div>';

    try {
        await Promise.all([
            getAndDisplayLabels(imageName),
            getAndDisplayImage(imageName)
        ]);
    } catch (error) {
        console.error('Error displaying image or labels:', error);
    }
}

async function getAndDisplayLabels(imageName) {
    try {
        const response = await fetch(`${window.API_BASE}/labels/${imageName}`, {
            headers: { 'Authorization': authToken }
        });
        const data = await response.json();

        if (data.labels && data.labels.length > 0) {
            const tableHTML = `
                <table class="labels-table">
                    <thead><tr><th>Label</th><th>Confidence</th></tr></thead>
                    <tbody>
                        ${data.labels.map(label => `
                            <tr>
                                <td>${label.name}</td>
                                <td style="background-color: ${getConfidenceColor(label.confidence)}">${label.confidence.toFixed(1)}%</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            document.getElementById('labelsDisplay').innerHTML = tableHTML;
        } else {
            document.getElementById('labelsDisplay').innerHTML = 'No labels found';
        }
    } catch (error) {
        let message = 'Unable to load labels. ';
        if (error.message.includes('404')) {
            message = 'No labels available for this image.';
        } else if (error.message.includes('401')) {
            message += 'Please log in again.';
        } else {
            message += 'Please try again.';
        }
        document.getElementById('labelsDisplay').innerHTML = message;
    }
}

async function getAndDisplayImage(imageName) {
    try {
        const displayElement = document.getElementById('imageDisplay');
        const rect = displayElement.getBoundingClientRect();
        const maxWidth = Math.floor(rect.width);
        const maxHeight = Math.floor(rect.height);

        const response = await fetch(`${window.API_BASE}/image/${imageName}?maxwidth=${maxWidth}&maxheight=${maxHeight}`, {
            headers: {
                'Accept': 'image/jpeg,image/png,image/gif',
                'Authorization': authToken
            }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const blob = await response.blob();
        if (blob.size === 0) throw new Error('Empty blob received');
        if (!blob.type.startsWith('image/')) throw new Error('Unexpected blob type:', blob.type);

        const imageUrl = URL.createObjectURL(blob);
        const img = document.createElement('img');
        img.className = 'image-display';
        window.currentImageUrl = imageUrl;

        img.onerror = () => {
            document.getElementById('imageDisplay').innerHTML = '<p>Failed to display image</p>';
            URL.revokeObjectURL(imageUrl);
        };

        document.getElementById('imageDisplay').innerHTML = '';
        document.getElementById('imageDisplay').appendChild(img);
        img.src = imageUrl;
    } catch (error) {
        let message = 'Unable to display image. ';
        if (error.message.includes('404')) {
            message += 'Image not found.';
        } else if (error.message.includes('401')) {
            message += 'Please log in again.';
        } else {
            message += 'Please try again.';
        }
        document.getElementById('imageDisplay').innerHTML = `<p>${message}</p>`;
    }
}

export async function deleteImage(imageName) {
    if (!confirm(`Are you sure you want to delete "${imageName}"?\n\nThis action cannot be undone.`)) return;

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = '<div class="modal-content"><div class="spinner"></div><div style="margin-top: 15px;">Deleting image...</div></div>';
    document.body.appendChild(modal);

    try {
        const response = await fetch(`${window.API_BASE}/image/${imageName}`, {
            method: 'DELETE',
            headers: { 'Authorization': authToken }
        });

        if (response.ok) {
            if (window.selectedImageName === imageName) {
                window.selectedImageName = null;
                if (window.currentImageUrl) {
                    URL.revokeObjectURL(window.currentImageUrl);
                    window.currentImageUrl = null;
                }
                document.getElementById('imageDisplay').innerHTML = 'Select an image';
                document.getElementById('labelsDisplay').innerHTML = 'Select an image to view labels';
            }
            logActivity(`Deleted image: ${imageName}`, 'success');
            loadImages();
        } else {
            logActivity(`Failed to delete image: ${imageName}`, 'error');
        }
    } catch (error) {
        logActivity(`Error deleting image: ${imageName}`, 'error');
    } finally {
        document.body.removeChild(modal);
    }
}
