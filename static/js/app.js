/* ── Navigation ─────────────────────────────────────────────── */
const pages   = document.querySelectorAll('.page');
const navBtns = document.querySelectorAll('.nav-btn');

navBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.page;
    pages.forEach(p => p.classList.toggle('active', p.id === `page-${target}`));
    navBtns.forEach(b => b.classList.toggle('active', b === btn));
    if (target === 'gallery') loadGallery();
  });
});

/* ── Stats ──────────────────────────────────────────────────── */
async function loadStats() {
  const res = await fetch('/api/stats');
  const data = await res.json();
  document.getElementById('stat-images').textContent  = data.total_images  ?? '—';
  document.getElementById('stat-vectors').textContent = data.indexed_vectors ?? '—';
}
loadStats();

/* ── Toast ──────────────────────────────────────────────────── */
let toastTimer;
function showToast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 3200);
}

/* ── Loader helper ──────────────────────────────────────────── */
function makeLoader(text = 'Processing…') {
  const d = document.createElement('div');
  d.className = 'loader';
  d.innerHTML = `<div class="spinner"></div><span>${text}</span>`;
  return d;
}

/* ════════════════════════════════════════════════════════════
   UPLOAD
════════════════════════════════════════════════════════════ */
const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('file-input');
const uploadQueue = document.getElementById('upload-queue');
const uploadBtn  = document.getElementById('upload-btn');
const uploadResults = document.getElementById('upload-results');

let selectedFiles = [];

function refreshQueue() {
  uploadQueue.innerHTML = '';
  if (!selectedFiles.length) { uploadQueue.classList.add('hidden'); uploadBtn.disabled = true; return; }
  uploadQueue.classList.remove('hidden');
  uploadBtn.disabled = false;

  selectedFiles.forEach((f, i) => {
    const div = document.createElement('div');
    div.className = 'queue-thumb';
    const mediaType = getMediaType(f.name);
    const url = URL.createObjectURL(f);
    
    if (mediaType === 'image') {
      div.innerHTML = `<img src="${url}" /><span class="q-name">${f.name}</span>
        <button class="q-remove" data-i="${i}">✕</button>`;
    } else if (mediaType === 'video') {
      div.innerHTML = `<video src="${url}" muted playsinline></video><span class="q-type">🎬</span><span class="q-name">${f.name}</span>
        <button class="q-remove" data-i="${i}">✕</button>`;
    } else if (mediaType === 'audio') {
      div.innerHTML = `<div class="audio-preview">🎵</div><span class="q-name">${f.name}</span>
        <button class="q-remove" data-i="${i}">✕</button>`;
    } else if (mediaType === 'pdf') {
      div.innerHTML = `<div class="pdf-preview">📄 PDF</div><span class="q-name">${f.name}</span>
        <button class="q-remove" data-i="${i}">✕</button>`;
    } else {
      div.innerHTML = `<div class="file-icon">📝</div><span class="q-name">${f.name}</span>
        <button class="q-remove" data-i="${i}">✕</button>`;
    }
    uploadQueue.appendChild(div);
  });

  uploadQueue.querySelectorAll('.q-remove').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      selectedFiles.splice(+btn.dataset.i, 1);
      refreshQueue();
    });
  });
}

// All supported media types per Gemini Embedding model
const ALLOWED_EXTS = [
  // Images
  'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp',
  // Videos (up to 120 seconds)
  'mp4', 'mov', 'avi', 'mkv', 'webm',
  // Audio
  'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac',
  // Documents
  'pdf', 'txt', 'md', 'json', 'csv'
];

const MEDIA_ICONS = {
  image: '🖼️',
  video: '🎬',
  audio: '🎵',
  pdf: '📄',
  text: '📝'
};

function getMediaType(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const images = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'];
  const videos = ['mp4', 'mov', 'avi', 'mkv', 'webm'];
  const audio = ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac'];
  const text = ['txt', 'md', 'json', 'csv'];
  
  if (images.includes(ext)) return 'image';
  if (videos.includes(ext)) return 'video';
  if (audio.includes(ext)) return 'audio';
  if (ext === 'pdf') return 'pdf';
  if (text.includes(ext)) return 'text';
  return 'unknown';
}

function addFiles(files) {
  [...files].forEach(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (ALLOWED_EXTS.includes(ext)) {
      selectedFiles.push(f);
    }
  });
  refreshQueue();
}

dropZone.addEventListener('click', e => {
  // Don't re-trigger if the click came from the label or the input itself
  if (e.target.tagName === 'LABEL' || e.target.tagName === 'INPUT') return;
  fileInput.click();
});
fileInput.addEventListener('change', e => { addFiles(e.target.files); fileInput.value = ''; });

dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  addFiles(e.dataTransfer.files);
});

