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
const geminiApiKeyInput = document.getElementById('geminiApiKey');
const fbGeminiSystemPromptInput = document.getElementById('fbGeminiSystemPrompt');
const ytGeminiSystemPromptInput = document.getElementById('ytGeminiSystemPrompt');
const viewTitle = document.getElementById('view-title');

// Edit state for configurations
let editingConfigIndex = null;
let currentConfigSheet = null;

// State for data updates
let currentCalendarData = [];
let currentFacebookData = [];
let currentYoutubeData = [];
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
    geminiApiKeyInput.value = localStorage.getItem('geminiApiKey') || "";
    fbGeminiSystemPromptInput.value = localStorage.getItem('fbGeminiSystemPrompt') || "Bạn là một người sáng tạo nội dung Facebook chuyên nghiệp. Hãy viết Hook ngắn gọn, thu hút, kèm icon và hashtag phù hợp.";
    ytGeminiSystemPromptInput.value = localStorage.getItem('ytGeminiSystemPrompt') || "Bạn là một người sáng tạo nội dung Youtube chuyên nghiệp. Hãy viết đoạn giới thiệu video hấp dẫn, tối ưu SEO và lôi cuốn người xem.";

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
    localStorage.setItem('geminiApiKey', geminiApiKeyInput.value.trim());
    localStorage.setItem('fbGeminiSystemPrompt', fbGeminiSystemPromptInput.value.trim());
    localStorage.setItem('ytGeminiSystemPrompt', ytGeminiSystemPromptInput.value.trim());
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
        'Media_Calendar': 'calendar-groups-container',
        'Published_History': 'history-list'
    }[sheetName];

    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        const res = await fetch(`/api/v2/sheets/${sheetName}`);
        const data = await res.json();

        if (sheetName === 'Media_Calendar') {
            currentCalendarData = data;
            renderCalendar(container, data);
        } else if (sheetName === 'Facebook_db') {
            currentFacebookData = data;
            renderCards(container, data, sheetName);
        } else if (sheetName === 'Youtube_db') {
            currentYoutubeData = data;
            renderCards(container, data, sheetName);
        } else if (sheetName === 'Published_History') {
            currentHistoryData = data;
            renderHistory(container, data);
        }
    } catch (err) {
        container.innerHTML = `<div class="status-message error">Lỗi tải dữ liệu: ${err.message}</div>`;
    }
}

