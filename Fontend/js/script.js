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
const wooGeminiSystemPromptInput = document.getElementById('wooGeminiSystemPrompt');
const viewTitle = document.getElementById('view-title');

// Edit state for configurations
let editingConfigIndex = null;
let currentConfigSheet = null;

// State for data updates
let currentCalendarData = [];
let currentFacebookData = [];
let currentYoutubeData = [];
let currentWooData = [];
let activeScheduleTarget = { index: null, platform: null };

// Filter State
let filterState = {
    Facebook_db: false,
    Youtube_db: false
};

// --- TOGGLE FILTER ---
function toggleFilter(sheetName) {
    filterState[sheetName] = !filterState[sheetName];
    loadSheetData(sheetName);
}

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
        if (target === 'woocommerce-view') loadWooDb();
    });
});

window.onload = () => {
    // Load config
    parentFolderInput.value = localStorage.getItem('parentFolderId') || DEFAULT_DRIVE_ID;
    sheetIdInput.value = localStorage.getItem('sheetId') || DEFAULT_SHEET_ID;
    geminiApiKeyInput.value = localStorage.getItem('geminiApiKey') || "";
    fbGeminiSystemPromptInput.value = localStorage.getItem('fbGeminiSystemPrompt') || "Bạn là một người sáng tạo nội dung Facebook chuyên nghiệp. Hãy viết Hook ngắn gọn, thu hút, kèm icon và hashtag phù hợp.";
    ytGeminiSystemPromptInput.value = localStorage.getItem('ytGeminiSystemPrompt') || "Bạn là một người sáng tạo nội dung Youtube chuyên nghiệp. Hãy viết đoạn giới thiệu video hấp dẫn, tối ưu SEO và lôi cuốn người xem.";
    wooGeminiSystemPromptInput.value = localStorage.getItem('wooGeminiSystemPrompt') || "Bạn là một chuyên gia SEO WooCommerce. Hãy viết mô tả sản phẩm hấp dẫn, chuẩn SEO, bao gồm các thẻ HTML H2, H3, và các đoạn bullet points nổi bật tính năng.";

    // WooCommerce Specific Setup
    const wooSystemPrompt = "Bạn là một chuyên gia SEO WooCommerce. Hãy viết mô tả sản phẩm hấp dẫn, chuẩn SEO, bao gồm các thẻ HTML H2, H3, và các đoạn bullet points nổi bật tính năng.";
    if (!localStorage.getItem('wooGeminiSystemPrompt')) {
        localStorage.setItem('wooGeminiSystemPrompt', wooSystemPrompt);
    }

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
    localStorage.setItem('wooGeminiSystemPrompt', wooGeminiSystemPromptInput.value.trim());
    alert('Cấu hình đã được lưu!');
}

// --- MULTI-ACCOUNT GOOGLE MANAGEMENT ---

