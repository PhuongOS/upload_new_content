// CONSTANTS
const DEFAULT_DRIVE_ID = '12m-yTKxnR31oBlLLUuaXHTWK9txuMKtr';
const DEFAULT_SHEET_ID = '1yOCyBE60Ds0OwLU7hlu0a3mDHZn-tw8w235DZN3lTu0';

// UI Elements
const authBtn = document.getElementById('authorize_button');
const authMiniStatus = document.getElementById('auth_mini_status');
const parentFolderInput = document.getElementById('parentFolderId');
const sheetIdInput = document.getElementById('sheetId');
const folderNameInput = document.getElementById('folderName');
const thumbnailInput = document.getElementById('thumbnailInput');
const fileInput = document.getElementById('fileInput');
const confirmBtn = document.getElementById('confirmBtn');
const progressList = document.getElementById('progressList');
const userEmailSpan = document.getElementById('userEmail');
const statusMessage = document.getElementById('statusMessage');
const viewTitle = document.getElementById('view-title');

// Edit state for configurations
let editingConfigIndex = null;
let currentConfigSheet = null;

// State for Media Calendar updates
let currentCalendarData = [];
let activeScheduleTarget = { index: null, platform: null };
let facebookConfigs = [];
let youtubeConfigs = [];

// Sidebar Navigation Logic
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        const target = item.getAttribute('data-target');

        // Update active nav item
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

        // Update visible view
        views.forEach(view => view.classList.remove('visible'));
        document.getElementById(target).classList.add('visible');

        // Update header title
        viewTitle.innerText = item.querySelector('span').innerText;

        // Auto-load data for specific views
        if (target === 'facebook-view') loadSheetData('Facebook_db');
        if (target === 'youtube-view') loadSheetData('Youtube_db');
        if (target === 'calendar-view') loadSheetData('Media_Calendar');
    });
});

window.onload = () => {
    // Load config
    parentFolderInput.value = localStorage.getItem('parentFolderId') || DEFAULT_DRIVE_ID;
    sheetIdInput.value = localStorage.getItem('sheetId') || DEFAULT_SHEET_ID;

    // Check Auth Status with Backend
    checkBackendAuth();
    // Load configs for dropdowns
    loadConfigs();
    // Start tracking existing tasks if any
    pollTasks();

    // Auto-parse URL in Sheet ID field
    sheetIdInput.oninput = (e) => {
        const val = e.target.value.trim();
        if (val.includes('/spreadsheets/d/')) {
            const { sheetId, tabId } = parseSheetUrl(val);
            if (sheetId) {
                e.target.value = sheetId;
                localStorage.setItem('sheetId', sheetId);
                console.log(`Auto-detected Sheet ID: ${sheetId}, Tab ID: ${tabId}`);
                statusMessage.innerText = `Auto-parsed ID from URL (Tab ID: ${tabId})`;
                statusMessage.className = 'status-message success';
            }
        } else {
            localStorage.setItem('sheetId', val);
        }
    };
};

