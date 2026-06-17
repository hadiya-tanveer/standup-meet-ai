const statusText = document.getElementById('status-text');
const pulseBar = document.getElementById('bars'); // changed to #bars

async function fetchStatus() {
    try {
        const response = await fetch('/status');
        if (response.ok) {
            const data = await response.json();
            statusText.textContent = data.status;

            if (data.status.toLowerCase() === "agent is speaking.") {
                pulseBar.classList.remove('idle');
                pulseBar.classList.add('speaking');
            } else {
                pulseBar.classList.remove('speaking');
                pulseBar.classList.add('idle');
            }
        } else {
            statusText.textContent = "Error fetching status";
        }
    } catch (error) {
        statusText.textContent = "Connection error";
    }
}

setInterval(fetchStatus, 2000);
fetchStatus();