uploadBtn.addEventListener('click', async () => {
  if (!selectedFiles.length) return;
  uploadBtn.disabled = true;
  uploadResults.innerHTML = '';
  const totalFiles = selectedFiles.length;
  const loader = makeLoader(`Indexing ${totalFiles} file(s) with Gemini Embedding 2…`);
  uploadResults.appendChild(loader);

  const form = new FormData();
  selectedFiles.forEach(f => form.append('files', f));

  try {
    const res  = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    loader.remove();

    // Only successful uploads are returned - failures are silently skipped
    const successful = data.results || [];
    const failedCount = totalFiles - successful.length;

    successful.forEach(r => {
      const card = document.createElement('div');
      card.className = 'upload-card';
      const mediaType = r.media_type || 'file';
      const icon = MEDIA_ICONS[mediaType] || '📎';
      
      let previewHTML = '';
      if (mediaType === 'image') {
        previewHTML = `<img src="${r.url}" alt="${r.name}" />`;
      } else if (mediaType === 'video') {
        previewHTML = `<video src="${r.url}" controls muted playsinline preload="metadata"></video>`;
      } else if (mediaType === 'audio') {
        previewHTML = `<audio src="${r.url}" controls preload="metadata"></audio>`;
      } else if (mediaType === 'pdf') {
        previewHTML = `<iframe src="${r.url}#page=1&view=FitH" title="${r.name}"></iframe>`;
      } else {
        previewHTML = `<div class="upload-card-preview">${icon}</div>`;
      }
      
      card.innerHTML = `
        ${previewHTML}
        <div class="upload-card-body">
          <div class="upload-ok">✓ ${icon} ${mediaType.toUpperCase()} Indexed</div>
          <div class="fname">${r.name}</div>
          <div class="caption">${r.caption || ''}</div>
        </div>`;
      uploadResults.appendChild(card);
    });

    // Show summary message
    if (successful.length > 0 && failedCount > 0) {
      showToast(`${successful.length} indexed, ${failedCount} skipped`, 'success');
    } else if (successful.length > 0) {
      showToast(`${successful.length} file(s) indexed`, 'success');
    } else {
      showToast('No files could be processed', 'error');
    }
    
    selectedFiles = []; refreshQueue();
    loadStats();
  } catch(e) {
    loader.remove();
    showToast('Upload failed: ' + e.message, 'error');
    uploadBtn.disabled = false;
  }
});

/* ════════════════════════════════════════════════════════════
   SEARCH — Tabs
════════════════════════════════════════════════════════════ */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === target));
  });
});

/* ── Text Search ────────────────────────────────────────────── */
const textQueryInput = document.getElementById('text-query');
const textSearchBtn  = document.getElementById('text-search-btn');
const textResults    = document.getElementById('text-results');

async function doTextSearch() {
  const query = textQueryInput.value.trim();
  if (!query) return;
  textResults.innerHTML = '';
  const loader = makeLoader('Searching…');
  textResults.appendChild(loader);
  
  // Hide network container
  document.getElementById('search-network-container').classList.add('hidden');

  try {
    const res = await fetch('/api/search/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: 20, min_score: 0.10 }),
    });
    
    // Check if response is OK
    if (!res.ok) {
      const text = await res.text();
      console.error('[Search Error] Status:', res.status, 'Response:', text);
      throw new Error(`Server error: ${res.status}`);
    }
    
    // Try to parse JSON
    let data;
    try {
      data = await res.json();
    } catch (parseErr) {
      const text = await res.text();
      console.error('[Search Error] JSON parse failed. Response:', text);
      throw new Error('Invalid response from server');
    }
    
    loader.remove();
    
    // Check for API errors
    if (data.error) {
      showToast('Error: ' + data.error, 'error');
      return;
    }
    
    // Sort by score descending and show top results
    const sortedResults = (data.results || [])
      .sort((a, b) => b.score - a.score)
      .slice(0, 12);
    
    renderResults(textResults, sortedResults);
    
    // Show network with query node
    if (sortedResults.length > 0) {
      const networkData = buildSearchNetworkFromResults(sortedResults);
      renderSearchNetwork(networkData, { name: query });
    }
  } catch(e) {
    loader.remove();
    console.error('[doTextSearch] Error:', e);
    showToast('Search failed: ' + e.message, 'error');
  }
}

// Build network data from search results
function buildSearchNetworkFromResults(results) {
  const nodes = results.map((r, i) => ({
    id: r.image_id,
    name: r.original_name,
    url: r.url,
    caption: r.caption,
    score: r.score,
    width: r.width,
    height: r.height,
    is_result: true
  }));
  
  // Build edges based on score similarity
  const edges = [];
  for (let i = 0; i < results.length; i++) {
    for (let j = i + 1; j < results.length; j++) {
      const scoreDiff = Math.abs(results[i].score - results[j].score);
      if (scoreDiff < 20) {  // Connect if scores are close
        edges.push({
          source: results[i].image_id,
          target: results[j].image_id,
          similarity: (Math.min(results[i].score, results[j].score) / 100)
        });
      }
    }
  }
  
  return { nodes, edges };
}

