import { authToken } from './auth.js';
import { loadImages, currentPage } from './imageList.js';

let selectedSuggestionIndex = -1;
let currentSuggestions = [];

export function setupFilters() {
    const filterInput = document.getElementById('filterInput');
    filterInput.addEventListener('input', handleFilterInput);
    filterInput.addEventListener('keydown', handleFilterKeydown);
    document.getElementById('addFilterBtn').addEventListener('click', addFilter);

    document.addEventListener('click', (event) => {
        const dropdown = document.getElementById('autocompleteDropdown');
        if (dropdown && filterInput && !filterInput.contains(event.target) && !dropdown.contains(event.target)) {
            dropdown.style.display = 'none';
        }
    });
}

async function handleFilterInput(event) {
    const input = event.target.value.trim().toLowerCase();
    const dropdown = document.getElementById('autocompleteDropdown');

    if (input.length === 0) {
        dropdown.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`${window.API_BASE}/suggest_filters?prefix=${encodeURIComponent(input)}`, {
            headers: { 'Authorization': authToken }
        });
        const suggestions = await response.json();
        currentSuggestions = suggestions;
        selectedSuggestionIndex = -1;

        if (suggestions.length > 0) {
            dropdown.innerHTML = suggestions.map((suggestion, index) =>
                `<div class="autocomplete-item" data-index="${index}">${suggestion}</div>`
            ).join('');
            dropdown.querySelectorAll('.autocomplete-item').forEach(el => {
                el.addEventListener('click', () => selectSuggestion(el.textContent));
            });
            dropdown.style.display = 'block';
        } else {
            dropdown.style.display = 'none';
        }
    } catch (error) {
        console.error('Error fetching suggestions:', error);
        dropdown.style.display = 'none';
    }
}

function handleFilterKeydown(event) {
    const dropdown = document.getElementById('autocompleteDropdown');
    const items = dropdown.querySelectorAll('.autocomplete-item');

    if (event.key === 'ArrowDown') {
        event.preventDefault();
        selectedSuggestionIndex = Math.min(selectedSuggestionIndex + 1, items.length - 1);
        updateSelectedSuggestion(items);
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        selectedSuggestionIndex = Math.max(selectedSuggestionIndex - 1, -1);
        updateSelectedSuggestion(items);
    } else if (event.key === 'Enter') {
        event.preventDefault();
        if (selectedSuggestionIndex >= 0 && currentSuggestions[selectedSuggestionIndex]) {
            selectSuggestion(currentSuggestions[selectedSuggestionIndex]);
        } else {
            addFilter();
        }
    } else if (event.key === 'Escape') {
        dropdown.style.display = 'none';
    }
}

function updateSelectedSuggestion(items) {
    items.forEach((item, index) => {
        item.style.background = index === selectedSuggestionIndex ? '#f0f0f0' : 'white';
    });
}

function selectSuggestion(suggestion) {
    document.getElementById('filterInput').value = suggestion;
    document.getElementById('autocompleteDropdown').style.display = 'none';
    addFilter();
}

function addFilter() {
    const filterText = document.getElementById('filterInput').value.trim().toLowerCase();
    if (filterText && !window.activeFilters.includes(filterText)) {
        window.activeFilters.push(filterText);
        updateActiveFilters();
        window.currentPage = 0;
        loadImages();
        document.getElementById('filterInput').value = '';
    }
}

function updateActiveFilters() {
    const filtersElement = document.getElementById('activeFilters');
    if (window.activeFilters.length === 0) {
        filtersElement.innerHTML = 'No filters active';
    } else {
        filtersElement.innerHTML = window.activeFilters.map(filter =>
            `<span class="filter-tag">${filter}<span class="remove" data-filter="${filter}">&times;</span></span>`
        ).join('');
        filtersElement.querySelectorAll('.remove').forEach(el => {
            el.addEventListener('click', () => removeFilter(el.dataset.filter));
        });
    }
}

function removeFilter(filter) {
    window.activeFilters = window.activeFilters.filter(f => f !== filter);
    updateActiveFilters();
    window.currentPage = 0;
    loadImages();
}