function parseSheetUrl(url) {
    const sheetIdMatch = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/);
    const gidMatch = url.match(/[#&]gid=([0-9]+)/);
    return {
        sheetId: sheetIdMatch ? sheetIdMatch[1] : null,
        tabId: gidMatch ? gidMatch[1] : "0"
    };
}

async function pollTasks() {
    setInterval(async () => {
        try {
            const res = await fetch('/api/tasks');
            const tasks = await res.json();
            const currentTaskId = localStorage.getItem('lastTaskId');
            if (currentTaskId && tasks[currentTaskId]) {
                const task = tasks[currentTaskId];
                if (task.status === 'processing') {
                    addProgressItem(`[BG] ${task.progress}`);
                } else if (task.status === 'success') {
                    addProgressItem(`✅ [BG] ${task.message}`);
                    localStorage.removeItem('lastTaskId');
                } else if (task.status === 'error') {
                    addProgressItem(`❌ [BG] Error: ${task.message}`);
                    localStorage.removeItem('lastTaskId');
                }
            }
        } catch (e) { }
    }, 5000);
}

async function loadConfigs() {
    try {
        const [fbRes, ytRes] = await Promise.all([
            fetch('/api/v2/sheets/Facebook_Config'),
            fetch('/api/v2/sheets/Youtube_Config')
        ]);
        if (fbRes.ok) facebookConfigs = await fbRes.json();
        if (ytRes.ok) youtubeConfigs = await ytRes.json();
        console.log("Configs loaded:", { facebook: facebookConfigs.length, youtube: youtubeConfigs.length });
    } catch (err) {
        console.error("Error loading configs:", err);
    }
}

function saveConfig() {
    localStorage.setItem('parentFolderId', parentFolderInput.value.trim());
    localStorage.setItem('sheetId', sheetIdInput.value.trim());
    alert('Cấu hình đã được lưu!');
}

// File Input Logic
document.getElementById('selectThumbnail').onclick = () => thumbnailInput.click();
thumbnailInput.onchange = () => {
    document.getElementById('thumbnailCount').textContent = thumbnailInput.files.length > 0 ? thumbnailInput.files[0].name : "Chọn hoặc kéo ảnh vào";
};

document.getElementById('selectFiles').onclick = () => fileInput.click();
fileInput.onchange = () => {
    document.getElementById('fileCount').textContent = fileInput.files.length > 0 ? `${fileInput.files.length} tệp đã chọn` : "Chọn hoặc kéo file vào";
};

document.getElementById('resetBtn').onclick = () => {
    folderNameInput.value = "";
    thumbnailInput.value = "";
    fileInput.value = "";
    document.getElementById('thumbnailCount').textContent = "Chọn hoặc kéo ảnh vào";
    document.getElementById('fileCount').textContent = "Chọn hoặc kéo file vào";
    progressList.innerHTML = "";
    statusMessage.textContent = "";
};

async function checkBackendAuth() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();

        if (data.connected) {
            authMiniStatus.className = "auth-status-dot connected";
            userEmailSpan.textContent = data.email;
            authBtn.style.display = 'none';
        } else {
            authMiniStatus.className = "auth-status-dot disconnected";
            authBtn.style.display = 'flex';
            authBtn.disabled = false;
        }
    } catch (e) {
        console.error("Backend offline?", e);
        authMiniStatus.className = "auth-status-dot disconnected";
    }
}

// SHEET DATA HANDLING
async function loadSheetData(sheetName) {
    const containerId = {
        'Facebook_db': 'facebook-cards-container',
        'Youtube_db': 'youtube-cards-container',
        'Media_Calendar': 'calendar-groups-container'
    }[sheetName];

    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        const res = await fetch(`/api/v2/sheets/${sheetName}`);
        const data = await res.json();

        if (sheetName === 'Media_Calendar') {
            currentCalendarData = data; // Store globally for updates
            renderCalendar(container, data);
        } else {
            renderCards(container, data, sheetName);
        }
    } catch (err) {
        container.innerHTML = `<div class="status-message error">Lỗi tải dữ liệu: ${err.message}</div>`;
    }
}

