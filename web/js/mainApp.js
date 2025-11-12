import { logout } from './auth.js';
import { setupImageList, calculateImagesPerPage, setupResizeObserver } from './imageList.js';
import { setupFilters } from './filters.js';
import { setupUpload } from './upload.js';

export function showApp() {
    document.getElementById('app').innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">Image Labeler</h1>
            <button id="logoutBtn" style="padding: 10px 20px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border: none; border-radius: 8px; cursor: pointer; transition: transform 0.2s; box-shadow: 0 4px 12px rgba(245,87,108,0.3);">Logout</button>
        </div>
        <div class="container">
            <div class="sidebar">
                <div class="filter-search" style="position: relative;">
                    <h4>Filter Search Box</h4>
                    <input type="text" id="filterInput" placeholder="Search labels...">
                    <div id="autocompleteDropdown" class="autocomplete-dropdown" style="display: none;"></div>
                    <button id="addFilterBtn" style="margin-top: 5px; padding: 5px 10px;">Add Filter</button>
                </div>
                <div class="active-filters">
                    <h4>Active Filters</h4>
                    <div id="activeFilters">No filters active</div>
                </div>
                <div class="image-list">
                    <div class="image-list-header">
                        <h4 id="imageListHeader">Images</h4>
                        <button class="refresh-btn" id="refreshBtn" title="Refresh image list">&#8635;</button>
                    </div>
                    <div class="image-list-content" id="imageListContainer">
                        <div class="image-list-scroll">
                            <div id="imageList">Loading...</div>
                        </div>
                    </div>
                </div>
                <div class="pagination">
                    <div id="paginationControls"></div>
                </div>
            </div>
            <div class="main-content">
                <div class="selected-image">
                    <div id="imageDisplay">Select an image</div>
                </div>
                <div class="labels-table-container" id="labelsDisplay">Select an image to view labels</div>
                <div class="upload-area" id="uploadArea">
                    <div id="uploadContent">
                        <svg class="upload-icon" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                            <rect x="20" y="35" width="60" height="50" rx="5" fill="none" stroke="#667eea" stroke-width="3"/>
                            <path d="M 50 15 L 50 60" stroke="#667eea" stroke-width="3" stroke-linecap="round"/>
                            <path d="M 35 30 L 50 15 L 65 30" fill="none" stroke="#667eea" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                            <circle cx="35" cy="55" r="8" fill="#667eea" opacity="0.3"/>
                            <path d="M 30 70 L 40 60 L 50 65 L 65 50 L 75 60 L 75 75 L 25 75 Z" fill="#667eea" opacity="0.3"/>
                        </svg>
                        <div>Click or drag files to upload</div>
                    </div>
                    <input type="file" id="fileInput" multiple accept=".jpg,.jpeg,.png,.gif" style="display: none;">
                </div>
                <div class="upload-report-area">
                    <h4>Activity Log</h4>
                    <div id="activityLog" class="upload-report">No activity yet</div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('logoutBtn').addEventListener('click', logout);
    setupImageList();
    setupFilters();
    setupUpload();

    requestAnimationFrame(() => {
        window.imagesPerPage = calculateImagesPerPage();
        setupResizeObserver();
    });
}