textSearchBtn.addEventListener('click', doTextSearch);
textQueryInput.addEventListener('keydown', e => { if (e.key === 'Enter') doTextSearch(); });

/* ── Image Search ───────────────────────────────────────────── */
const imgQueryZone    = document.getElementById('img-query-zone');
const imgQueryInput   = document.getElementById('img-query-input');
const imgQueryPreview = document.getElementById('img-query-preview');
const imgPlaceholder  = document.getElementById('img-query-placeholder');
const imgSearchBtn    = document.getElementById('img-search-btn');
const imgResults      = document.getElementById('img-results');
let queryImageFile = null;

imgQueryZone.addEventListener('click',   () => imgQueryInput.click());
imgQueryZone.addEventListener('dragover', e => { e.preventDefault(); imgQueryZone.style.borderColor = 'var(--accent)'; });
imgQueryZone.addEventListener('dragleave', () => imgQueryZone.style.borderColor = '');
imgQueryZone.addEventListener('drop', e => {
  e.preventDefault(); imgQueryZone.style.borderColor = '';
  const f = e.dataTransfer.files[0];
  if (f) setQueryImage(f);
});
imgQueryInput.addEventListener('change', e => { if (e.target.files[0]) setQueryImage(e.target.files[0]); });

function setQueryImage(file) {
  queryImageFile = file;
  imgQueryPreview.src = URL.createObjectURL(file);
  imgQueryPreview.classList.remove('hidden');
  imgPlaceholder.classList.add('hidden');
  imgSearchBtn.disabled = false;
}

imgSearchBtn.addEventListener('click', async () => {
  if (!queryImageFile) return;
  imgResults.innerHTML = '';
  const loader = makeLoader('Finding similar images…');
  imgResults.appendChild(loader);
  
  // Hide network container
  document.getElementById('search-network-container').classList.add('hidden');

  const form = new FormData();
  form.append('image', queryImageFile);
  form.append('top_k', 10);

  try {
    const res  = await fetch('/api/search/image', { method: 'POST', body: form });
    const data = await res.json();
    loader.remove();
    renderResults(imgResults, data.results || []);
    
    // Show network with query as center node
    if (data.results && data.results.length > 0) {
      const networkData = buildSearchNetworkFromResults(data.results);
      renderSearchNetwork(networkData, { name: 'Query Image' });
    }
  } catch(e) {
    loader.remove();
    showToast('Search failed: ' + e.message, 'error');
  }
});

/* ── Render result cards ────────────────────────────────────── */
function renderResults(container, results) {
  container.innerHTML = '';
  if (!results.length) {
    container.innerHTML = '<p style="color:var(--text-dim);padding:20px 0">No matching files found. Try a different query.</p>';
    return;
  }
  results.forEach(r => {
    const mediaType = r.media_type || 'image';
    const icon = MEDIA_ICONS[mediaType] || '📎';
    
    const card = document.createElement('div');
    card.className = 'result-card';
    
    // Build preview based on media type - use <a> tag for videos/PDFs
    let previewHTML;
    if (mediaType === 'image') {
      previewHTML = `<img src="${r.url}" alt="${r.original_name}" loading="lazy" />`;
    } else if (mediaType === 'video') {
      previewHTML = `
        <a href="${r.url}" target="_blank" class="result-media-link" title="Click to open video">
          <video src="${r.url}" muted playsinline preload="metadata"></video>
          <div class="result-media-overlay"><span>▶</span></div>
        </a>`;
    } else if (mediaType === 'audio') {
      previewHTML = `<div class="result-card-media"><span>🎵</span><small>Audio</small></div>`;
    } else if (mediaType === 'pdf') {
      previewHTML = `
        <a href="${r.url}" target="_blank" class="result-media-link" title="Click to open PDF">
          <div class="result-card-media"><span>📄</span><small>PDF</small></div>
          <div class="result-media-overlay"><span>↗</span></div>
        </a>`;
    } else {
      previewHTML = `<div class="result-card-icon">${icon}</div>`;
    }
    
    card.innerHTML = `
      ${previewHTML}
      <div class="result-card-body">
        <div class="r-name">${icon} ${r.original_name}</div>
        <span class="r-score">${r.score}% match</span>
      </div>`;
    
    if (mediaType === 'image') {
      card.addEventListener('click', () => openLightbox(r));
    }
    container.appendChild(card);
  });
}

/* ── Render search network ─────────────────────────────────── */
let searchGraphInstance = null;

