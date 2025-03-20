// Initialize tracking logs
const trackingLogs = [];
let isTrackingPaused = false;

// Function to update the log display without losing expanded state
function updateLogDisplay() {
    const logContainer = document.getElementById('tracking-log');
    if (!logContainer) return;
    
    // Store the expanded state of existing log entries
    const expandedStates = new Map();
    document.querySelectorAll('.log-entry').forEach((entry, index) => {
        const expanded = {};
        entry.querySelectorAll('.caret-icon').forEach((caret, i) => {
            expanded[i] = caret.classList.contains('expanded');
        });
        expandedStates.set(index, expanded);
    });
    
    // Clear existing logs
    logContainer.innerHTML = '';
    
    if (trackingLogs.length === 0) {
        logContainer.innerHTML = '<p>Waiting for tracking events...</p>';
        return;
    }
    
    // Add new logs in reverse order (newest first)
    trackingLogs.slice().reverse().forEach((log, index) => {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        const logHeader = document.createElement('div');
        logHeader.className = 'log-header';
        
        const logType = document.createElement('span');
        logType.className = 'log-type';
        logType.textContent = log.type || 'Event';
        
        const logTime = document.createElement('span');
        logTime.className = 'log-time';
        logTime.textContent = log.timestamp.toLocaleTimeString();
        
        logHeader.appendChild(logType);
        logHeader.appendChild(logTime);
        
        const logDataContainer = document.createElement('div');
        logDataContainer.className = 'log-data';
        
        // Use JSONViewer with configurable expanded state
        const jsonViewer = new JSONViewer({
            expanded: false // Start collapsed by default
        });
        logDataContainer.appendChild(jsonViewer.getContainer());
        jsonViewer.showJSON(log.data);
        
        logEntry.appendChild(logHeader);
        logEntry.appendChild(logDataContainer);
        
        logContainer.appendChild(logEntry);
        
        // Restore expanded state for existing entries
        if (expandedStates.has(index)) {
            const expandedState = expandedStates.get(index);
            const carets = logEntry.querySelectorAll('.caret-icon');
            
            carets.forEach((caret, i) => {
                if (expandedState[i]) {
                    // Trigger click to expand
                    caret.click();
                }
            });
        } else if (index === 0) {
            // For new entries (first item), auto-expand first level
            const firstCaret = logEntry.querySelector('.caret-icon');
            if (firstCaret) {
                firstCaret.click();
            }
        }
    });
}

// Function to clear logs
function clearLogs() {
    trackingLogs.length = 0;
    updateLogDisplay();
}

// Function to toggle event tracking
function toggleTracking() {
    isTrackingPaused = !isTrackingPaused;
    
    // Update button text
    const toggleBtn = document.getElementById('toggle-tracking-btn');
    if (toggleBtn) {
        toggleBtn.textContent = isTrackingPaused ? 'Resume Tracking' : 'Pause Tracking';
        toggleBtn.classList.toggle('paused', isTrackingPaused);
    }
}

// Callback function for successful Snowplow requests
function requestCallback(payload) {
    // Skip if tracking is paused
    if (isTrackingPaused) return;
    
    try {
        let data = payload;
        let type = 'POST Request';
        
        // For GET requests
        if (typeof payload === 'string' && payload.startsWith('?')) {
            type = 'GET Request';
            const params = new URLSearchParams(payload);
            data = {};
            for (const [key, value] of params.entries()) {
                data[key] = value;
            }
        }
        
        trackingLogs.push({
            type: type,
            timestamp: new Date(),
            data: data
        });
        
        updateLogDisplay();
    } catch (e) {
        console.error('Error logging Snowplow request:', e);
    }
}

// Initialize UI event handlers
function initUI() {
    // Initialize button event handlers
    document.getElementById('clear-log-btn').addEventListener('click', clearLogs);
    document.getElementById('track-event-btn').addEventListener('click', function() {
        if (!isTrackingPaused) {
            window.snowplow('trackStructEvent', 'User Actions', 'Button Click', 'Track Event Button', null, null);
        }
    });
    
    document.getElementById('toggle-tracking-btn').addEventListener('click', toggleTracking);
} 