function renderCards(container, data, sheetName) {
    if (!data || data.length === 0) {
        container.innerHTML = '<p class="empty-state">Không có dữ liệu.</p>';
        return;
    }

    const platform = sheetName === 'Facebook_db' ? 'facebook' : 'youtube';

    container.innerHTML = data.map((item, index) => {
        const configs = platform === 'facebook' ? facebookConfigs : youtubeConfigs;
        const currentVal = platform === 'facebook' ? (item.page?.id || "") : (item.channel?.id || "");

        const dropdownHtml = `
            <select class="card-select" onchange="updateCardField('${sheetName}', ${index}, { platform: '${platform}', id: this.value, name: this.options[this.selectedIndex].text, gmail: this.options[this.selectedIndex].getAttribute('data-gmail') || '' })">
                <option value="">-- Chọn ${platform === 'facebook' ? 'Page' : 'Kênh'} --</option>
                ${configs.map(c => {
            const id = platform === 'facebook' ? c.page_id : c.channel_id;
            const name = platform === 'facebook' ? c.page_name : c.channel_name;
            const gmail = platform === 'youtube' ? (c.gmail_channel || '') : '';
            return `<option title="${id}" value="${id}" data-gmail="${gmail}" ${id === currentVal ? 'selected' : ''}>${name}</option>`;
        }).join('')}
            </select>
        `;

        return `
            <div class="content-card">
                <div class="card-header">
                    <div class="card-title" title="${item.video_name || item.Name_video || 'No Name'}">
                        ${item.video_name || item.Name_video || 'No Title'}
                    </div>
                    <div class="card-id">#${item.stt || item.STT || (index + 1)}</div>
                </div>
                
                <div class="card-body">
                    <div class="card-info-item">
                        <i class="fas fa-folder-open"></i>
                        <span>ID Drive: ${item.media_drive_id || item.Id_media_on_drive || 'N/A'}</span>
                    </div>
                    
                    <div class="card-info-item">
                        <i class="${platform === 'facebook' ? 'fab fa-facebook' : 'fab fa-youtube'}"></i>
                        <div style="flex:1">
                            <span style="display:block; font-size: 11px; opacity: 0.6; margin-bottom: 2px;">
                                ${platform === 'facebook' ? 'Page Selection (Name : ID)' : 'Channel Selection (Name : ID)'}:
                            </span>
                            ${dropdownHtml}
                            ${platform === 'youtube' && item.channel?.gmail ? `<span style="display:block; font-size: 11px; opacity: 0.6; margin-top: 4px; color: var(--accent);">Gmail: ${item.channel.gmail}</span>` : ''}
                        </div>
                    </div>
                    
                    <div class="card-info-item">
                        <i class="fas fa-clock"></i>
                        <span>Schedule: ${item.calendar || item.Calendar || 'N/A'}</span>
                    </div>
                    <div>
                       <span class="badge badge-${platform}">${platform}</span>
                    </div>
                </div>

                <div class="card-actions">
                    <button class="btn-icon" onclick="openDriveLink('${item.video_url || item.Video_url || item.Link_on_drive || ''}')" title="View on Drive">
                        <i class="fas fa-external-link-alt"></i>
                    </button>
                    <button class="btn-icon delete" onclick="deleteRow('${sheetName}', ${index})" title="Delete">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderCalendar(container, data) {
    if (!data || data.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-calendar-times" style="display: block; font-size: 2rem; margin-bottom: 10px; opacity: 0.5;"></i>
                <p>Không có dữ liệu lịch.</p>
            </div>`;
        return;
    }

    // Header definition based on MediaCalendarModel
    const headers = [
        "STT", "Chủ đề", "Category", "Youtube", "Facebook", "Tiktok", "Lịch Chung", "Hành động"
    ];

    let html = `
        <table class="calendar-table">
            <thead>
                <tr>
                    ${headers.map(h => `<th>${h}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
    `;

    html += data.map((item, index) => {
        const yt = item.youtube || {};
        const fb = item.facebook || {};
        const tk = item.tiktok || {};

        return `
            <tr>
                <td>${item.stt}</td>
                <td class="name-cell" title="${item.name}">${item.name}</td>
                <td>${item.category}</td>
                <td>
                    <div class="table-badge-group">
                        ${yt.calendar ? `<span class="badge badge-youtube" title="${yt.channels}">YT: ${yt.calendar}</span>` : '<span class="text-muted">-</span>'}
                        <button class="btn-calendar-cell" onclick="openScheduleModal(${index}, 'youtube')">
                            <i class="fas fa-calendar-alt"></i> Calendar
                        </button>
                    </div>
                </td>
                <td>
                    <div class="table-badge-group">
                        ${fb.calendar ? `<span class="badge badge-facebook" title="${fb.pages}">FB: ${fb.calendar}</span>` : '<span class="text-muted">-</span>'}
                        <button class="btn-calendar-cell" onclick="openScheduleModal(${index}, 'facebook')">
                            <i class="fas fa-calendar-alt"></i> Calendar
                        </button>
                    </div>
                </td>
                <td>
                    <div class="table-badge-group">
                        ${tk.calendar ? `<span class="badge badge-tiktok" title="${tk.accounts}">TK: ${tk.calendar}</span>` : '<span class="text-muted">-</span>'}
                    </div>
                </td>
                <td class="date-cell">${item.general_calendar || '-'}</td>
                <td>
                    <div class="card-actions" style="border: none; margin: 0; padding: 0;">
                        <button class="btn-icon" onclick="openDriveLink('${item.link_on_drive || ''}')" title="Xem trên Drive">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                        <button class="btn-icon delete" onclick="deleteRow('Media_Calendar', ${index})" title="Xóa">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

async function updateCardField(sheetName, index, fieldData) {
    try {
        // Fetch full row first
        const loadRes = await fetch(`/api/v2/sheets/${sheetName}`);
        const rows = await loadRes.json();
        const row = rows[index];
        if (!row) return;

        // Update based on platform
        if (fieldData.platform === 'facebook') {
            if (!row.page) row.page = {};
            row.page.id = fieldData.id;
            row.page.name = fieldData.name;
            // Sync Access Token from config
            const config = facebookConfigs.find(c => c.page_id === fieldData.id);
            if (config) row.page.access_token = config.access_token;
        } else if (fieldData.platform === 'youtube') {
            if (!row.channel) row.channel = {};
            row.channel.id = fieldData.id;
            row.channel.name = fieldData.name;
            row.channel.gmail = fieldData.gmail;
        }

        const res = await fetch(`/api/v2/sheets/${sheetName}/${index}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(row)
        });

        if (res.ok) {
            console.log("Updated field successfully");
            loadSheetData(sheetName); // Refresh UI
        }
    } catch (err) {
        console.error("Update failed:", err);
    }
}

function openDriveLink(link) {
    if (link) window.open(link, '_blank');
}

async function deleteRow(sheetName, stt) {
    const confirmed = await showConfirmModal(`Bạn có chắc muốn xóa bài đăng #${stt}?`);
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/v2/sheets/${sheetName}/${stt}`, {
            method: 'DELETE'
        });
        const result = await res.json();
        if (res.ok) {
            alert('Đã xóa thành công!');
            loadSheetData(sheetName); // Refresh
        } else {
            alert('Lỗi: ' + result.message);
        }
    } catch (err) {
        alert('Lỗi hệ thống khi xóa.');
    }
}

// SCHEDULE MODAL LOGIC
function openScheduleModal(index, platform) {
    // Note: index is the 0-based data index
    const item = currentCalendarData[index];
    if (!item) return;

    activeScheduleTarget = { index, platform };

    document.getElementById('modal-item-name').textContent = item.name || 'Nội dung không tên';
    document.getElementById('modal-platform-label').textContent = `Thời gian đăng (${platform.charAt(0).toUpperCase() + platform.slice(1)})`;

    // Attempt to set current value if exists (format YYYY-MM-DDTHH:MM)
    const currentVal = platform === 'facebook' ? (item.facebook?.calendar || "") : (item.youtube?.calendar || "");
    const dateInput = document.getElementById('scheduleTimeInput');

    // Simple heuristic to populate datetime input if it looks like ISO or similar
    if (currentVal && currentVal.includes(':')) {
        try {
            // If it's already in a parsable format, try to set it. 
            // Most spreadsheets might have custom formats though.
            const date = new Date(currentVal);
            if (!isNaN(date)) {
                dateInput.value = date.toISOString().slice(0, 16);
            }
        } catch (e) { }
    } else {
        dateInput.value = "";
    }

    document.getElementById('scheduleModal').classList.add('visible');
}

function closeScheduleModal() {
    document.getElementById('scheduleModal').classList.remove('visible');
}

document.getElementById('saveScheduleBtn').onclick = async () => {
    const { index, platform } = activeScheduleTarget;
    const nextTime = document.getElementById('scheduleTimeInput').value; // YYYY-MM-DDTHH:mm
    if (!nextTime) return alert("Vui lòng chọn thời gian!");

    const item = currentCalendarData[index];
    if (!item) return;

    // Update the specific platform calendar field
    if (platform === 'facebook') {
        if (!item.facebook) item.facebook = {};
        item.facebook.calendar = nextTime.replace('T', ' ');
    } else {
        if (!item.youtube) item.youtube = {};
        item.youtube.calendar = nextTime.replace('T', ' ');
    }

    const saveBtn = document.getElementById('saveScheduleBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = "Đang lưu...";

    try {
        const res = await fetch(`/api/v2/sheets/Media_Calendar/${index}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });

        if (res.ok) {
            closeScheduleModal();
            // Sync to platform DB
            const scheduleTime = nextTime.replace('T', ' ');
            syncToPlatformDb(item, platform, scheduleTime);
            loadSheetData('Media_Calendar'); // Refresh
        } else {
            const err = await res.json();
            alert('Lỗi: ' + (err.message || "Không thể cập nhật"));
        }
    } catch (e) {
        alert('Lỗi kết nối server.');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Lưu lịch đăng";
    }
};

// SYNC LOGIC
async function syncToPlatformDb(mediaItem, platform, scheduleTime) {
    const sheetName = platform === 'facebook' ? 'Facebook_db' : 'Youtube_db';

    // Build payload based on user requirements
    const payload = {
        stt: mediaItem.stt,
        media_drive_id: mediaItem.id,
        video_name: mediaItem.name,
        video_url: mediaItem.link_on_drive,
        content_type: 'Video',
        calendar: scheduleTime
    };

    // If it's facebook, the model uses 'page' object and specific keys
    if (platform === 'facebook') {
        const pageId = mediaItem.facebook?.page_id || "";
        const config = facebookConfigs.find(c => c.page_id === pageId);
        payload.page = {
            name: mediaItem.facebook?.pages || "",
            id: pageId,
            access_token: config ? config.access_token : ""
        };
    } else {
        // Youtube model uses 'channel' object
        const channelId = mediaItem.youtube?.channel_id || "";
        const config = youtubeConfigs.find(c => c.channel_id === channelId);
        payload.channel = {
            name: mediaItem.youtube?.channels || "",
            id: channelId,
            gmail: config ? config.gmail_channel : ""
        };
    }

    try {
        console.log(`Syncing to ${sheetName}...`, payload);
        // We append for now as "set lịch" implies creating an entry in the target DB
        const res = await fetch(`/api/v2/sheets/${sheetName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            console.log(`Successfully synced to ${sheetName}`);
        } else {
            console.error(`Failed to sync to ${sheetName}`);
        }
    } catch (err) {
        console.error(`Error syncing to ${sheetName}:`, err);
    }
}

// CONFIRM MODAL LOGIC
function showConfirmModal(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const messageEl = document.getElementById('confirmModalMessage');
        const okBtn = document.getElementById('confirmOkBtn');
        const cancelBtn = document.getElementById('confirmCancelBtn');

        messageEl.textContent = message;
        modal.classList.add('visible');

        const handleResponse = (result) => {
            modal.classList.remove('visible');
            resolve(result);
            // Cleanup listeners
            okBtn.onclick = null;
            cancelBtn.onclick = null;
        };

        okBtn.onclick = () => handleResponse(true);
        cancelBtn.onclick = () => handleResponse(false);
    });
}

authBtn.onclick = () => {
    window.location.href = '/api/auth/login';
};

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

    if (!parentId || !sheetId) return alert("Vui lòng cấu hình Parent Folder ID và Sheet ID!");
    if (!folderName) return alert("Vui lòng nhập Chủ đề / Tên thư mục!");
    if (thumbnailInput.files.length === 0) return alert("Vui lòng chọn Thumbnail!");

    confirmBtn.disabled = true;
    confirmBtn.textContent = "Đang bắt đầu...";
    statusMessage.textContent = "Gửi yêu cầu lên server...";

    const formData = new FormData();
    formData.append('parentId', parentId);
    formData.append('sheetId', sheetId);
    formData.append('folderName', folderName);
    formData.append('thumbnail', thumbnailInput.files[0]);

    for (let i = 0; i < fileInput.files.length; i++) {
        formData.append('files', fileInput.files[i]);
    }

    try {
        addProgressItem(`Gửi dữ liệu: ${folderName}`);
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (response.ok && result.status === 'queued') {
            localStorage.setItem('lastTaskId', result.task_id);
            addProgressItem("🚀 Đã bắt đầu Upload ngầm!");
            statusMessage.textContent = "Đang chạy ngầm...";

            if (confirm("Yêu cầu đã được gửi. Bạn có muốn reset form không?")) {
                document.getElementById('resetBtn').click();
            }
        } else {
            throw new Error(result.message || "Unknown error");
        }
    } catch (err) {
        console.error(err);
        addProgressItem(`❌ Lỗi: ${err.message}`);
        statusMessage.textContent = "Lỗi hệ thống";
        alert(`Lỗi: ${err.message}`);
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Bắt đầu Upload";
    }
};
// CONFIG VIEW LOGIC
const configTabBtns = document.querySelectorAll('.config-tab-btn');
const configTabContents = document.querySelectorAll('.config-tab-content');

configTabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-tab');

        // Active button
        configTabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Active content
        configTabContents.forEach(c => c.classList.remove('active'));
        document.getElementById(target).classList.add('active');

        // Reset edit state
        editingConfigIndex = null;
        currentConfigSheet = null;
        const formBtn = document.querySelector(`#${target} .btn-primary`);
        if (formBtn) {
            const prefix = target === 'facebook-config' ? 'fb' : 'yt';
            formBtn.innerHTML = `<i class="fas fa-plus"></i> Thêm ${target === 'facebook-config' ? 'tài khoản' : 'kênh'}`;
            document.getElementById(`${prefix}-config-name`).value = '';
            document.getElementById(`${prefix}-config-id`).value = '';
            document.getElementById(`${prefix}-config-token`).value = '';
        }
    });
});