function renderSearchNetwork(networkData, queryNode = null) {
  const container = document.getElementById('search-network-graph');
  const containerWrapper = document.getElementById('search-network-container');
  
  if (!container) return;
  
  container.innerHTML = '';
  
  if (!networkData.nodes.length) {
    containerWrapper.classList.add('hidden');
    return;
  }
  
  containerWrapper.classList.remove('hidden');
  
  if (typeof ForceGraph3D === 'undefined' || typeof THREE === 'undefined') {
    container.innerHTML = '<p style="padding:20px;color:var(--text-dim)">3D library not loaded</p>';
    return;
  }
  
  try {
    // Add query node as the center if provided
    let nodes = networkData.nodes.map((n, i) => ({
      ...n,
      val: n.score ? (n.score / 10) : 5,  // Size based on match score
      color: i === 0 ? '#f5a623' : (n.score > 70 ? '#4caf7d' : (n.score > 50 ? '#5b6ef5' : '#9c27b0'))
    }));
    
    // If we have a query node, add it and connect to all results
    let links = [...networkData.edges];
    if (queryNode) {
      const queryId = '_query_';
      nodes.unshift({
        id: queryId,
        name: 'Query',
        val: 12,  // Biggest node
        color: '#f05454',  // Red for query
        isQuery: true
      });
      
      // Connect query to all result nodes
      nodes.slice(1).forEach(n => {
        links.push({
          source: queryId,
          target: n.id,
          similarity: (n.score || 50) / 100
        });
      });
    }
    
    const data = { nodes, links };
    
    searchGraphInstance = ForceGraph3D({ controlType: 'orbit' })(container)
      .graphData(data)
      .backgroundColor('#0f1117')
      .showNavInfo(false)
      .width(container.clientWidth)
      .height(400);
    
    // Node with thumbnail image
    searchGraphInstance.nodeThreeObject(node => {
      const group = new THREE.Group();
      const size = node.val || 5;
      const color = node.color || '#5b6ef5';
      
      if (node.isQuery) {
        // Query node - big sphere with label
        const sphere = new THREE.Mesh(
          new THREE.SphereGeometry(size, 16, 16),
          new THREE.MeshBasicMaterial({ 
            color: new THREE.Color(color), 
            transparent: true, 
            opacity: 0.9 
          })
        );
        group.add(sphere);
        
        // Glow effect
        const glow = new THREE.Mesh(
          new THREE.SphereGeometry(size * 1.5, 16, 16),
          new THREE.MeshBasicMaterial({ 
            color: new THREE.Color(color), 
            transparent: true, 
            opacity: 0.2 
          })
        );
        group.add(glow);
      } else {
        // Result nodes - show thumbnail
        const textureLoader = new THREE.TextureLoader();
        const texture = textureLoader.load(node.url);
        
        // Thumbnail plane
        const geometry = new THREE.PlaneGeometry(size * 1.5, size * 1.5);
        const material = new THREE.MeshBasicMaterial({ 
          map: texture,
          transparent: true,
          side: THREE.DoubleSide
        });
        const plane = new THREE.Mesh(geometry, material);
        
        // Colored border based on match quality
        const borderGeometry = new THREE.PlaneGeometry(size * 1.6, size * 1.6);
        const borderMaterial = new THREE.MeshBasicMaterial({ 
          color: new THREE.Color(color),
          transparent: true,
          opacity: 0.8,
          side: THREE.BackSide
        });
        const border = new THREE.Mesh(borderGeometry, borderMaterial);
        border.position.z = -0.1;
        
        group.add(border);
        group.add(plane);
      }
      
      // Label
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const text = node.name?.length > 12 ? node.name.slice(0, 10) + '...' : (node.name || 'Untitled');
      ctx.font = 'bold 14px sans-serif';
      const w = ctx.measureText(text).width + 12;
      canvas.width = w;
      canvas.height = 24;
      
      ctx.fillStyle = 'rgba(15, 17, 23, 0.95)';
      ctx.fillRect(0, 0, w, 24);
      ctx.fillStyle = '#e8eaf6';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, w/2, 12);
      
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ 
        map: new THREE.CanvasTexture(canvas), 
        transparent: true 
      }));
      sprite.position.y = node.isQuery ? size + 6 : -size - 4;
      sprite.scale.set(w/4, 24/4, 1);
      group.add(sprite);
      
      return group;
    });
    
    // Link styling based on similarity
    searchGraphInstance.linkWidth(l => Math.max(0.5, l.similarity * 4));
    searchGraphInstance.linkColor(l => {
      const sim = l.similarity || 0;
      if (sim > 0.8) return 'rgba(76, 175, 125, 0.6)';  // Green for high sim
      if (sim > 0.6) return 'rgba(91, 110, 245, 0.5)';  // Blue for med sim
      return 'rgba(156, 39, 176, 0.4)';  // Purple for low sim
    });
    searchGraphInstance.linkOpacity(0.8);
    
    // Tooltip
    searchGraphInstance.nodeLabel(n => {
      if (n.isQuery) return 'Search Query';
      return `${n.name}\nMatch: ${Math.round(n.score || 0)}%\n${n.caption ? n.caption.slice(0, 50) : ''}`;
    });
    
    // Click handler
    searchGraphInstance.onNodeClick(node => {
      if (node.isQuery) return;
      openLightbox({ 
        url: node.url, 
        original_name: node.name, 
        caption: node.caption, 
        width: node.width || 0, 
        height: node.height || 0, 
        upload_ts: null 
      });
    });
    
    // Hover effect for preview
    const hoverPreview = document.getElementById('node-hover-preview');
    const hoverImg = hoverPreview?.querySelector('img');
    let hoverUpdateFunc;
    
    searchGraphInstance.onNodeHover(node => {
      if (node && !node.isQuery && hoverPreview && hoverImg && node.url) {
        hoverImg.src = node.url;
        hoverPreview.style.display = 'block';
        hoverUpdateFunc = (e) => {
          hoverPreview.style.left = (e.clientX + 20) + 'px';
          hoverPreview.style.top = (e.clientY - 100) + 'px';
        };
        document.addEventListener('mousemove', hoverUpdateFunc);
      } else {
        if (hoverPreview) hoverPreview.style.display = 'none';
        if (hoverUpdateFunc) document.removeEventListener('mousemove', hoverUpdateFunc);
      }
    });
    
    // Physics settings for better layout
    searchGraphInstance.d3Force('charge').strength(-100);
    searchGraphInstance.d3Force('link').distance(30);
    
    searchGraphInstance.warmupTicks(80);
    searchGraphInstance.cooldownTicks(50);
    
  } catch (e) {
    console.error('Search network error:', e);
    container.innerHTML = `<p style="padding:20px;color:var(--error)">Error: ${e.message}</p>`;
  }
}

