
file_path = 'Fontend/js/script.js'

js_content = """
// --- HARAVAN ADVANCED LOGIC ---
let haravanMetadata = { types: [], vendors: [], collections: [] };

async function fetchHaravanMetadata() {
    try {
        const [metaRes, colRes] = await Promise.all([
            fetch('/api/v2/haravan/metadata'),
            fetch('/api/v2/haravan/collections')
        ]);
        
        if (metaRes.ok) {
            const meta = await metaRes.json();
            if (meta.success) {
                haravanMetadata.types = meta.types;
                haravanMetadata.vendors = meta.vendors;
            }
        }
        
        if (colRes.ok) {
            const col = await colRes.json();
            if (col.success) {
                haravanMetadata.collections = col.collections;
            }
        }
        console.log('Haravan Metadata Loaded:', haravanMetadata);
    } catch (e) {
        console.warn('Failed to load Haravan metadata', e);
    }
}

// Override loadHaravanDb
// const originalLoadHaravanDb = loadHaravanDb; // No need generic override if we replace the function
// But loadHaravanDb is defined in global scope or as function declaration.
// We can redefine it.

loadHaravanDb = async function() {
    // Call metadata first if empty
    if(haravanMetadata.types.length === 0) fetchHaravanMetadata();
    
    const container = document.getElementById('haravanDbBody');
    if (!container) return;
    container.innerHTML = '<tr><td colspan="6" style="text-align:center"><i class="fas fa-circle-notch fa-spin"></i> Đang tải dữ liệu...</td></tr>';

    try {
        const res = await fetch('/api/v2/sheets/Haravan_db');
        const data = await res.json();
        currentHaravanData = data;
        renderHaravanTable(data);
    } catch (err) {
        container.innerHTML = `<tr><td colspan="6" style="color:red; text-align:center">Lỗi tải dữ liệu: ${err.message}</td></tr>`;
    }
};

function renderHaravanTable(data) {
    const container = document.getElementById('haravanDbBody');
    if (!data || data.length === 0) {
        container.innerHTML = '<tr><td colspan="6" style="text-align:center">Chưa có dữ liệu.</td></tr>';
        return;
    }

    container.innerHTML = data.map((item, index) => {
        let statusClass = 'secondary';
        let statusText = item.status || 'PENDING';
        if (statusText === 'SUCCESS') statusClass = 'success';
        if (statusText === 'ERROR') statusClass = 'danger';

        const sourceLink = item.source_url || '';
        const sourceDisplay = sourceLink ? `<div style="font-size: 11px; color: var(--text-muted); max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"><a href="${sourceLink}" target="_blank" style="color: var(--primary); text-decoration: none;"><i class="fas fa-link"></i> ${sourceLink}</a></div>` : '';

        return `
            <tr>
                <td>${item.stt || (index + 1)}</td>
                <td>
                    <div style="font-weight: 500">${item.product_title || 'No Title'}</div>
                    ${sourceDisplay}
                </td>
                <td>${item.regular_price || 0}</td>
                <td>${item.product_type || '-'}</td>
                <td><span class="badge badge-${statusClass}">${statusText}</span></td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-primary" onclick="publishHaravanItem(${index})" title="Đăng bài"><i class="fas fa-paper-plane"></i></button>
                        <button class="btn btn-sm btn-warning" onclick="openEditHaravanModal(${index})" title="Chỉnh sửa"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-danger" onclick="deleteHaravanItem(${index})" title="Xóa"><i class="fas fa-trash"></i></button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openEditHaravanModal(index) {
    const item = currentHaravanData[index];
    if (!item) return;

    document.getElementById('editHrvIndex').value = index;
    document.getElementById('editHrvTitle').value = item.product_title || '';
    document.getElementById('editHrvPrice').value = item.regular_price || '';
    document.getElementById('editHrvSalePrice').value = item.sale_price || '';
    document.getElementById('editHrvType').value = item.product_type || '';
    document.getElementById('editHrvVendor').value = item.vendor || '';
    document.getElementById('editHrvTags').value = item.tags || '';
    document.getElementById('editHrvDesc').value = item.description_html || '';

    // Populate Datalists
    const typeList = document.getElementById('hrvTypeList');
    if(typeList) typeList.innerHTML = haravanMetadata.types.map(t => `<option value="${t}">`).join('');
    
    const vendorList = document.getElementById('hrvVendorList');
    if(vendorList) vendorList.innerHTML = haravanMetadata.vendors.map(v => `<option value="${v}">`).join('');

    // Populate Collections
    const colSelect = document.getElementById('editHrvCollection');
    if(colSelect) {
        colSelect.innerHTML = '<option value="">-- Chọn nhóm sản phẩm --</option>' + 
            haravanMetadata.collections.map(c => `<option value="${c.id}">${c.title}</option>`).join('');
    }

    document.getElementById('editHaravanModal').classList.add('visible');
}

function closeEditHaravanModal() {
    document.getElementById('editHaravanModal').classList.remove('visible');
}

async function saveHaravanItemEdit() {
    const index = document.getElementById('editHrvIndex').value;
    const item = currentHaravanData[index];
    
    // Update basic fields
    item.product_title = document.getElementById('editHrvTitle').value;
    item.regular_price = document.getElementById('editHrvPrice').value;
    item.sale_price = document.getElementById('editHrvSalePrice').value;
    item.product_type = document.getElementById('editHrvType').value;
    item.vendor = document.getElementById('editHrvVendor').value;
    item.tags = document.getElementById('editHrvTags').value;
    item.description_html = document.getElementById('editHrvDesc').value;
    
    // Check custom collections
    const colSelect = document.getElementById('editHrvCollection');
    if(colSelect && colSelect.value) {
        item._collection_id = colSelect.value;
    }

    // Handle Image Upload (Preview)
    const fileInput = document.getElementById('editHrvImageUpload');
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const reader = new FileReader();
        reader.onload = async function(e) {
            item._base64_image = e.target.result.split(',')[1];
            item._image_filename = file.name;
            await commitHaravanSave(index, item);
        };
        reader.readAsDataURL(file);
    } else {
        await commitHaravanSave(index, item);
    }
}

async function commitHaravanSave(index, item) {
    try {
        const res = await fetch(`/api/v2/sheets/Haravan_db/${index}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item)
        });
        if (res.ok) {
            alert('Đã lưu thay đổi!');
            closeEditHaravanModal();
            loadHaravanDb();
        } else {
            alert('Lỗi khi lưu.');
        }
    } catch (e) {
        alert('Lỗi kết nối: ' + e.message);
    }
}

async function analyzeHaravanUrl() {
    const url = document.getElementById('hrvAnalyzeUrl').value;
    if (!url) return alert('Vui lòng nhập Link sản phẩm!');
    
    const btn = document.querySelector('#haravan-view .btn-primary');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang phân tích...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/v2/ai/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                api_key: localStorage.getItem('geminiApiKey'),
                system_prompt: "You are a Haravan/Shopify Product Expert. Extract product info from user URL (simulate extraction or infer from URL structure if possible) and format as JSON: {title, price, description, vendor, type, tags}. Return ONLY JSON.",
                user_prompt: `Analyze this product URL: ${url}. Provide the JSON data.`
            })
        });
        
        const data = await res.json();
        if (data.result) {
            try {
                const jsonStr = data.result.replace(/```json/g, '').replace(/```/g, '').trim();
                const product = JSON.parse(jsonStr);
                
                const newItem = {
                    stt: currentHaravanData.length + 1,
                    product_title: product.title || 'Draft Product',
                    regular_price: product.price ? product.price.toString().replace(/[^0-9]/g, '') : '0',
                    product_type: product.type || '',
                    vendor: product.vendor || '',
                    tags: product.tags || '',
                    description_html: product.description || '',
                    source_url: url,
                    status: 'PENDING'
                };
                
                await fetch('/api/v2/sheets/Haravan_db', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(newItem)
                });
                
                alert('Phân tích và thêm thành công!');
                loadHaravanDb();
            } catch (parseErr) {
                alert('AI trả về dữ liệu không đúng định dạng JSON.');
                console.error(data.result);
            }
        } else {
            alert('Lỗi AI: ' + data.error);
        }
    } catch (e) {
        alert('Lỗi hệ thống: ' + e.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function handleHaravanCsv(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async function(e) {
        const text = e.target.result;
        const lines = text.split('\\n').filter(line => line.trim() !== '');
        
        let count = 0;
        // Skip header row 0
        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            if (cols.length < 2) continue;
            
            const newItem = {
                stt: currentHaravanData.length + 1 + count,
                product_title: cols[0] || 'Imported Product',
                regular_price: cols[1] || '0',
                status: 'PENDING'
            };
             await fetch('/api/v2/sheets/Haravan_db', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(newItem)
            });
            count++;
        }
        alert(`Đã import ${count} sản phẩm!`);
        loadHaravanDb();
    };
    reader.readAsText(file);
}
"""

with open(file_path, "a") as f:
    f.write(js_content)
