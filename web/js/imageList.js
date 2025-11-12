import { authToken } from './auth.js';
import { selectImage, deleteImage } from './imageDisplay.js';
import { logActivity } from './utils.js';

export let currentPage = 0;
export let totalPages = 0;
export let totalImages = 0;
export let images = [];
let resizeObserver = null;

export function calculateImagesPerPage() {
    const container = document.getElementById('imageListContainer');
    const header = document.querySelector('.image-list-header');
    if (!container || !header) return 1;

    const containerStyle = window.getComputedStyle(container);
    const padding = parseFloat(containerStyle.paddingTop) + parseFloat(containerStyle.paddingBottom);
    const headerMargin = parseFloat(window.getComputedStyle(header).marginBottom);
    const availableHeight = container.clientHeight - header.offsetHeight - padding - headerMargin;

    const itemHeight = 44;
    const calculatedItems = Math.floor(availableHeight / itemHeight);
    return Math.max(1, calculatedItems);
}

export function setupResizeObserver() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    if (resizeObserver) resizeObserver.disconnect();

    let rafId;
    resizeObserver = new ResizeObserver(() => {
        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
            const newImagesPerPage = calculateImagesPerPage();
            if (newImagesPerPage !== window.imagesPerPage) {
                window.imagesPerPage = newImagesPerPage;
                currentPage = 0;
                loadImages();
            }
        });
    });

    resizeObserver.observe(sidebar);
}

export async function loadImages() {
    document.getElementById('imageList').innerHTML = 'Loading...';
    try {
        const filtersParam = window.activeFilters?.length > 0 ? `&filters=${encodeURIComponent(window.activeFilters.join(','))}` : '';
        const response = await fetch(`${window.API_BASE}/images?page=${currentPage}&limit=${window.imagesPerPage}${filtersParam}`, {
            headers: { 'Authorization': authToken }
        });
        const data = await response.json();
        images = data.images;
        totalPages = data.pagination.totalPages;
        totalImages = data.pagination.total;
        displayImageList();
        updatePagination();
    } catch (error) {
        let message = 'Unable to load images. ';
        if (error.message.includes('401') || error.message.includes('403')) {
            message += 'Session expired.';
        } else if (error.message.includes('NetworkError') || !navigator.onLine) {
            message += 'Network connection issue.';
        } else {
            message += 'Server error.';
        }
        document.getElementById('imageList').innerHTML = message;
        logActivity(message, 'error');
    }
}

function displayImageList() {
    const listElement = document.getElementById('imageList');
    listElement.innerHTML = images.map(image =>
        `<div class="image-item" data-image="${image}">
            <span class="image-name">${image}</span>
            <button class="delete-btn" data-image="${image}" title="Delete image">&times;</button>
        </div>`
    ).join('');

    listElement.querySelectorAll('.image-name').forEach(el => {
        el.addEventListener('click', () => selectImage(el.parentElement.dataset.image));
    });
    listElement.querySelectorAll('.delete-btn').forEach(el => {
        el.addEventListener('click', () => deleteImage(el.dataset.image));
    });

    const startIndex = currentPage * window.imagesPerPage + 1;
    const endIndex = Math.min(startIndex + images.length - 1, totalImages);
    document.getElementById('imageListHeader').textContent = `Images (${startIndex}-${endIndex} of ${totalImages})`;

    if (window.selectedImageName) {
        if (images.includes(window.selectedImageName)) {
            document.querySelector(`.image-item[data-image="${window.selectedImageName}"]`)?.classList.add('selected');
        } else {
            window.selectedImageName = null;
            if (window.currentImageUrl) {
                URL.revokeObjectURL(window.currentImageUrl);
                window.currentImageUrl = null;
            }
            document.getElementById('imageDisplay').innerHTML = 'Select an image';
            document.getElementById('labelsDisplay').innerHTML = 'Select an image to view labels';
        }
    }
}

function updatePagination() {
    const paginationElement = document.getElementById('paginationControls');

    if (totalPages <= 1) {
        paginationElement.innerHTML = '';
        return;
    }

    const firstDisabled = currentPage === 0 ? 'disabled' : '';
    const lastDisabled = currentPage === totalPages - 1 ? 'disabled' : '';
    const prevDisabled = currentPage < 3 ? 'disabled' : '';
    const nextDisabled = currentPage >= totalPages - 3 ? 'disabled' : '';

    let controls = `
        <button ${firstDisabled} data-page="0">|&laquo;</button>
        <button ${prevDisabled} data-page="${Math.max(0, currentPage - 3)}">&laquo;</button>
    `;

    let startPage = Math.max(0, Math.min(currentPage - 1, totalPages - 3));
    let endPage = Math.min(totalPages, startPage + 3);

    for (let i = startPage; i < endPage; i++) {
        controls += `<button class="${i === currentPage ? 'active' : ''}" data-page="${i}">${i + 1}</button>`;
    }

    controls += `
        <button ${nextDisabled} data-page="${Math.min(totalPages - 1, currentPage + 3)}">&raquo;</button>
        <button ${lastDisabled} data-page="${totalPages - 1}">&raquo;|</button>
    `;

    paginationElement.innerHTML = controls;
    paginationElement.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => changePage(parseInt(btn.dataset.page)));
    });
}

function changePage(page) {
    currentPage = page;
    loadImages();
}

export function setupImageList() {
    document.getElementById('refreshBtn').addEventListener('click', loadImages);
}