/* ════════════════════════════════════════════════════════════
   GALLERY
════════════════════════════════════════════════════════════ */
const galleryGrid  = document.getElementById('gallery-grid');
const galleryEmpty = document.getElementById('gallery-empty');
const galleryCount = document.getElementById('gallery-count');

async function loadGallery() {
  galleryGrid.innerHTML = '<div class="loader"><div class="spinner"></div><span>Loading…</span></div>';
  galleryEmpty.classList.add('hidden');

  const res  = await fetch('/api/images');
  const data = await res.json();
  galleryGrid.innerHTML = '';

  if (!data.images.length) {
    galleryEmpty.classList.remove('hidden');
    galleryCount.textContent = '';
    return;
  }

  const mediaLabel = data.total === 1 ? 'file' : 'files';
  galleryCount.textContent = `${data.total} ${mediaLabel} in your library`;

  data.images.forEach(img => {
    const mediaType = img.media_type || 'image';
    const icon = MEDIA_ICONS[mediaType] || '📎';
    const isImage = mediaType === 'image';
    
    const card = document.createElement('div');
    card.className = 'gallery-card';
    const date = new Date(img.upload_ts).toLocaleDateString(undefined, { month:'short', day:'numeric', year:'numeric' });
    
    // Build preview based on media type
    let previewHTML;
    if (mediaType === 'image') {
      previewHTML = `<img src="${img.url}" alt="${img.original_name}" loading="lazy" />`;
    } else if (mediaType === 'video') {
      // Use anchor tag for reliable clicking
      previewHTML = `
        <a href="${img.url}" target="_blank" class="media-link" title="Click to open video" onclick="console.log('[CLICK] Video:', '${img.url}');">
          <video src="${img.url}" muted playsinline preload="metadata"></video>
          <div class="media-overlay">
            <span class="play-btn">▶</span>
            <small>Open Video</small>
          </div>
        </a>`;
    } else if (mediaType === 'audio') {
      previewHTML = `<div class="gallery-card-audio"><span>🎵</span><small>Audio</small></div>`;
    } else if (mediaType === 'pdf') {
      // Use anchor tag for reliable clicking
      previewHTML = `
        <a href="${img.url}" target="_blank" class="media-link" title="Click to open PDF" onclick="console.log('[CLICK] PDF:', '${img.url}');">
          <div class="gallery-card-pdf">
            <span>📄</span>
            <small>PDF Document</small>
          </div>
          <div class="media-overlay">
            <span class="open-btn">↗</span>
            <small>Open PDF</small>
          </div>
        </a>`;
    } else {
      previewHTML = `<div class="gallery-card-icon">${icon}</div>`;
    }
    
    const dimsText = (img.width && img.height) ? `${img.width} × ${img.height}` : mediaType.toUpperCase();
    
    card.innerHTML = `
      <div class="gallery-card-preview" data-media="${mediaType}">
        ${previewHTML}
        <div class="gallery-card-overlay">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </div>
      </div>
      <div class="gallery-card-body">
        <div class="g-name">${img.original_name}</div>
        <div class="g-date">${date}</div>
        <div class="g-dims">${dimsText}</div>
        <button class="btn-delete" data-id="${img.image_id}">Delete</button>
      </div>`;

    // Click handlers for different media types
    const previewEl = card.querySelector('.gallery-card-preview');
    if (mediaType === 'image') {
      previewEl.addEventListener('click', () => openLightbox(img));
    }
    // Note: Videos and PDFs now use <a> tags with target="_blank" for reliable clicking
    // The onclick handler in the HTML logs the click for debugging
    
    card.querySelector('.btn-delete').addEventListener('click', async e => {
      e.stopPropagation();
      if (!confirm(`Delete "${img.original_name}"?`)) return;
      const btn = e.currentTarget;
      btn.textContent = 'Deleting…'; btn.disabled = true;
      try {
        const r = await fetch(`/api/images/${img.image_id}`, { method: 'DELETE' });
        if (r.ok) { card.remove(); loadStats(); showToast('File deleted'); }
        else showToast('Delete failed', 'error');
      } catch { showToast('Delete failed', 'error'); }
    });

    galleryGrid.appendChild(card);
  });
}

