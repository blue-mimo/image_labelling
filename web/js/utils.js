export function logActivity(message, type = 'info') {
    const log = document.getElementById('activityLog');
    const timestamp = new Date().toLocaleTimeString();
    const color = type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#333';
    const entry = `<div style="color: ${color}; margin: 5px 0;"><strong>${timestamp}</strong> - ${message}</div>`;
    if (log.innerHTML === 'No activity yet') {
        log.innerHTML = entry;
    } else {
        log.innerHTML = entry + log.innerHTML;
    }
}

export function getConfidenceColor(confidence) {
    if (confidence < 50) {
        return 'rgb(139, 0, 0)';
    } else if (confidence <= 75) {
        const ratio = (confidence - 50) / 25;
        const red = Math.round(139 * (1 - ratio) + 255 * ratio);
        const green = Math.round(255 * ratio);
        return `rgb(${red}, ${green}, 0)`;
    } else {
        const ratio = (confidence - 75) / 25;
        const red = Math.round(255 * (1 - ratio));
        const green = Math.round(255 - 128 * ratio);
        return `rgb(${red}, ${green}, 0)`;
    }
}