async function loadConfigData(sheetName) {
    const containerId = sheetName === 'Facebook_Config' ? 'facebook-config-list' : 'youtube-config-list';
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i></div>';

    try {
        const res = await fetch(`/api/v2/sheets/${sheetName}`);
        const data = await res.json();
        renderConfigList(container, data, sheetName);
    } catch (err) {
        container.innerHTML = `<div class="status-message error">Lỗi tải: ${err.message}</div>`;
    }
}

function renderConfigList(container, data, sheetName) {
    if (!data || data.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-info-circle" style="display: block; font-size: 2rem; margin-bottom: 10px; opacity: 0.5;"></i>
                <p>Chưa có cấu hình nào.</p>
            </div>`;
        return;
    }

    container.innerHTML = data.map((item, idx) => {
        const name = item.Name || item.name || item.page_name || item.channel_name || 'No Name';
        const id = item.Id || item.id || item.page_id || item.channel_id || 'N/A';
        const stt = item.STT || item.stt || (idx + 1);
        const extraInfo = sheetName === 'Facebook_Config' ? (item.Token || item.access_token || '') : (item.Gmail || item.gmail_channel || '');

        return `
            <div class="config-item">
                <div class="config-item-info">
                    <div class="config-item-name">
                        <i class="fas fa-check-circle" style="color: var(--accent); margin-right: 8px;"></i>
                        ${name}
                    </div>
                    <div class="config-item-id">ID: ${id}</div>
                    ${extraInfo ? `<div class="config-item-id" style="font-size: 11px; opacity: 0.7;">${sheetName === 'Facebook_Config' ? 'Token: ' + (extraInfo.substring(0, 10) + '...') : 'Email: ' + extraInfo}</div>` : ''}
                </div>
                <div class="config-item-actions">
                    <button class="btn-icon" onclick="editConfigRow('${sheetName}', ${JSON.stringify(item).replace(/"/g, '&quot;')}, ${stt})" title="Sửa">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon btn-icon-danger" onclick="deleteConfigRow('${sheetName}', ${stt})" title="Xóa">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function editConfigRow(sheetName, item, stt) {
    editingConfigIndex = stt;
    currentConfigSheet = sheetName;
    const prefix = sheetName === 'Facebook_Config' ? 'fb' : 'yt';

    document.getElementById(`${prefix}-config-name`).value = item.Name || item.name || item.page_name || item.channel_name || '';
    document.getElementById(`${prefix}-config-id`).value = item.Id || item.id || item.page_id || item.channel_id || '';
    document.getElementById(`${prefix}-config-token`).value = item.Token || item.token || item.access_token || item.gmail_channel || '';

    const btn = document.querySelector(`.config-tab-content#${sheetName === 'Facebook_Config' ? 'facebook-config' : 'youtube-config'} .btn-primary`);
    if (btn) {
        btn.innerHTML = '<i class="fas fa-save"></i> Cập nhật cấu hình';
        btn.onclick = (e) => addConfigAccount(e, sheetName); // Re-bind to ensure it uses the updated stt
    }
}