function renderCards(container, data, sheetName) {
    const showAll = filterState[sheetName];

    // Sync Toggle Switch UI
    const toggleId = sheetName === 'Facebook_db' ? 'toggle-facebook-all' : 'toggle-youtube-all';
    const toggleEl = document.getElementById(toggleId);
    if (toggleEl) toggleEl.checked = showAll;

    // Filter Logic
    const activeData = data.filter(item => {
        if (showAll) return true; // Show All

        // Default: New Only (Not Posted & No Hook)
        const status = (item.status || '').toUpperCase();
        const isPosted = status === 'PUBLISHED' || status === 'SUCCESS';
        const hasHook = item.hook && item.hook.trim().length > 0;

        return !isPosted && !hasHook;
    });

    if (!activeData || activeData.length === 0) {
        container.innerHTML = `<p class="empty-state">Không có dữ liệu phù hợp (Chế độ: ${showAll ? 'Tất cả' : 'Mới chưa xử lý'}).</p>`;
        return;
    }

    const platform = sheetName === 'Facebook_db' ? 'facebook' : 'youtube';

    container.innerHTML = activeData.map((item, index) => {
        // Find original index in full data array to ensure actions work on correct row
        // Note: index passed to map is local to activeData. We need the real index from the sheet 
        // which matches the 'stt' usually, but 'stt' is a string. 
        // Simplest: use data.indexOf(item). 
        // Wait, updateCardField and other functions take 'index'. If I filter, the index changes.
        // Important: logic functions take row index. 
        // I MUST pass the original index.
        const originalIndex = data.indexOf(item);

        const configs = platform === 'facebook' ? facebookConfigs : youtubeConfigs;
        const currentVal = platform === 'facebook' ? (item.page?.id || "") : (item.channel?.id || "");

        const dropdownHtml = `
            <select class="card-select" onchange="updateCardField('${sheetName}', ${originalIndex}, { platform: '${platform}', id: this.value, name: this.options[this.selectedIndex].text, gmail: this.options[this.selectedIndex].getAttribute('data-gmail') || '' })">
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
            <div class="content-card" onclick="openHookModal(event, '${sheetName}', ${originalIndex})">
                <div class="card-header">
                    <div class="card-title" title="${item.video_name || item.Name_video || 'No Name'}">
                        ${item.video_name || item.Name_video || 'No Title'}
                    </div>
                    <div class="card-id">#${item.stt || item.STT || (originalIndex + 1)}</div>
                </div>
                
                <div class="card-body">
                    <div class="card-info-item">
                        <i class="fas fa-quote-left"></i>
                        <span class="hook-preview">${item.hook ? item.hook.substring(0, 50) + (item.hook.length > 50 ? '...' : '') : 'Click để thêm mô tả (Hook)...'}</span>
                    </div>

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
                        <i class="fas fa-file-alt"></i>
                        <div style="flex:1">
                            <span style="display:block; font-size: 11px; opacity: 0.6; margin-bottom: 2px;">Loại bài đăng:</span>
                            <select class="card-select" onchange="updateCardField('${sheetName}', ${originalIndex}, { field: 'post_type', value: this.value })">
                                ${platform === 'facebook'
                ? ['Image', 'Text', 'Video', 'Reels'].map(opt => `<option value="${opt}" ${item.post_type === opt ? 'selected' : ''}>${opt}</option>`).join('')
                : `<option value="Video" selected>Video</option>`}
                            </select>
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
                    <button class="btn-icon publish" onclick="publishPost(event, '${sheetName}', ${originalIndex})" title="Đăng ngay">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                    <button class="btn-icon delete" onclick="deleteRow('${sheetName}', ${originalIndex})" title="Delete">
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
        } else if (fieldData.field === 'post_type') {
            row.post_type = fieldData.value;
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
    if (window.event) window.event.stopPropagation();
    if (link) window.open(link, '_blank');
}

async function deleteRow(sheetName, stt) {
    if (window.event) window.event.stopPropagation();
    const isMediaCalendar = sheetName === 'Media_Calendar';
    const message = isMediaCalendar
        ? `Bạn có chắc muốn xóa bài đăng #${stt}? HÀNH ĐỘNG NÀY SẼ XÓA CẢ THƯ MỤC TRÊN DRIVE.`
        : `Bạn có chắc muốn xóa bài đăng #${stt}?`;

    const confirmed = await showConfirmModal({
        title: "Xác nhận xóa?",
        message: message,
        type: "danger",
        okText: "Xác nhận xóa",
        requireText: isMediaCalendar
    });
    if (!confirmed) return;

    try {
        const url = isMediaCalendar ? `/api/v2/sheets/${sheetName}/${stt}?delete_drive=true` : `/api/v2/sheets/${sheetName}/${stt}`;
        const res = await fetch(url, {
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

async function revokeSchedule() {
    const { index, platform } = activeScheduleTarget;
    const item = currentCalendarData[index];
    if (!item) return;

    const revokeBtn = document.getElementById('revokeScheduleBtn');
    revokeBtn.disabled = true;
    revokeBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Đang thu hồi...';

    try {
        // 1. Clear calendar field in Media_Calendar
        if (platform === 'facebook') {
            if (!item.facebook) item.facebook = {};
            item.facebook.calendar = "";
        } else {
            if (!item.youtube) item.youtube = {};
            item.youtube.calendar = "";
        }

        const res = await fetch(`/api/v2/sheets/Media_Calendar/${index}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });

        if (res.ok) {
            // 2. Delete from platform DB
            await syncToPlatformDb(item, platform, "", true);
            closeScheduleModal();
            loadSheetData('Media_Calendar');
        } else {
            alert("Lỗi khi thu hồi lịch.");
        }
    } catch (e) {
        console.error(e);
        alert("Lỗi hệ thống.");
    } finally {
        revokeBtn.disabled = false;
        revokeBtn.innerHTML = '<i class="fas fa-undo"></i> Thu hồi lịch';
    }
}

// SYNC LOGIC (Upsert/Delete)
async function syncToPlatformDb(mediaItem, platform, scheduleTime, isRevoke = false) {
    const sheetName = platform === 'facebook' ? 'Facebook_db' : 'Youtube_db';
    const driveIdField = 'media_drive_id';
    const targetDriveId = mediaItem.id;

    try {
        // 1. Fetch current data to check for duplicates
        const listRes = await fetch(`/api/v2/sheets/${sheetName}`);
        const listData = await listRes.json();

        // Find existing row with matching Drive ID
        const existingIdx = listData.findIndex(row => row[driveIdField] === targetDriveId);

        if (isRevoke) {
            if (existingIdx !== -1) {
                console.log(`Sync: Revoking - Deleting row ${existingIdx} in ${sheetName}`);
                await fetch(`/api/v2/sheets/${sheetName}/${existingIdx}`, { method: 'DELETE' });
            }
            return;
        }

        // Build payload
        const payload = {
            stt: mediaItem.stt,
            media_drive_id: targetDriveId,
            video_name: mediaItem.name,
            video_url: mediaItem.link_on_drive,
            thumbnail_url: mediaItem.thumbnail || "",
            content_type: 'Video',
            calendar: scheduleTime
        };

        if (platform === 'facebook') {
            const pageId = mediaItem.facebook?.page_id || "";
            const config = facebookConfigs.find(c => c.page_id === pageId);
            payload.page = {
                name: mediaItem.facebook?.pages || "",
                id: pageId,
                access_token: config ? config.access_token : ""
            };
        } else {
            const channelId = mediaItem.youtube?.channel_id || "";
            const config = youtubeConfigs.find(c => c.channel_id === channelId);
            payload.channel = {
                name: mediaItem.youtube?.channels || "",
                id: channelId,
                gmail: config ? config.gmail_channel : ""
            };
        }

        if (existingIdx !== -1) {
            // Update mode
            console.log(`Sync: Updating existing row at ${existingIdx} in ${sheetName}`);
            await fetch(`/api/v2/sheets/${sheetName}/${existingIdx}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            // Append mode
            console.log(`Sync: Appending new row to ${sheetName}`);
            await fetch(`/api/v2/sheets/${sheetName}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }
    } catch (err) {
        console.error(`Sync to ${sheetName} failed:`, err);
    }
}

// CONFIRM MODAL LOGIC
/**
 * Hiển thị modal xác nhận tùy chỉnh.
 * @param {Object|string} options - Thông báo hoặc object cấu hình
 * @returns {Promise<boolean>}
 */
function showConfirmModal(options) {
    if (typeof options === 'string') {
        options = { message: options };
    }

    const {
        title = "Xác nhận?",
        message = "Bạn có chắc chắn muốn thực hiện hành động này?",
        type = "danger", // danger, primary, warning, success
        okText = "Xác nhận",
        cancelText = "Hủy",
        requireText = false
    } = options;

    const modal = document.getElementById('confirmModal');
    const msgEl = document.getElementById('confirmModalMessage');
    const titleEl = modal.querySelector('h3');
    const iconEl = modal.querySelector('.warning-icon');
    const okBtn = document.getElementById('confirmOkBtn');
    const cancelBtn = document.getElementById('confirmCancelBtn');
    const textWrap = document.getElementById('confirmTextWrap');
    const textInput = document.getElementById('confirmTextInput');

    // Cập nhật nội dung
    msgEl.innerText = message;
    titleEl.innerText = title;
    okBtn.innerText = okText;
    cancelBtn.innerText = cancelText;

    // Cập nhật giao diện theo type
    modal.className = `modal-overlay modal-${type}`;

    // Reset và cấu hình input text nếu cần
    textWrap.style.display = requireText ? 'block' : 'none';
    textInput.value = '';

    modal.classList.add('visible');

    return new Promise((resolve) => {
        const handleCancel = () => {
            modal.classList.remove('visible');
            cleanup();
            resolve(false);
        };

        const handleOk = () => {
            if (requireText && textInput.value.trim().toUpperCase() !== 'DELETE') {
                textInput.classList.add('shake');
                setTimeout(() => textInput.classList.remove('shake'), 400);
                return;
            }
            modal.classList.remove('visible');
            cleanup();
            resolve(true);
        };

        const cleanup = () => {
            okBtn.removeEventListener('click', handleOk);
            cancelBtn.removeEventListener('click', handleCancel);
        };

        okBtn.addEventListener('click', handleOk);
        cancelBtn.addEventListener('click', handleCancel);
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

            const resetConfirmed = await showConfirmModal({
                title: "Thành công!",
                message: "Yêu cầu đã được gửi. Bạn có muốn reset form không?",
                type: "warning",
                okText: "Reset Form",
                cancelText: "Giữ lại dữ liệu"
            });
            if (resetConfirmed) {
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

// HOOK MODAL LOGIC
let activeHookTarget = { sheetName: null, index: null };

async function openHookModal(event, sheetName, index) {
    // If we click select/button inside card, don't trigger modal
    const target = event.target;
    if (target.tagName === 'SELECT' || target.tagName === 'OPTION' || target.closest('.card-actions') || target.closest('button')) {
        return;
    }

    activeHookTarget = { sheetName, index };

    // Choose local data for instant opening
    const rows = sheetName === 'Facebook_db' ? currentFacebookData : currentYoutubeData;
    const item = rows[index];
    if (!item) return;

    document.getElementById('hook-item-name').textContent = item.video_name || item.Name_video || 'Nội dung #' + (index + 1);
    document.getElementById('hookInput').value = item.hook || "";
    document.getElementById('hookModal').classList.add('visible');
}

function closeHookModal() {
    document.getElementById('hookModal').classList.remove('visible');
}

document.getElementById('saveHookBtn').onclick = async () => {
    const { sheetName, index } = activeHookTarget;
    const newHook = document.getElementById('hookInput').value;

    const saveBtn = document.getElementById('saveHookBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = "Đang lưu...";

    try {
        const rows = sheetName === 'Facebook_db' ? currentFacebookData : currentYoutubeData;
        const row = rows[index];

        row.hook = newHook;

        const res = await fetch(`/api/v2/sheets/${sheetName}/${index}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(row)
        });

        if (res.ok) {
            closeHookModal();
            loadSheetData(sheetName);
        } else {
            alert('Lỗi khi lưu Hook.');
        }
    } catch (e) {
        alert('Lỗi kết nối server.');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Lưu nội dung";
    }
};

// Function: Delete Post
async function deletePost(index) {
    const confirmed = await showConfirmModal({
        title: "Xóa bài viết?",
        message: "Bạn có chắc muốn xóa bài viết này khỏi Platform? Hành động này không thể hoàn tác.",
        type: "danger",
        okText: "Xóa vĩnh viễn"
    });

    if (!confirmed) return;

    fetch('/api/v2/post/delete', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: index })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Optional: Show success modal
                // showConfirmModal({ title: "Thành công", message: "Đã xóa bài viết.", type: "success" });
                loadPublishedHistory();
            } else {
                alert("Lỗi: " + (data.error || "Không xác định"));
            }
        })
        .catch(err => alert("Lỗi kết nối: " + err));
}

// Function: Publish Now (Skip Schedule)
async function publishNow(index) {
    const confirmed = await showConfirmModal({
        title: "Public Ngay?",
        message: "Bạn có chắc muốn Public ngay lập tức bài viết này (Bỏ qua lịch hẹn)?",
        type: "success",
        okText: "Public Ngay"
    });

    if (!confirmed) return;

    fetch('/api/v2/post/publish-now', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: index })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Auto Update UI without full reload if possible, or just reload
                // showConfirmModal({ title: "Thành công", message: "Đã Public thành công!", type: "success" });
                alert("Đã Public thành công! Trạng thái đã chuyển sang SUCCESS.");
                loadPublishedHistory();
            } else {
                alert("Lỗi: " + (data.error || "Không xác định"));
            }
        })
        .catch(err => alert("Lỗi kết nối: " + err));
}

