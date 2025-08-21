let currentState = 'stopped';
let networkInfoLoaded = false;

async function loadNetworkInfo() {
    if (networkInfoLoaded) return;

    try {
        const response = await fetch('/network-info');
        const networkInfo = await response.json();

        // Calculate base URL
        const baseUrl = `http://${networkInfo.private_ip}:${networkInfo.port}`;

        // Update network info display
        document.getElementById('privateIp').textContent = networkInfo.private_ip;
        document.getElementById('hostname').textContent = networkInfo.hostname;
        document.getElementById('port').textContent = networkInfo.port;
        document.getElementById('baseUrl').textContent = baseUrl;

        // Update API URLs
        document.getElementById('eventUrl').textContent = `${baseUrl}/event`;
        document.getElementById('healthUrl').textContent = `${baseUrl}/health`;
        document.getElementById('statsUrl').textContent = `${baseUrl}/stats`;

        networkInfoLoaded = true;

    } catch (error) {
        console.error('Error fetching network info:', error);
        showMessage('Error fetching network info', 'error');
    }
}


async function refreshStats() {
    try {
        const response = await fetch('/stats');
        const data = await response.json();

        // Update counts
        document.getElementById('redCount').textContent = data.red_count;
        document.getElementById('blueCount').textContent = data.blue_count;
        document.getElementById('totalCount').textContent = data.total_count;

        // Update system state
        currentState = data.system_state;
        updateSystemStatus(data.system_state);
        updateButtonStates();
        // Update registered sources
        updateRegisteredSources(data.registered_data || {});

        // Update response time
        await updateResponseTimeDisplay();
        //document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function updateResponseTimeDisplay() {
    try {
        const response = await fetch('/config/response-time');
        const data = await response.json();

        document.getElementById('currentResponseTime').textContent = `${data.response_time_ms}ms`;
        document.getElementById('responseTimeInput').value = data.response_time_ms;
    } catch (error) {
        console.error('Error fetching response time:', error);
    }
}

async function updateResponseTime() {
    const input = document.getElementById('responseTimeInput');
    const newResponseTime = parseInt(input.value);

    if (newResponseTime < 100) {
        showMessage('Response time must be at least 100ms', 'error');
        return;
    }

    try {
        const response = await fetch('/config/response-time', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                response_time_ms: newResponseTime
            })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage(data.message, 'success');
            await updateResponseTimeDisplay();
        } else {
            showMessage(data.detail || 'Failed to update response time', 'error');
        }

    } catch (error) {
        console.error('Error updating response time:', error);
        showMessage('Error updating response time', 'error');
    }
}

function updateRegisteredSources(registeredSources) {
    // Update Red sources
    console.log("update registered sources")
    console.log(registeredSources)
    const redSourcesDiv = document.getElementById('redSources');
    const redSources = registeredSources.RED || [];

    if (redSources.length === 0) {
        redSourcesDiv.innerHTML = '<div class="no-sources">No registered sources</div>';
    } else {
        redSourcesDiv.innerHTML = redSources.map(ip =>
            `<div class="source-item red">📱 ${ip}</div>`
        ).join('');
    }

    // Update Blue sources
    const blueSourcesDiv = document.getElementById('blueSources');
    const blueSources = registeredSources.BLUE || [];

    if (blueSources.length === 0) {
        blueSourcesDiv.innerHTML = '<div class="no-sources">No registered sources</div>';
    } else {
        blueSourcesDiv.innerHTML = blueSources.map(ip =>
            `<div class="source-item blue">📱 ${ip}</div>`
        ).join('');
    }
}

// Auto-refresh stats every 5 seconds
setInterval(refreshStats, 5000);

// Initial load
loadNetworkInfo();  // Load network info once
refreshStats();     // Load stats

function updateSystemStatus(state) {
    const statusElement = document.getElementById('systemStatus');
    const indicatorElement = document.getElementById('statusIndicator');

    if (state === 'started') {
        statusElement.textContent = 'System Started - Counting Events';
        indicatorElement.className = 'status-indicator status-started';
    } else {
        statusElement.textContent = 'System Stopped - Not Counting Events';
        indicatorElement.className = 'status-indicator status-stopped';
    }
}

function updateButtonStates() {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const resetBtn = document.getElementById('resetBtn');

    if (currentState === 'started') {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        resetBtn.disabled = true;
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        resetBtn.disabled = false;
    }
}

async function controlSystem(action) {
    try {
        const response = await fetch(`/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (response.ok) {
            currentState = data.system_state;
            updateSystemStatus(data.system_state);
            updateButtonStates();
            showMessage(data.message, 'success');

            // Refresh stats after successful action
            setTimeout(refreshStats, 500);
        } else {
            showMessage(data.detail || 'Operation failed', 'error');
        }

    } catch (error) {
        console.error(`Error ${action}:`, error);
        showMessage(`Error performing ${action}`, 'error');
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('messageDiv');
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';

    // Hide message after 3 seconds
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 3000);
}

// Auto-refresh every 5 seconds
setInterval(refreshStats, 500);

// Initial load
refreshStats();