async function addConfigAccount(evt, sheetName) {
    const prefix = sheetName === 'Facebook_Config' ? 'fb' : 'yt';
    const nameInput = document.getElementById(`${prefix}-config-name`);
    const idInput = document.getElementById(`${prefix}-config-id`);
    const tokenInput = document.getElementById(`${prefix}-config-token`);

    const name = nameInput.value.trim();
    const id = idInput.value.trim();
    const token = tokenInput.value.trim();

    if (!name || !id) return alert("Vui lòng nhập Tên và ID!");

    // Construct data based on model
    const payload = {};
    if (sheetName === 'Facebook_Config') {
        payload.page_name = name;
        payload.page_id = id;
        payload.access_token = token;
    } else {
        payload.channel_name = name;
        payload.channel_id = id;
        payload.gmail_channel = token;
    }

    try {
        const btn = evt.target.closest('button');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> ${editingConfigIndex !== null ? 'Đang cập nhật...' : 'Đang thêm...'}`;

        const url = editingConfigIndex !== null
            ? `/api/v2/sheets/${sheetName}/${editingConfigIndex}`
            : `/api/v2/sheets/${sheetName}`;
        const method = editingConfigIndex !== null ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            nameInput.value = '';
            idInput.value = '';
            tokenInput.value = '';
            editingConfigIndex = null;
            btn.innerHTML = `<i class="fas fa-plus"></i> Thêm ${sheetName === 'Facebook_Config' ? 'tài khoản' : 'kênh'}`;
            loadConfigData(sheetName); // Refresh list
            loadConfigs(); // Refresh global dropdowns
        } else {
            const err = await res.json();
            alert('Lỗi: ' + (err.message || 'Không thể thực hiện.'));
        }
    } catch (e) {
        alert('Lỗi kết nối server.');
    } finally {
        const btn = evt.target.closest('button');
        if (btn && editingConfigIndex === null) {
            btn.disabled = false;
        }
    }
}

async function deleteConfigRow(sheetName, stt) {
    const confirmed = await showConfirmModal(`Bạn có chắc muốn xóa cấu hình #${stt}?`);
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/v2/sheets/${sheetName}?row_index=${stt}`, {
            method: 'DELETE'
        });
        if (res.ok) {
            alert('Đã xóa!');
            loadConfigData(sheetName);
        } else {
            alert('Lỗi khi xóa.');
        }
    } catch (e) {
        alert('Lỗi hệ thống.');
    }
}