async function generateAiHook() {
    const { sheetName, index } = activeHookTarget;
    const rows = sheetName === 'Facebook_db' ? currentFacebookData : currentYoutubeData;
    const item = rows[index];

    if (!item) return;

    const rawKeys = geminiApiKeyInput.value.trim();
    if (!rawKeys) {
        alert("Vui lòng cấu hình Gemini API Key (ít nhất 1 key) trong phần Cài đặt chung!");
        return;
    }

    const apiKeys = rawKeys.split('\n').map(k => k.trim()).filter(k => k.length > 0);
    const aiBtn = document.getElementById('aiWriteBtn');
    const hookInput = document.getElementById('hookInput');

    aiBtn.disabled = true;
    const originalText = aiBtn.innerHTML;

    const videoName = item.video_name || item.Name_video || "nội dung này";
    const systemPrompt = sheetName === 'Facebook_db' ? fbGeminiSystemPromptInput.value.trim() : ytGeminiSystemPromptInput.value.trim();
    const userPrompt = `Hãy viết một đoạn Hook ngắn gọn (khoảng 2-3 câu) để mô tả cho video có tên: "${videoName}". ${item.hook ? 'Tham khảo nội dung hiện tại: ' + item.hook : ''}`;

    let success = false;
    let lastError = "";

    for (let i = 0; i < apiKeys.length; i++) {
        const apiKey = apiKeys[i];
        aiBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Thử Key #${i + 1}...`;

        try {
            const res = await fetch('/api/v2/ai/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_key: apiKey,
                    system_prompt: systemPrompt,
                    user_prompt: userPrompt
                })
            });

            const data = await res.json();

            if (res.ok) {
                hookInput.value = data.result;
                success = true;
                break;
            } else {
                if (res.status === 429 || (data.error && data.error.includes("429"))) {
                    console.warn(`Key #${i + 1} bị giới hạn (429). Đang chuyển sang key tiếp theo...`);
                    lastError = "Tất cả API Key đều bị giới hạn (429).";
                    continue;
                } else {
                    alert(`Lỗi AI (Key #${i + 1}): ` + data.error);
                    lastError = data.error;
                    break;
                }
            }
        } catch (err) {
            console.error(err);
            lastError = "Lỗi kết nối server.";
            continue;
        }
    }

    if (!success && lastError) {
        alert("Không thể tạo nội dung: " + lastError);
    }

    aiBtn.disabled = false;
    aiBtn.innerHTML = originalText;
}
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
    const confirmed = await showConfirmModal({
        title: "Xóa cấu hình?",
        message: `Bạn có chắc muốn xóa cấu hình #${stt}?`,
        type: "danger",
        okText: "Xóa ngay"
    });
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