async function loadLinkedAccounts() {
    const container = document.getElementById('google-accounts-list');
    if (!container) return;

    container.innerHTML = '<p class="empty-state">Đang tải...</p>';

    try {
        const res = await fetch('/api/auth/accounts');
        const data = await res.json();

        if (data.success && data.accounts && data.accounts.length > 0) {
            container.innerHTML = data.accounts.map(acc => `
                <div class="account-card glass-card" style="display: flex; align-items: center; gap: 15px; padding: 15px; margin-bottom: 10px;">
                    <img src="${acc.picture || 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y'}" 
                         alt="Avatar" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;">
                    <div style="flex: 1;">
                        <strong style="color: var(--text-primary);">${acc.name || 'Tài khoản Google'}</strong>
                        <p style="color: var(--text-secondary); font-size: 0.85em; margin: 2px 0;">${acc.email}</p>
                        <p style="color: var(--text-muted); font-size: 0.8em;">
                            <i class="fab fa-youtube" style="color: var(--danger);"></i> 
                            ${acc.channels?.length || 0} kênh YouTube
                        </p>
                    </div>
                    <div class="account-actions" style="display: flex; gap: 8px;">
                        <button class="btn btn-small" onclick="refreshAccountChannels('${acc.id}')" title="Refresh kênh">
                            <i class="fas fa-sync"></i>
                        </button>
                        <button class="btn btn-small btn-danger" onclick="removeGoogleAccount('${acc.id}')" title="Xóa tài khoản">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 30px;">
                    <i class="fab fa-google" style="font-size: 3em; color: var(--text-muted); margin-bottom: 15px;"></i>
                    <p>Chưa có tài khoản Google nào được kết nối.</p>
                    <p style="font-size: 0.9em; color: var(--text-secondary);">Nhấn "Thêm tài khoản" để bắt đầu.</p>
                </div>
            `;
        }
    } catch (err) {
        container.innerHTML = `<p class="empty-state" style="color: var(--danger);">Lỗi tải danh sách: ${err.message}</p>`;
    }
}

async function addGoogleAccount() {
    try {
        const res = await fetch('/api/auth/accounts/add', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            alert(`Đã thêm tài khoản: ${data.email}\nSố kênh YouTube: ${data.channels?.length || 0}`);
            loadLinkedAccounts();
        } else if (data.needs_manual_auth && data.auth_url) {
            // Remote access: Mở URL trong tab mới
            alert('Một tab mới sẽ mở để bạn đăng nhập Google.\n\nSau khi xác thực xong, hãy quay lại và nhấn "Thêm tài khoản" lần nữa.');
            window.open(data.auth_url, '_blank');
        } else {
            alert(`Lỗi: ${data.error || data.message || 'Không xác định'}`);
        }
    } catch (err) {
        alert(`Lỗi kết nối: ${err.message}`);
    }
}

async function removeGoogleAccount(accountId) {
    const confirmed = await showConfirmModal({
        title: "Xóa tài khoản?",
        message: "Bạn có chắc muốn xóa tài khoản này? Các kênh YouTube liên kết sẽ không thể đăng bài được nữa.",
        type: "danger",
        okText: "Xóa ngay"
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/auth/accounts/${accountId}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            alert('Đã xóa tài khoản thành công.');
            loadLinkedAccounts();
        } else {
            alert(`Lỗi: ${data.error}`);
        }
    } catch (err) {
        alert(`Lỗi kết nối: ${err.message}`);
    }
}

async function refreshAccountChannels(accountId) {
    const confirmed = await showConfirmModal({
        title: "Cập nhật kênh?",
        message: "Hệ thống sẽ đồng bộ lại danh sách kênh từ Google và cập nhật Sheet Youtube_Config.",
        type: "primary",
        okText: "Cập nhật"
    });
    if (!confirmed) return;
    try {
        const res = await fetch(`/api/auth/accounts/${accountId}/channels`);
        const data = await res.json();

        if (data.success) {
            alert(`Đã cập nhật ${data.channels?.length || 0} kênh.`);
            loadLinkedAccounts();
        } else {
            alert(`Lỗi: ${data.error}`);
        }
    } catch (err) {
        alert(`Lỗi: ${err.message}`);
    }
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
 * @param {Object|string} titleOrOptions - Tiêu đề hoặc object cấu hình
 * @param {string} [message] - Nội dung thông báo (nếu đối số 1 là string)
 * @returns {Promise<boolean>}
 */
function showConfirmModal(titleOrOptions, message) {
    let options = {};
    if (typeof titleOrOptions === 'string') {
        options = { title: titleOrOptions, message: message || "" };
    } else {
        options = titleOrOptions;
    }

    const {
        title = "Xác nhận?",
        message: finalMessage = "Bạn có chắc chắn muốn thực hiện hành động này?",
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
    msgEl.innerHTML = finalMessage; // Sử dụng innerHTML để hiển thị được HTML preview
    titleEl.innerText = title;
    okBtn.innerText = okText;
    cancelBtn.innerText = cancelText;
    cancelBtn.style.display = cancelText ? 'inline-block' : 'none';

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

function showSuccessModal(title, message) {
    return showConfirmModal({
        title,
        message,
        type: 'success',
        okText: 'OK',
        cancelText: ''
    });
}

function showErrorModal(title, message) {
    return showConfirmModal({
        title,
        message,
        type: 'danger',
        okText: 'Đóng',
        cancelText: ''
    });
}

authBtn.onclick = async () => {
    try {
        authBtn.disabled = true;
        authBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Đang kết nối...';

        // Gọi API login với format=json để kiểm tra xem có cần manual auth không
        const res = await fetch('/api/auth/login?format=json');
        const data = await res.json();

        if (data.needs_manual_auth) {
            const confirmed = await showConfirmModal({
                title: "Yêu cầu xác thực thủ công",
                message: "Server không thể tự mở trình duyệt (Docker/Remote). Hệ thống sẽ mở một tab mới để bạn đăng nhập Google.\n\nSau khi xong, hãy quay lại đây.",
                type: "primary",
                okText: "Mở trang xác thực",
                cancelText: "Đóng"
            });
            if (confirmed) {
                window.open(data.auth_url, '_blank');
            }
        } else {
            // Local mode: redirect trực tiếp
            window.location.href = '/api/auth/login';
        }
    } catch (err) {
        console.error("Auth error:", err);
        // Fallback: redirect trực tiếp nếu fetch lỗi
        window.location.href = '/api/auth/login';
    } finally {
        authBtn.disabled = false;
        authBtn.innerHTML = '<img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="18" height="18" alt="Google"> <span>Kết nối Google</span>';
    }
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
    const uploadToWp = document.getElementById('uploadWpCheck').checked;

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
    formData.append('uploadToWp', uploadToWp);
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

    aiBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Đang suy nghĩ...`;

    try {
        const res = await fetch('/api/v2/ai/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: rawKeys, // Gửi toàn bộ chuỗi (Có thể chứa nhiều key)
                system_prompt: systemPrompt,
                user_prompt: userPrompt
            })
        });

        const data = await res.json();

        if (res.ok) {
            hookInput.value = data.result;
        } else {
            // Xử lý thông báo lỗi dựa trên mã lỗi backend trả về
            let errMsg = data.error || "Không thể tạo nội dung.";
            if (res.status === 429) {
                showErrorModal("Hết hạn mức (429)", "Tất cả API Key bạn cung cấp đều đã hết hạn mức sử dụng (Quota Exceeded). Vui lòng thử lại sau hoặc thêm key mới.");
            } else if (res.status === 503) {
                showErrorModal("Server Bận (503)", "Dịch vụ Gemini đang quá tải. Vui lòng thử lại sau giây lát.");
            } else if (res.status === 403) {
                showErrorModal("Lỗi phân quyền (403)", "API Key không hợp lệ hoặc không có quyền truy cập model này.");
            } else {
                showErrorModal("Lỗi AI", errMsg);
            }
        }
    } catch (err) {
        console.error("AI Error:", err);
        showErrorModal("Lỗi kết nối", "Không thể kết nối tới server AI: " + err.message);
    } finally {
        aiBtn.disabled = false;
        aiBtn.innerHTML = originalText;
    }
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
                if (btn) btn.innerHTML = '<i class="fas fa-sync fa-spin"></i>';
                // Cập nhật progress item nếu có log message mới và khác message cũ
                if (task.message && task.message !== lastMessage) {
                    addProgressItem(`🔄 [Post] ${task.message}`);
                    lastMessage = task.message;
                }
            } else if (task.status === 'success') {
                clearInterval(interval);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-check-circle" style="color: #10b981;"></i>';
                }
                addProgressItem(`✅ [Post] Đăng thành công! (ID: ${task.result?.post_id || task.result?.data?.id || 'N/A'})`);
                alert('🚀 Bài viết đã được đăng thành công!');

                if (sheetName === 'Woocommerce_db') loadWooDb();
                else loadSheetData(sheetName);

                // Reset icon sau 3 giây
                if (btn) setTimeout(() => { btn.innerHTML = originalHtml; }, 3000);
            } else if (task.status === 'error') {
                clearInterval(interval);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                }
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

// --- WOOCOMMERCE FUNCTIONS ---

async function loadWooDb() {
    const tbody = document.getElementById('wooDbBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center"><i class="fas fa-spinner fa-spin"></i> Đang tải dữ liệu...</td></tr>';

    try {
        const res = await fetch('/api/v2/woocommerce/db');
        const data = await res.json();
        currentWooData = data;
        renderWooDb(data);
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--danger)">Lỗi: ${err.message}</td></tr>`;
    }
}

function renderWooDb(data) {
    const tbody = document.getElementById('wooDbBody');
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">Chưa có sản phẩm nào.</td></tr>';
        return;
    }

    tbody.innerHTML = data.map((item, index) => {
        let statusClass = 'status-new';
        if (item.status === 'SUCCESS') statusClass = 'status-success';
        if (item.status === 'ERROR') statusClass = 'status-danger';
        if (item.status === 'PENDING_REVIEW') statusClass = 'status-warning';

        const postStatus = item.post_status || 'publish';
        const postStatusLabel = postStatus === 'draft' ? '<br><small style="color:#fbbf24">(Bản nháp)</small>' : '';

        return `
            <tr>
                <td>${index + 1}</td>
                <td>
                    <div style="font-weight: 500">${item.title}</div>
                    <div style="font-size: 11px; color: var(--text-muted)">${item.wc_id ? 'ID: ' + item.wc_id : 'Source: ' + (item.source_url || 'N/A')}${postStatusLabel}</div>
                </td>
                <td>${item.regular_price}${item.sale_price ? ' <del style="font-size:11px">' + item.sale_price + '</del>' : ''}</td>
                <td>${item.categories || 'N/A'}</td>
                <td><span class="status-badge ${statusClass}">${item.status || 'NEW'}</span></td>
                <td>
                    <div class="action-buttons">
                        ${item.status !== 'SUCCESS' ? `
                            <button class="btn btn-sm btn-primary" onclick="postWooItem(${index})" title="Đăng bài"><i class="fas fa-paper-plane"></i></button>
                            <button class="btn btn-sm btn-warning" onclick="editWooItem(${index})" title="Chỉnh sửa"><i class="fas fa-edit"></i></button>
                            <button class="btn btn-sm btn-danger" onclick="deleteWooItem(${index})" title="Xóa"><i class="fas fa-trash"></i></button>
                        ` : ''}
                        ${item.wc_link ? `<a href="${item.wc_link}" target="_blank" class="btn btn-sm btn-secondary" title="Xem bài viết"><i class="fas fa-external-link-alt"></i></a>` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Edit/Delete Items in Queue
function editWooItem(index) {
    const item = currentWooData[index];
    if (!item) return;

    document.getElementById('editWooIndex').value = index;
    document.getElementById('editWooTitle').value = item.title || "";
    document.getElementById('editWooPrice').value = item.regular_price || "";
    document.getElementById('editWooSalePrice').value = item.sale_price || "";
    document.getElementById('editWooCategories').value = item.categories || "";
    document.getElementById('editWooPostStatus').value = item.post_status || 'publish';
    document.getElementById('editWooDesc').value = item.description || "";
    document.getElementById('editWooShortDesc').value = item.short_description || "";

    // Reset tabs
    switchWooEditTab('editor');

    document.getElementById('editWooModal').classList.add('visible');
}

function switchWooEditTab(tab) {
    const editor = document.getElementById('wooEditorView');
    const preview = document.getElementById('wooPreviewView');
    const tabs = document.querySelectorAll('.woo-edit-tabs .btn-tab');

    if (tab === 'editor') {
        editor.style.display = 'block';
        preview.style.display = 'none';
        tabs[0].classList.add('active');
        tabs[1].classList.remove('active');
    } else {
        editor.style.display = 'none';
        preview.style.display = 'block';
        tabs[0].classList.remove('active');
        tabs[1].classList.add('active');
        preview.innerHTML = document.getElementById('editWooDesc').value;
    }
}

function closeEditWooModal() {
    document.getElementById('editWooModal').classList.remove('visible');
}

async function saveWooItemEdit() {
    const index = parseInt(document.getElementById('editWooIndex').value);
    const newTitle = document.getElementById('editWooTitle').value.trim();
    const newPostStatus = document.getElementById('editWooPostStatus').value;

    if (!newTitle) return showErrorModal("Lỗi", "Tiêu đề không được để trống.");

    try {
        const item = {
            ...currentWooData[index],
            title: newTitle,
            regular_price: document.getElementById('editWooPrice').value.trim(),
            sale_price: document.getElementById('editWooSalePrice').value.trim(),
            categories: document.getElementById('editWooCategories').value.trim(),
            post_status: newPostStatus,
            description: document.getElementById('editWooDesc').value,
            short_description: document.getElementById('editWooShortDesc').value,
            status: "NEW" // Chuyển về NEW sau khi đã kiểm duyệt xong
        };
        const res = await fetch('/api/v2/woocommerce/update-item', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: index, data: item })
        });

        if (res.ok) {
            showSuccessModal("Thành công", "Đã cập nhật thông tin sản phẩm.");
            closeEditWooModal();
            loadWooDb();
        } else {
            const err = await res.json();
            showErrorModal("Lỗi", err.error);
        }
    } catch (err) {
        showErrorModal("Lỗi kết nối", err.message);
    }
}

async function deleteWooItem(index) {
    if (await showConfirmModal("Xác nhận xóa", `Bạn có chắc chắn muốn xóa sản phẩm "${currentWooData[index].title}" khỏi hàng đợi?`)) {
        try {
            const res = await fetch('/api/v2/woocommerce/delete-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: index })
            });

            if (res.ok) {
                showSuccessModal("Đã xóa", "Sản phẩm đã được gỡ khỏi hàng đợi.");
                loadWooDb();
            } else {
                const err = await res.json();
                showErrorModal("Lỗi", err.error);
            }
        } catch (err) {
            showErrorModal("Lỗi kết nối", err.message);
        }
    }
}

async function postWooItem(index) {
    if (!await showConfirmModal("Đăng sản phẩm lên WooCommerce?", "Bạn có chắc chắn muốn đăng sản phẩm này ngay bây giờ?")) return;

    try {
        showSuccessModal("Đang xử lý...", "Đang kết nối và đăng sản phẩm lên WooCommerce. Vui lòng đợi.");
        const res = await fetch('/api/v2/post/publish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sheet_name: 'Woocommerce_db', index: index })
        });
        const result = await res.json();

        if (result.task_id) {
            // Sử dụng logic polling giống publishPost
            addProgressItem(`🕒 [Task] Đang đăng WooCommerce (ID: ${result.task_id.substring(0, 8)}...)`);

            // Tìm nút nếu có thể, hoặc truyền null
            startTaskPolling(result.task_id, null, "", "Woocommerce_db");

            // Thông báo bắt đầu thành công
            showSuccessModal("Đã bắt đầu!", "Yêu cầu đăng sản phẩm đã được gửi. Bạn có thể theo dõi tiến độ ở góc phải màn hình.");
        } else if (result.success) {
            // Fallback nếu server trả về success đồng bộ
            showSuccessModal("Thành công!", "Sản phẩm đã được đăng lên WooCommerce.");
            loadWooDb();
        } else {
            showErrorModal("Lỗi đăng bài", result.error || "Không rõ nguyên nhân.");
        }
    } catch (err) {
        showErrorModal("Lỗi kết nối", err.message);
    }
}

// Config Modal
function openWooConfig() {
    console.log("Opening WooCommerce Config Modal...");
    const modal = document.getElementById('wooConfigModal');
    if (modal) {
        modal.classList.add('visible');
        loadWooConfig();
    } else {
        console.error("Critical: #wooConfigModal element not found!");
    }
}

function closeWooConfig() {
    document.getElementById('wooConfigModal').classList.remove('visible');
}

async function loadWooConfig() {
    try {
        const res = await fetch('/api/v2/woocommerce/config');
        const config = await res.json();
        document.getElementById('wc_url').value = config.site_url || "";
        document.getElementById('wc_key').value = config.consumer_key || "";
        document.getElementById('wc_secret').value = config.consumer_secret || "";
        document.getElementById('wp_user').value = config.wp_user || "";
        document.getElementById('wp_app_pass').value = config.wp_app_pass || "";
    } catch (err) {
        console.error("Lỗi load config WC:", err);
    }
}

async function saveWooConfig() {
    const data = {
        site_url: document.getElementById('wc_url').value.trim(),
        consumer_key: document.getElementById('wc_key').value.trim(),
        consumer_secret: document.getElementById('wc_secret').value.trim(),
        wp_user: document.getElementById('wp_user').value.trim(),
        wp_app_pass: document.getElementById('wp_app_pass').value.trim()
    };

    try {
        const res = await fetch('/api/v2/woocommerce/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.success) {
            showSuccessModal("Lưu thành công", "Cấu hình WooCommerce đã được cập nhật.");
            closeWooConfig();
        } else {
            showErrorModal("Lỗi lưu cấu hình", result.error);
        }
    } catch (err) {
        showErrorModal("Lỗi kết nối", err.message);
    }
}

// Analyze Tool
async function analyzeWooUrl() {
    const urlInput = document.getElementById('wooAnalyzeUrl');
    const youtubeInput = document.getElementById('wooYoutubeUrl');
    const fileInput = document.getElementById('wooImageFiles');

    const url = urlInput.value.trim();
    const youtubeUrl = youtubeInput.value.trim();
    const apiKey = localStorage.getItem('geminiApiKey');
    const systemPrompt = localStorage.getItem('wooGeminiSystemPrompt');

    if (!url) return showErrorModal("Thiếu thông tin", "Vui lòng nhập URL sản phẩm.");
    if (!apiKey) return showErrorModal("Thiếu API Key", "Vui lòng cấu hình Gemini API Key trong phần Cấu hình chung.");

    const analyzeBtn = document.querySelector('button[onclick="analyzeWooUrl()"]');
    const originalBtnHtml = analyzeBtn.innerHTML;

    try {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Đang phân tích...';

        showSuccessModal("Đang phân tích...", "AI đang cào dữ liệu và viết lại nội dung chuẩn SEO. Có thể mất 15-45 giây.");

        const res = await fetch('/api/v2/woocommerce/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                api_key: apiKey.trim(),
                system_prompt: systemPrompt,
                youtube_url: youtubeUrl
            })
        });

        const data = await res.json();

        if (!res.ok || data.error) {
            showErrorModal("Lỗi phân tích", data.error || "Không thể phân tích URL này.");
            return;
        }

        // Hiển thị kết quả AI và hỏi có muốn thêm vào DB không
        const imagesHtml = (data.images || "").split(',')
            .filter(u => u.trim())
            .map(u => `<img src="${u.trim()}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1)">`)
            .join('');

        // Lấy mã nhúng YouTube nếu có trong description
        let youtubePreviewHtml = '';
        if (data.description) {
            // Trường hợp 1: Mã nhúng cũ (iframe trong div)
            const iframeMatch = data.description.match(/<div class="video-container".*?<\/div>/s);
            if (iframeMatch) {
                youtubePreviewHtml = `<div style="margin-top: 15px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1)">
                    <p style="padding: 5px 10px; background: rgba(255,255,255,0.05); font-size: 11px; margin: 0; opacity: 0.7">Youtube Video Preview</p>
                    ${iframeMatch[0]}
                </div>`;
            } else {
                // Trường hợp 2: URL thuần (mới) - Tìm link youtube để tạo preview
                const ytUrlMatch = data.description.match(/https:\/\/www\.youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/);
                if (ytUrlMatch) {
                    const videoId = ytUrlMatch[1];
                    youtubePreviewHtml = `<div style="margin-top: 15px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1)">
                        <p style="padding: 5px 10px; background: rgba(255,255,255,0.05); font-size: 11px; margin: 0; opacity: 0.7">Youtube Video Preview</p>
                        <div style="text-align:center;"><iframe width="100%" height="200" src="https://www.youtube.com/embed/${videoId}" frameborder="0" allowfullscreen></iframe></div>
                    </div>`;
                }
            }
        }

        const previewHtml = `
            <div style="text-align: left; background: rgba(0,0,0,0.2); padding: 15px; border-radius: 12px; font-size: 13px; color: #e0e0e0; line-height: 1.6">
                <div style="margin-bottom: 10px; font-weight: 600; color: var(--accent); font-size: 14px">${data.title}</div>
                <div style="margin-bottom: 10px; display: flex; gap: 8px; flex-wrap: wrap">${imagesHtml}</div>
                ${youtubePreviewHtml}
                <div style="margin-top: 10px; margin-bottom: 5px"><b>Giá:</b> ${data.regular_price} ${data.sale_price ? `<del style="opacity: 0.5; margin-left: 5px">${data.sale_price}</del>` : ''}</div>
                <div style="margin-bottom: 5px"><b>Danh mục:</b> ${data.categories || 'Tự động'}</div>
                <div style="opacity: 0.8; font-style: italic; margin-bottom: 15px">${data.short_description}</div>
                
                <div class="input-group" style="margin-top: 10px; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px">
                    <label style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.7">Chế độ đăng bài</label>
                    <select id="confirmPostStatus" class="card-select" style="margin-top: 5px; background: rgba(0,0,0,0.3)">
                        <option value="publish">Public (Công khai)</option>
                        <option value="draft">Draft (Bản nháp)</option>
                    </select>
                </div>
            </div>
        `;

        if (await showConfirmModal("Kết quả AI Phân tích", previewHtml + "<br>Bạn có muốn thêm sản phẩm này vào hàng đợi đăng bài không?")) {
            const selectedStatus = document.getElementById('confirmPostStatus').value;

            // Sử dụng FormData để gửi kèm file ảnh lên Drive
            const formData = new FormData();
            formData.append('title', data.title);
            formData.append('regular_price', data.regular_price);
            formData.append('sale_price', data.sale_price || '');
            formData.append('description', data.description);
            formData.append('short_description', data.short_description);
            formData.append('categories', data.categories || '');
            formData.append('images', data.images || '');
            formData.append('source_url', url);
            formData.append('post_status', selectedStatus); // Gửi trạng thái đã chọn
            formData.append('parent_folder_id', localStorage.getItem('parentFolderId') || 'root');

            // Đính kèm các file ảnh từ input
            if (fileInput.files.length > 0) {
                for (let i = 0; i < fileInput.files.length; i++) {
                    formData.append('image_files', fileInput.files[i]);
                }
            }

            const addRes = await fetch('/api/v2/woocommerce/add-item', {
                method: 'POST',
                body: formData // Không set header Content-Type, trình duyệt tự xử lý cho FormData
            });

            if (addRes.ok) {
                showSuccessModal("Hoàn tất", "Sản phẩm đã được thêm vào Woocommerce_db.");
                urlInput.value = ''; // Clear input
                youtubeInput.value = '';
                fileInput.value = '';
                loadWooDb();
            } else {
                const addErr = await addRes.json();
                showErrorModal("Lỗi thêm sản phẩm", addErr.error);
            }
        }
    } catch (err) {
        console.error("Analyze Error:", err);
        showErrorModal("Lỗi kết nối", "Không thể kết nối tới server: " + err.message);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = originalBtnHtml;
    }
}

// CSV Upload
async function handleWooCsv(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        showSuccessModal("Đang xử lý CSV...", "Hệ thống đang import dữ liệu vào Google Sheets.");
        const res = await fetch('/api/v2/woocommerce/import-csv', {
            method: 'POST',
            body: formData
        });
        const result = await res.json();
        if (result.success) {
            showSuccessModal("Thành công!", `Đã import ${result.imported} sản phẩm từ file CSV.`);
            loadWooDb();
        } else {
            showErrorModal("Lỗi Import", result.error);
        }
    } catch (err) {
        showErrorModal("Lỗi kết nối", err.message);
    }
    // Reset input
    event.target.value = '';
}

async function handleBulkAnalyzeCsv(event) {
    const file = event.target.files[0];
    if (!file) return;

    const apiKey = localStorage.getItem('geminiApiKey');
    if (!apiKey) return showErrorModal("Thiếu thông tin", "Vui lòng cấu hình Gemini API Key.");

    const formData = new FormData();
    formData.append('file', file);
    formData.append('api_key', apiKey.trim());
    formData.append('system_prompt', localStorage.getItem('wooGeminiSystemPrompt') || '');

    try {
        showSuccessModal("Đã bắt đầu", "Hệ thống đang bắt đầu phân tích hàng loạt. Các bài viết sẽ xuất hiện dần trong danh sách.");
        const res = await fetch('/api/v2/woocommerce/bulk-analyze', {
            method: 'POST',
            body: formData
        });
        const result = await res.json();
        if (result.success) {
            startBulkPolling(result.task_id);
        } else {
            showErrorModal("Lỗi", result.error);
        }
    } catch (err) {
        showErrorModal("Lỗi kết nối", err.message);
    }
    event.target.value = '';
}

function startBulkPolling(taskId) {
    const statusDiv = document.getElementById('bulkAnalyzeStatus');
    const progressBar = document.getElementById('bulkAnalyzeProgress');
    statusDiv.style.display = 'block';

    const interval = setInterval(async () => {
        try {
            const res = await fetch('/api/tasks');
            const tasks = await res.json();
            const task = tasks[taskId];

            if (!task) return;

            // Refresh table real-time to show new items
            loadWooDb();

            if (task.status === 'processing') {
                // Ta không có tổng số ở đây từ backend dễ dàng, nhưng có thể update message
                if (task.message) {
                    addProgressItem(`🤖 [Bulk] ${task.message}`);
                }
            } else if (task.status === 'success') {
                clearInterval(interval);
                statusDiv.style.display = 'none';
                showSuccessModal("Hoàn tất", "Phân tích hàng loạt đã xong!");
            } else if (task.status === 'error') {
                clearInterval(interval);
                statusDiv.style.display = 'none';
                showErrorModal("Lỗi phân tích hàng loạt", task.message);
            }
        } catch (e) { console.error(e); }
    }, 5000);
}

// --- HELPER WRAPPER ---
function loadPublishedHistory() {
    console.log("Reloading Published History...");
    loadSheetData('Published_History');
}
