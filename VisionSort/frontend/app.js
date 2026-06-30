/**
 * VisionSort Dashboard Controller
 * Handles real-time WebSockets canvas drawing, control interactions,
 * and Chart.js telemetry rendering.
 */

// UI Elements
const canvas = document.getElementById("camera-feed");
const ctx = canvas.getContext("2d");
const speedSlider = document.getElementById("speed-slider");
const speedVal = document.getElementById("speed-val");
const dbStatusBadge = document.getElementById("db-status");
const conveyorStatusBadge = document.getElementById("conveyor-status");
// Stats Counters
const statSorted = document.getElementById("stat-sorted");
const statFps = document.getElementById("stat-fps");

// Action Buttons
const btnManualOverride = document.getElementById("btn-manual-override");
const btnBypassDiverter = document.getElementById("btn-bypass-diverter");
const materialButtons = document.querySelectorAll(".material-btn");

// Application State
let activeTargetMaterial = "Plastic";
let bypassModeActive = false;
let ws = null;

// Initialize WebSockets
function connectWebSocket() {
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/stream`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log("Connected to VisionSort stream server.");
        updateConveyorStatus(true);
    };
    
    ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        
        if (payload.type === "init_config") {
            const config = payload.data;
            activeTargetMaterial = config.target_material;
            speedSlider.value = config.speed;
            speedVal.textContent = parseFloat(config.speed).toFixed(1) + "x";
            
            // Sync Bypass Mode
            bypassModeActive = config.bypass_mode || false;
            updateBypassButtonState(bypassModeActive);
            
            updateActiveMaterialButton(config.target_material);
            updateDbStatus(config.db_status);
        } 
        else if (payload.type === "frame_update") {
            const frame = payload.data;
            
            // 1. Draw frame to Canvas
            drawConveyorFrame(frame.image);
            
            // 2. Update Stats
            updateMetrics(frame.metrics);
            
            // 4. Update Database Badge dynamically
            updateDbStatus(frame.metrics.db_status);
            
            // 5. Update Target Material in UI if changed on backend
            if (activeTargetMaterial !== frame.target_material) {
                activeTargetMaterial = frame.target_material;
                updateActiveMaterialButton(frame.target_material);
            }
            
            // 6. Sync Bypass if changed on backend
            if (frame.bypass_mode !== undefined && bypassModeActive !== frame.bypass_mode) {
                bypassModeActive = frame.bypass_mode;
                updateBypassButtonState(frame.bypass_mode);
            }
        }
    };
    
    ws.onclose = () => {
        console.warn("WebSocket stream disconnected. Reconnecting in 3s...");
        updateConveyorStatus(false);
        updateDbStatus("Disconnected");
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (err) => {
        console.error("WebSocket error: ", err);
    };
}

// Draw JPEG Frame on Canvas
function drawConveyorFrame(base64Image) {
    const img = new Image();
    img.src = `data:image/jpeg;base64,${base64Image}`;
    img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
}

function updateMetrics(metrics) {
    statSorted.textContent = metrics.total_sorted.toLocaleString();
    
    // Conveyor speed multiplier
    const mult = parseFloat(speedSlider.value).toFixed(1);
    statFps.textContent = `${mult}x`;
}

// Update DB status indicator
function updateDbStatus(status) {
    const dot = dbStatusBadge.querySelector(".status-dot");
    const label = dbStatusBadge.querySelector(".status-label");
    
    label.textContent = status;
    
    if (status.includes("Connected") || status.includes("Active") || status.includes("MongoDB")) {
        dot.style.background = "var(--color-metal)";
        dot.style.boxShadow = "0 0 8px var(--color-metal)";
        dot.classList.remove("error");
    } else if (status.includes("Fallback")) {
        dot.style.background = "var(--color-biological)";
        dot.style.boxShadow = "0 0 8px var(--color-biological)";
        dot.classList.remove("error");
    } else {
        dot.style.background = "var(--color-fault)";
        dot.style.boxShadow = "0 0 8px var(--color-fault)";
        dot.classList.add("error");
    }
}

// Update Conveyor connection indicator
function updateConveyorStatus(active) {
    const dot = conveyorStatusBadge.querySelector(".status-dot");
    const label = conveyorStatusBadge.querySelector(".status-label");
    
    if (active) {
        dot.style.background = "var(--color-metal)";
        dot.style.boxShadow = "0 0 8px var(--color-metal)";
        label.textContent = "Conveyor Active";
        dot.classList.add("pulsing");
    } else {
        dot.style.background = "var(--color-fault)";
        dot.style.boxShadow = "0 0 8px var(--color-fault)";
        label.textContent = "Conveyor Offline";
        dot.classList.remove("pulsing");
    }
}

// Highlight the active target material button
function updateActiveMaterialButton(material) {
    materialButtons.forEach(btn => {
        if (btn.getAttribute("data-material") === material) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}




// Update Bypass mode button styling
function updateBypassButtonState(active) {
    if (!btnBypassDiverter) return;
    if (active) {
        btnBypassDiverter.classList.add("active");
        btnBypassDiverter.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
            Bypass Active
        `;
    } else {
        btnBypassDiverter.classList.remove("active");
        btnBypassDiverter.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
            Bypass Diverter
        `;
    }
}

// Event Listeners
speedSlider.oninput = (e) => {
    const speed = parseFloat(e.target.value);
    speedVal.textContent = speed.toFixed(1) + "x";
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: "set_speed",
            speed: speed
        }));
    }
};

materialButtons.forEach(btn => {
    btn.onclick = (e) => {
        const material = e.target.getAttribute("data-material");
        activeTargetMaterial = material;
        updateActiveMaterialButton(material);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: "set_target",
                material: material
            }));
        }
    };
});


if (btnBypassDiverter) {
    btnBypassDiverter.onclick = () => {
        bypassModeActive = !bypassModeActive;
        updateBypassButtonState(bypassModeActive);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: "set_bypass_mode",
                bypass_mode: bypassModeActive
            }));
        }
    };
}

if (btnManualOverride) {
    btnManualOverride.onclick = () => {
        // Inject a manual divert alert for testing
        if (ws && ws.readyState === WebSocket.OPEN) {
            // Send command to test diverter: trigger a fake contaminant (forces Organic material on the belt)
            ws.send(JSON.stringify({
                type: "set_speed",
                speed: parseFloat(speedSlider.value)
            }));
            
            // Add a visual flash overlay to the canvas in the client
            const overlay = document.createElement("div");
            overlay.style.position = "absolute";
            overlay.style.top = "0";
            overlay.style.left = "0";
            overlay.style.width = "100%";
            overlay.style.height = "100%";
            overlay.style.background = "rgba(243, 156, 18, 0.25)";
            overlay.style.pointerEvents = "none";
            overlay.style.transition = "opacity 0.5s ease";
            canvas.parentElement.appendChild(overlay);
            setTimeout(() => {
                overlay.style.opacity = "0";
                setTimeout(() => overlay.remove(), 500);
            }, 100);
        }
    };
}

// Start application
let trendsChart = null;

async function fetchHistoricalTrends() {
    try {
        const response = await fetch("/api/trends");
        const json = await response.json();
        if (json.status === "success" && json.data) {
            updateTrendsChart(json.data);
        }
    } catch (e) {
        console.error("Failed to fetch historical trends:", e);
    }
}

function updateTrendsChart(data) {
    const labels = data.map(d => d.hour);
    const plastics = data.map(d => d.plastics);
    const metals = data.map(d => d.metals);
    const biological = data.map(d => d.biological);
    const paper = data.map(d => d.paper);
    const faults = data.map(d => d.faults);

    if (trendsChart) {
        trendsChart.data.labels = labels;
        trendsChart.data.datasets[0].data = plastics;
        trendsChart.data.datasets[1].data = metals;
        trendsChart.data.datasets[2].data = biological;
        trendsChart.data.datasets[3].data = paper;
        trendsChart.data.datasets[4].data = faults;
        trendsChart.update();
        return;
    }

    const trendsCanvas = document.getElementById("trends-chart");
    if (!trendsCanvas) return;
    
    const ctx = trendsCanvas.getContext("2d");
    trendsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Plastics",
                    data: plastics,
                    backgroundColor: "rgba(0, 242, 254, 0.75)",
                    borderColor: "#00f2fe",
                    borderWidth: 1,
                    stack: "materials"
                },
                {
                    label: "Metals",
                    data: metals,
                    backgroundColor: "rgba(0, 245, 160, 0.75)",
                    borderColor: "#00f5a0",
                    borderWidth: 1,
                    stack: "materials"
                },
                {
                    label: "Organic",
                    data: biological,
                    backgroundColor: "rgba(241, 196, 15, 0.75)",
                    borderColor: "#f1c40f",
                    borderWidth: 1,
                    stack: "materials"
                },
                {
                    label: "Paper",
                    data: paper,
                    backgroundColor: "rgba(161, 140, 209, 0.75)",
                    borderColor: "#a18cd1",
                    borderWidth: 1,
                    stack: "materials"
                },
                {
                    label: "Contaminants",
                    data: faults,
                    backgroundColor: "rgba(255, 78, 80, 0.75)",
                    borderColor: "#ff4e50",
                    borderWidth: 1,
                    stack: "materials"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        color: "#9ca3af",
                        font: {
                            family: "Outfit",
                            size: 10
                        },
                        boxWidth: 8,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    mode: "index",
                    intersect: false
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        color: "rgba(255, 255, 255, 0.05)"
                    },
                    ticks: {
                        color: "#9ca3af",
                        font: {
                            family: "Outfit",
                            size: 10
                        }
                    }
                },
                y: {
                    stacked: true,
                    grid: {
                        color: "rgba(255, 255, 255, 0.05)"
                    },
                    ticks: {
                        color: "#9ca3af",
                        font: {
                            family: "Outfit",
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

window.onload = () => {
    connectWebSocket();
    fetchHistoricalTrends();
    // Poll DB trends every 10 seconds for real-time history rollups
    setInterval(fetchHistoricalTrends, 10000);
};