// --- DỊCH VỤ ĐĂNG BÀI (POST SERVICE UI) ---

async function publishPost(event, sheetName, index) {
    if (event) event.stopPropagation();

    const confirmed = await showConfirmModal({
        title: "Xác nhận đăng bài?",
        message: `Bạn có chắc muốn ĐĂNG bài viết này lên ${sheetName === 'Facebook_db' ? 'Facebook' : 'YouTube'} không?`,
        type: "primary",
        okText: "Đăng ngay",
        cancelText: "Hủy"
    });

    if (!confirmed) return;

    // Tìm button element chính xác
    const btn = event ? (event.currentTarget || event.target.closest('button')) : null;
    let originalHtml = "";

    if (btn) {
        originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>';
    }

    console.log(`[Publish] Đang gửi yêu cầu cho ${sheetName} tại dòng ${index}`);

    try {
        const res = await fetch('/api/v2/post/publish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sheet_name: sheetName, index: index })
        });

        if (!res.ok) {
            const errorText = await res.text();
            throw new Error(errorText || res.statusText);
        }

        const result = await res.json();
        if (result.task_id) {
            addProgressItem(`🕒 [Task] Đã bắt đầu khởi tạo (ID: ${result.task_id.substring(0, 8)}...)`);
            startTaskPolling(result.task_id, btn, originalHtml, sheetName);
        } else {
            throw new Error(result.error || 'Server không trả về Task ID');
        }
    } catch (err) {
        console.error("[Publish Error]", err);
        alert('❌ Lỗi: ' + err.message);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    }
}