/* ════════════════════════════════════════════════════════════
   LIGHTBOX & MEDIA PLAYERS
════════════════════════════════════════════════════════════ */
function openLightbox(img) {
  document.getElementById('lb-img').src        = img.url;
  document.getElementById('lb-name').textContent    = img.original_name;
  document.getElementById('lb-caption').textContent = img.caption || '—';
  document.getElementById('lb-size').textContent    = img.width ? `${img.width} × ${img.height} px` : '';
  document.getElementById('lb-date').textContent    = img.upload_ts
    ? new Date(img.upload_ts).toLocaleDateString(undefined, { dateStyle: 'medium' }) : '';
  document.getElementById('lightbox').classList.remove('hidden');
}

function openVideoPlayer(video) {
  console.log('[openVideoPlayer] Opening:', video?.url);
  if (video?.url) {
    window.open(video.url, '_blank');
  }
}

function openPdfViewer(pdf) {
  console.log('[openPdfViewer] Opening:', pdf?.url);
  if (pdf?.url) {
    window.open(pdf.url, '_blank');
  }
}

function closeLightbox() {
  document.getElementById('lightbox').classList.add('hidden');
  document.getElementById('lb-img').src = '';
}

document.getElementById('lb-close').addEventListener('click', closeLightbox);
document.getElementById('lb-backdrop').addEventListener('click', closeLightbox);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });

/* ════════════════════════════════════════════════════════════
   NETWORK 3D GRAPH (Simplified)
════════════════════════════════════════════════════════════ */
const networkContainer = document.getElementById('network-container');
const networkEmpty = document.getElementById('network-empty');
const networkStats = document.getElementById('network-stats');
const netRefreshBtn = document.getElementById('net-refresh');

let graphInstance = null;
let graphData = null;
let currentClusterMethod = 'neighbor';

// Cluster method selector
document.getElementById('cluster-method')?.addEventListener('change', (e) => {
  currentClusterMethod = e.target.value;
  loadNetworkGraph();
});

// Method descriptions
const methodDescriptions = {
  neighbor: 'Each image is colored based on its single most similar match. Creates visual "pairs" or "chains" of related images.',
  high_sim: 'Only images with >75% similarity are grouped together. Creates tight clusters of very similar content. Isolated images appear gray.',
  embedding_pca: 'Uses machine learning (PCA + K-means) on the 3072-dim embeddings to find natural semantic groupings.',
  similarity_tiers: 'Ranks all images by average similarity to others, then divides into 6 tiers. Blue = most connected, Red = most unique.',
  dominant_theme: 'Analyzes image captions for common keywords (person, nature, building, food, etc.) and groups by theme.',
  none: 'No grouping applied. All nodes shown in blue.'
};

async function loadNetworkGraph() {
  if (!document.getElementById('page-network').classList.contains('active')) return;
  
  if (!window.libsLoaded?.forceGraph3d) {
    document.getElementById('network-graph').innerHTML = `
      <div class="empty-state" style="padding:40px">
        <p style="color:var(--error)">Loading 3D library...</p>
      </div>
    `;
    networkContainer.classList.remove('hidden');
    setTimeout(loadNetworkGraph, 1000);
    return;
  }
  
  document.getElementById('network-graph').innerHTML = '<div class="loader" style="padding:40px"><div class="spinner"></div><span>Loading...</span></div>';
  networkEmpty.classList.add('hidden');
  networkContainer.classList.remove('hidden');
  
  try {
    const res = await fetch(`/api/network?cluster=${currentClusterMethod}`);
    const data = await res.json();
    
    if (data.error) throw new Error(data.error);
    if (!data.nodes || data.nodes.length < 2) {
      networkEmpty.classList.remove('hidden');
      networkContainer.classList.add('hidden');
      return;
    }
    
    graphData = data;
    networkStats.textContent = `${data.node_count} nodes, ${data.edge_count} edges`;
    
    // Show grouping description
    const descEl = document.getElementById('grouping-description');
    if (descEl) {
      descEl.textContent = data.description || methodDescriptions[currentClusterMethod] || '';
    }
    
    render3DGraph(data);
  } catch (e) {
    console.error('Network error:', e);
    document.getElementById('network-graph').innerHTML = `
      <div class="empty-state" style="padding:40px">
        <p style="color:var(--error)">Error: ${e.message}</p>
      </div>
    `;
  }
}

