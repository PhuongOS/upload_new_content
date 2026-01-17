// CONSTANTS
const DEFAULT_DRIVE_ID = '12m-yTKxnR31oBlLLUuaXHTWK9txuMKtr';
const DEFAULT_SHEET_ID = '1yOCyBE60Ds0OwLU7hlu0a3mDHZn-tw8w235DZN3lTu0';

// UI Elements
const authBtn = document.getElementById('authorize_button');
const authStatus = document.getElementById('auth_status');
const configInputs = document.getElementById('configInputs');
const parentFolderInput = document.getElementById('parentFolderId');
const sheetIdInput = document.getElementById('sheetId');
const folderNameInput = document.getElementById('folderName');
const thumbnailInput = document.getElementById('thumbnailInput');
const fileInput = document.getElementById('fileInput');
const confirmBtn = document.getElementById('confirmBtn');
const progressList = document.getElementById('progressList');
const userEmailSpan = document.getElementById('userEmail');
const configDisplay = document.getElementById('configDisplay');
const statusMessage = document.getElementById('statusMessage');

window.onload = () => {
    // Load config
    parentFolderInput.value = localStorage.getItem('parentFolderId') || DEFAULT_DRIVE_ID;
    sheetIdInput.value = localStorage.getItem('sheetId') || DEFAULT_SHEET_ID;

    // Check Auth Status with Backend
    checkBackendAuth();
};

function toggleConfig() {
    configInputs.style.display = configInputs.style.display === 'none' ? 'block' : 'none';
}

function saveConfig() {
    localStorage.setItem('parentFolderId', parentFolderInput.value.trim());
    localStorage.setItem('sheetId', sheetIdInput.value.trim());
    alert('Configuration saved!');
    toggleConfig();
}

// File Input Logic
document.getElementById('selectThumbnail').onclick = () => thumbnailInput.click();
thumbnailInput.onchange = () => {
    document.getElementById('thumbnailCount').textContent = thumbnailInput.files.length > 0 ? thumbnailInput.files[0].name : "No file selected";
};

document.getElementById('selectFiles').onclick = () => fileInput.click();
fileInput.onchange = () => {
    document.getElementById('fileCount').textContent = fileInput.files.length > 0 ? `${fileInput.files.length} file(s) selected` : "No file selected";
};

document.getElementById('resetBtn').onclick = () => {
    folderNameInput.value = "";
    thumbnailInput.value = "";
    fileInput.value = "";
    document.getElementById('thumbnailCount').textContent = "No file selected";
    document.getElementById('fileCount').textContent = "No file selected";
    progressList.innerHTML = "";
    statusMessage.textContent = "";
};

// --- BACKEND INTEGRATION ---

async function checkBackendAuth() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();

        if (data.connected) {
            authStatus.className = "status-badge status-connected";
            authStatus.innerText = "Connected";
            userEmailSpan.textContent = data.email;

            authBtn.style.display = 'none';
            configDisplay.style.display = 'block';
        } else {
            authBtn.disabled = false;
            authStatus.innerText = "Ready to Connect";
        }
    } catch (e) {
        console.error("Backend offline?", e);
        authStatus.innerText = "Server Offline";
    }
}

// Login just redirects to backend route
authBtn.onclick = () => {
    window.location.href = '/api/auth/login';
};

// --- UPLOAD LOGIC ---

function addProgressItem(text) {
    const div = document.createElement('div');
    div.className = 'progress-item';
    div.textContent = text;
    progressList.appendChild(div);
    progressList.scrollTop = progressList.scrollHeight;
}

confirmBtn.onclick = async () => {
    const parentId = parentFolderInput.value.trim();
    const sheetId = sheetIdInput.value.trim();
    const folderName = folderNameInput.value.trim();

    if (!parentId || !sheetId) return alert("Please configure Parent Folder ID and Sheet ID!");
    if (!folderName) return alert("Please enter a Folder Name!");
    if (thumbnailInput.files.length === 0) return alert("Please select a Thumbnail!");

    confirmBtn.disabled = true;
    confirmBtn.textContent = "Processing...";
    progressList.innerHTML = "";
    statusMessage.textContent = "Uploading... Please wait.";

    // Build FormData
    const formData = new FormData();
    formData.append('parentId', parentId);
    formData.append('sheetId', sheetId);
    formData.append('folderName', folderName);
    formData.append('thumbnail', thumbnailInput.files[0]);

    for (let i = 0; i < fileInput.files.length; i++) {
        formData.append('files', fileInput.files[i]);
    }

    try {
        addProgressItem("Sending data to backend server...");

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            addProgressItem("✅ Process Completed Successfully!");
            statusMessage.textContent = "Success!";
            confirmBtn.className = "btn btn-success"; // Fixed class usage
            confirmBtn.textContent = "Success!";
            alert("Upload Completed Successfully!");
        } else {
            throw new Error(result.message || "Unknown error");
        }

    } catch (err) {
        console.error(err);
        addProgressItem(`❌ Error: ${err.message}`);
        statusMessage.textContent = "Error";
        confirmBtn.className = "btn btn-error";
        alert(`Process Failed: ${err.message}`);
    } finally {
        setTimeout(() => {
            confirmBtn.disabled = false;
            confirmBtn.textContent = "Confirm & Upload";
            confirmBtn.className = "btn btn-confirm";
        }, 3000);
    }
};