function startTaskPolling(taskId, btn, originalHtml, sheetName) {
    let lastMessage = "";
    const interval = setInterval(async () => {
        try {
            const res = await fetch('/api/tasks');
            const tasks = await res.json();
            const task = tasks[taskId];

            if (!task) return;

            if (task.status === 'processing') {
                btn.innerHTML = '<i class="fas fa-sync fa-spin"></i>';
                // Cập nhật progress item nếu có log message mới và khác message cũ
                if (task.message && task.message !== lastMessage) {
                    addProgressItem(`🔄 [Post] ${task.message}`);
                    lastMessage = task.message;
                }
            } else if (task.status === 'success') {
                clearInterval(interval);
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check-circle" style="color: #10b981;"></i>';
                addProgressItem(`✅ [Post] Đăng thành công! (ID: ${task.result?.post_id || 'N/A'})`);
                alert('🚀 Bài viết đã được đăng thành công!');
                loadSheetData(sheetName);

                // Reset icon sau 3 giây
                setTimeout(() => { btn.innerHTML = originalHtml; }, 3000);
            } else if (task.status === 'error') {
                clearInterval(interval);
                btn.disabled = false;
                btn.innerHTML = originalHtml;
                addProgressItem(`❌ [Post] Lỗi: ${task.message}`);
                alert('❌ Lỗi khi đăng bài: ' + task.message);
            }
        } catch (e) {
            console.error("Polling error:", e);
        }
    }, 2500);
}