function render3DGraph(apiData) {
  const container = document.getElementById('network-graph');
  container.innerHTML = '';
  
  if (typeof ForceGraph3D === 'undefined' || typeof THREE === 'undefined') {
    container.innerHTML = `<div class="empty-state" style="padding:40px"><p style="color:var(--error)">3D library not loaded</p></div>`;
    return;
  }
  
  try {
    // Clone data
    const data = {
      nodes: apiData.nodes.map(n => ({ ...n })),
      links: (apiData.edges || []).map(e => ({ ...e }))
    };
    
    // Set initial positions
    data.nodes.forEach(n => {
      n.fx = n.x;
      n.fy = n.y;
      n.fz = n.z;
    });
    
    graphInstance = ForceGraph3D({ controlType: 'orbit' })(container)
      .graphData(data)
      .backgroundColor('#0f1117')
      .showNavInfo(false)
      .width(container.clientWidth)
      .height(600);
    
    // Node with thumbnail image
    graphInstance.nodeThreeObject(node => {
      const group = new THREE.Group();
      const size = 8;  // Node size
      
      // Create a plane with the image texture
      const textureLoader = new THREE.TextureLoader();
      const texture = textureLoader.load(node.url);
      
      // Create rounded rectangle shape for thumbnail
      const canvas = document.createElement('canvas');
      canvas.width = 128;
      canvas.height = 128;
      const ctx = canvas.getContext('2d');
      
      // Draw rounded rectangle background
      ctx.fillStyle = node.color || '#5b6ef5';
      ctx.beginPath();
      ctx.roundRect(0, 0, 128, 128, 16);
      ctx.fill();
      
      // Create texture from canvas
      const bgTexture = new THREE.CanvasTexture(canvas);
      
      // Main thumbnail plane
      const geometry = new THREE.PlaneGeometry(size, size);
      const material = new THREE.MeshBasicMaterial({ 
        map: texture,
        transparent: true,
        side: THREE.DoubleSide
      });
      const plane = new THREE.Mesh(geometry, material);
      
      // Add colored border/glow
      const borderGeometry = new THREE.PlaneGeometry(size + 0.5, size + 0.5);
      const borderMaterial = new THREE.MeshBasicMaterial({ 
        color: new THREE.Color(node.color || '#5b6ef5'),
        transparent: true,
        opacity: 0.8,
        side: THREE.BackSide
      });
      const border = new THREE.Mesh(borderGeometry, borderMaterial);
      border.position.z = -0.1;
      
      group.add(border);
      group.add(plane);
      
      // Label below the image
      const labelCanvas = document.createElement('canvas');
      const labelCtx = labelCanvas.getContext('2d');
      const text = node.name?.length > 12 ? node.name.slice(0, 10) + '...' : (node.name || 'Untitled');
      labelCtx.font = 'bold 14px sans-serif';
      const w = labelCtx.measureText(text).width + 16;
      labelCanvas.width = w;
      labelCanvas.height = 24;
      
      labelCtx.fillStyle = 'rgba(15, 17, 23, 0.95)';
      labelCtx.fillRect(0, 0, w, 24);
      labelCtx.fillStyle = '#e8eaf6';
      labelCtx.textAlign = 'center';
      labelCtx.textBaseline = 'middle';
      labelCtx.fillText(text, w/2, 12);
      
      const labelSprite = new THREE.Sprite(new THREE.SpriteMaterial({ 
        map: new THREE.CanvasTexture(labelCanvas), 
        transparent: true 
      }));
      labelSprite.position.y = -size/2 - 3;
      labelSprite.scale.set(w/4, 24/4, 1);
      group.add(labelSprite);
      
      return group;
    });
    
    graphInstance.linkWidth(l => Math.max(0.5, (l.similarity || 0.5) * 2));
    graphInstance.linkColor(() => 'rgba(150, 150, 150, 0.3)');
    graphInstance.nodeLabel(n => n.caption ? n.caption.slice(0, 60) : n.name);
    
    graphInstance.onNodeClick(node => {
      openLightbox({ 
        url: node.url, 
        original_name: node.name, 
        caption: node.caption, 
        width: node.width, 
        height: node.height, 
        upload_ts: null 
      });
    });
    
    // Hover effect for preview
    const hoverPreview = document.getElementById('node-hover-preview');
    const hoverImg = hoverPreview?.querySelector('img');
    
    graphInstance.onNodeHover(node => {
      if (node && hoverPreview && hoverImg && node.url) {
        hoverImg.src = node.url;
        hoverPreview.style.display = 'block';
        // Position near mouse but not covering it
        document.addEventListener('mousemove', updateHoverPosition);
      } else {
        if (hoverPreview) hoverPreview.style.display = 'none';
        document.removeEventListener('mousemove', updateHoverPosition);
      }
    });
    
    function updateHoverPosition(e) {
      if (hoverPreview) {
        hoverPreview.style.left = (e.clientX + 20) + 'px';
        hoverPreview.style.top = (e.clientY - 100) + 'px';
      }
    }
    
    graphInstance.warmupTicks(60);
    graphInstance.cooldownTicks(40);
    
    // Release fixed positions
    setTimeout(() => {
      data.nodes.forEach(n => { n.fx = n.fy = n.fz = undefined; });
    }, 800);
    
  } catch (e) {
    console.error('3D error:', e);
    container.innerHTML = `<div class="empty-state" style="padding:40px"><p style="color:var(--error)">Error: ${e.message}</p></div>`;
  }
}