function renderHistory(container, data) {
    if (!data || !Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<p class="empty-state"><i class="fas fa-info-circle"></i> Chưa có lịch sử bài đăng hoặc đang tải dữ liệu...</p>';
        return;
    }

    // Tách dữ liệu theo nền tảng
    const facebookItems = data.filter(item => (item.Page_name || item.Facebook_Post_Id) && !item.Channel_name);
    const youtubeItems = data.filter(item => (item.Channel_name || item.Youtube_Post_Id));

    const renderGroup = (items, title, iconClass, badgeClass) => {
        if (!items || items.length === 0) return '';

        const gridHtml = items.map((item) => {
            const realIndex = data.indexOf(item);
            const isFacebook = !!item.Facebook_Post_Id;
            const platformClass = isFacebook ? 'facebook' : 'youtube';
            const scheduledStatus = item.Status === 'SCHEDULED';

            // Generic Management Actions
            let managementActions = `
                <div class="card-mgmt-actions">
                    <button class="btn-icon-tiny" onclick="syncThumbnail(${realIndex})" title="Đồng bộ Thumbnail">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    ${scheduledStatus ? `
                    <button class="btn-icon-tiny success" onclick="publishNow(${realIndex})" title="🚀 Public Ngay (Bỏ qua lịch)">
                        <i class="fas fa-rocket"></i>
                    </button>
                    ` : ''}
                    <button class="btn-icon-tiny" onclick="openEditPostModal(${realIndex})" title="Sửa nội dung">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon-tiny danger" onclick="deletePublishedPost(${realIndex}, '${platformClass}')" title="Xoá bài đăng (Platform + Sheet)">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;

            return `
            <div class="content-card history-card premium-glass">
                <div class="card-media-wrap">
                    <img src="${item.Thumbnail || 'https://placehold.co/150'}" alt="Thumbnail" class="history-thumb" onerror="this.src='https://placehold.co/150?text=No+Image'">
                    <div class="platform-icon-overlay">
                        <i class="${isFacebook ? 'fab fa-facebook' : 'fab fa-youtube'}"></i>
                    </div>
                    ${scheduledStatus ? `
                    <div class="scheduled-overlay" title="Bài viết đang chờ đăng">
                        <i class="fas fa-clock"></i>
                    </div>` : `
                    <div class="play-button-overlay">
                        <i class="fas fa-play"></i>
                    </div>`}
                    ${managementActions}
                </div>
                
                <div class="card-content-wrap">
                    <div class="card-title-line" title="${item.Name_video}">${item.Name_video || 'No Title'}</div>
                    
                    <div class="status-row">
                        <span class="status-label-glass ${item.Status === 'SUCCESS' ? 'status-success' : (scheduledStatus ? 'status-warning' : 'status-fail')}">
                            <span class="dot"></span> ${item.Status || 'Unknown'}
                        </span>
                    </div>

                    <div class="card-footer-actions">
                        <button class="btn-platform-view" onclick="window.open('${item.Link_On_Platfrom}', '_blank')">
                            <span>View on Platform</span>
                            <i class="fas fa-arrow-right"></i>
                        </button>
                    </div>
                </div>
                
                <button class="btn-delete-history" onclick="deleteHistoryRow(${realIndex})" title="Chỉ xoá dòng lịch sử (Không xoá bài)">
                    <i class="fas fa-eraser"></i>
                </button>
            </div>`;
        }).join('');

        return `
            <div style="margin-bottom: 40px;">
                <h3 style="margin-bottom: 20px; font-size: 1.1rem; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
                    <i class="${iconClass}"></i> ${title} <span class="badge ${badgeClass}" style="margin-left: auto;">${items.length}</span>
                </h3>
                <div class="history-grid">
                    ${gridHtml}
                </div>
            </div>
        `;
    };

    let fullHtml = '';
    if (facebookItems.length > 0) fullHtml += renderGroup(facebookItems, 'Facebook History', 'fab fa-facebook', 'badge-facebook');
    if (youtubeItems.length > 0) fullHtml += renderGroup(youtubeItems, 'YouTube History', 'fab fa-youtube', 'badge-youtube');

    container.innerHTML = fullHtml || '<p class="empty-state">Không có dữ liệu lịch sử.</p>';
}

// --- GENERIC POST MANAGEMENT (FB & YT) ---

let activeEditPostIndex = null;

async function syncThumbnail(index) {
    addProgressItem(`🔄 Đang đồng bộ Thumbnail bài viết #${index}...`);
    try {
        const res = await fetch(`/api/v2/post/sync-thumbnail/${index}`, { method: 'POST' });
        const result = await res.json();
        if (res.ok) {
            addProgressItem(`✅ Đồng bộ Thumbnail thành công!`);
            loadSheetData('Published_History');
        } else {
            alert("Lỗi đồng bộ: " + result.error);
        }
    } catch (e) {
        alert("Lỗi kết nối server.");
    }
}

async function openEditPostModal(index) {
    const rows = await (await fetch('/api/v2/sheets/Published_History')).json();
    const item = rows[index];
    if (!item) return;

    activeEditPostIndex = index;

    // Reset fields & Show Loading
    document.getElementById('edit-post-title-display').textContent = item.Name_video || `Bài viết #${index}`;
    document.getElementById('editPostTitle').value = "Đang tải...";
    document.getElementById('editPostDesc').value = "Đang tải nội dung từ Platform...";
    document.getElementById('editPostPrivacy').value = "";
    document.getElementById('savePostEditBtn').disabled = true;

    document.getElementById('editPostModal').classList.add('visible');

    // Fetch details from backend
    try {
        const res = await fetch(`/api/v2/post/details/${index}`);
        const result = await res.json();

        if (res.ok && result.success) {
            const data = result.data;
            document.getElementById('editPostTitle').value = data.title || "";
            document.getElementById('editPostDesc').value = data.description || "";
            // Privacy mapping if needed, or just set if valid
            const p = data.privacy;
            if (p === 'public' || p === 'private' || p === 'unlisted') {
                document.getElementById('editPostPrivacy').value = p;
            }
        } else {
            document.getElementById('editPostDesc').value = "Không thể tải nội dung: " + (result.error || "Unknown");
        }
    } catch (e) {
        document.getElementById('editPostDesc').value = "Lỗi kết nối: " + e.message;
    } finally {
        document.getElementById('savePostEditBtn').disabled = false;
    }
}

function closeEditPostModal() {
    document.getElementById('editPostModal').classList.remove('visible');
    activeEditPostIndex = null;
}

document.getElementById('savePostEditBtn').onclick = async () => {
    if (activeEditPostIndex === null) return;

    const title = document.getElementById('editPostTitle').value;
    const desc = document.getElementById('editPostDesc').value;
    const privacy = document.getElementById('editPostPrivacy').value;
    const thumbFile = document.getElementById('editPostThumb').files[0];

    const btn = document.getElementById('savePostEditBtn');
    btn.disabled = true;
    btn.innerHTML = "Đang lưu...";

    try {
        let res;
        // Nếu có file thumbnail, dùng FormData
        if (thumbFile) {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('description', desc);
            formData.append('privacy', privacy);
            formData.append('thumbnail', thumbFile);

            res = await fetch(`/api/v2/post/update/${activeEditPostIndex}`, {
                method: 'POST',
                body: formData // Content-Type tự động set multipart/form-data
            });
        } else {
            // Không có file, dùng JSON như cũ
            res = await fetch(`/api/v2/post/update/${activeEditPostIndex}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    description: desc,
                    privacy: privacy
                })
            });
        }

        const result = await res.json();

        if (res.ok) {
            alert("Cập nhật thành công!");
            closeEditPostModal();
            loadSheetData('Published_History');
        } else {
            alert("Lỗi: " + result.error);
        }
    } catch (e) {
        alert("Lỗi hệ thống: " + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = "Lưu thay đổi";
    }
};

async function deletePublishedPost(index, platform) {
    const confirmed = await showConfirmModal({
        title: "Xóa bài đăng?",
        message: `Hành động này sẽ XÓA bài viết trên ${platform.toUpperCase()} và xóa khỏi lịch sử. Không thể hoàn tác!`,
        type: "danger",
        okText: "Xóa vĩnh viễn"
    });
    if (!confirmed) return;

    addProgressItem(`🗑️ Đang xóa bài viết #${index} khỏi Platform & History...`);
    try {
        const res = await fetch(`/api/v2/post/delete/${index}`, {
            method: 'DELETE'
        });
        const result = await res.json();
        if (res.ok) {
            addProgressItem(`✅ Đã xóa thành công bài viết #${index}.`);
            loadSheetData('Published_History');
        } else {
            alert("Lỗi khi xóa: " + result.error);
        }
    } catch (e) {
        alert("Lỗi kết nối server.");
    }
}

async function deleteHistoryRow(index) {
    const confirmed = await showConfirmModal({
        title: "Xóa lịch sử?",
        message: "Bạn có chắc muốn xoá dòng lịch sử này? (Bài viết trên Platform vẫn giữ nguyên)",
        type: "warning",
        okText: "Xóa dòng"
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/v2/sheets/Published_History/${index}`, { method: 'DELETE' });
        if (res.ok) {
            loadSheetData('Published_History');
        } else {
            alert('Lỗi khi xoá.');
        }
    } catch (e) {
        alert('Lỗi hệ thống.');
    }
}

// --- HELPER WRAPPER ---
function loadPublishedHistory() {
    console.log("Reloading Published History...");
    loadSheetData('Published_History');
}