// Refresh button
if (netRefreshBtn) {
  netRefreshBtn.addEventListener('click', () => {
    loadNetworkGraph();
  });
}

// Fullscreen toggle for main network
const netFullscreenBtn = document.getElementById('net-fullscreen');
if (netFullscreenBtn) {
  netFullscreenBtn.addEventListener('click', () => {
    const container = document.getElementById('network-container');
    const graphDiv = document.getElementById('network-graph');
    
    if (container.classList.contains('fullscreen')) {
      // Exit fullscreen
      container.classList.remove('fullscreen');
      netFullscreenBtn.textContent = '⛶';
      graphDiv.style.height = '600px';
    } else {
      // Enter fullscreen
      container.classList.add('fullscreen');
      netFullscreenBtn.textContent = '✕';
      graphDiv.style.height = 'calc(100vh - 100px)';
    }
    
    // Resize graph
    if (graphInstance) {
      setTimeout(() => {
        graphInstance.width(graphDiv.clientWidth);
        graphInstance.height(graphDiv.clientHeight);
      }, 100);
    }
  });
}

// Fullscreen toggle for search network
const searchNetFullscreenBtn = document.getElementById('search-net-fullscreen');
if (searchNetFullscreenBtn) {
  searchNetFullscreenBtn.addEventListener('click', () => {
    const container = document.getElementById('search-network-container');
    const graphDiv = document.getElementById('search-network-graph');
    
    if (container.classList.contains('fullscreen')) {
      // Exit fullscreen
      container.classList.remove('fullscreen');
      searchNetFullscreenBtn.textContent = '⛶';
      graphDiv.style.height = '400px';
    } else {
      // Enter fullscreen
      container.classList.add('fullscreen');
      searchNetFullscreenBtn.textContent = '✕';
    }
    
    // Resize graph
    if (searchGraphInstance) {
      setTimeout(() => {
        searchGraphInstance.width(graphDiv.clientWidth);
        searchGraphInstance.height(graphDiv.clientHeight);
      }, 100);
    }
  });
}

// Exit fullscreen on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    // Exit main network fullscreen
    const netContainer = document.getElementById('network-container');
    if (netContainer?.classList.contains('fullscreen')) {
      netContainer.classList.remove('fullscreen');
      if (netFullscreenBtn) netFullscreenBtn.textContent = '⛶';
      const graphDiv = document.getElementById('network-graph');
      graphDiv.style.height = '600px';
      if (graphInstance) {
        setTimeout(() => {
          graphInstance.width(graphDiv.clientWidth);
          graphInstance.height(graphDiv.clientHeight);
        }, 100);
      }
    }
    
    // Exit search network fullscreen
    const searchContainer = document.getElementById('search-network-container');
    if (searchContainer?.classList.contains('fullscreen')) {
      searchContainer.classList.remove('fullscreen');
      if (searchNetFullscreenBtn) searchNetFullscreenBtn.textContent = '⛶';
      const graphDiv = document.getElementById('search-network-graph');
      graphDiv.style.height = '400px';
      if (searchGraphInstance) {
        setTimeout(() => {
          searchGraphInstance.width(graphDiv.clientWidth);
          searchGraphInstance.height(graphDiv.clientHeight);
        }, 100);
      }
    }
  }
});

// Load network when navigating to network page
navBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.dataset.page === 'network') {
      loadNetworkGraph();
    }
  });
});
