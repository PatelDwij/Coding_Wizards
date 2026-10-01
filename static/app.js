/**
 * DocSnap - Client-Side Controller & UI Engine
 * Handles Drag & Drop, Paste, AI Stepper, Dynamic Schema Rendering,
 * Confidence Visualizer, Two-Way Data Binding, and Contextual Exports.
 */

(function () {
  'use strict';

  // App State
  const state = {
    currentScreen: 'upload', // 'upload' | 'processing' | 'results'
    currentFile: null,
    currentImageUrl: null,
    docType: null,
    language: 'English',
    confidence: 1.0,
    fieldConfidence: {},
    extractedData: null,
    zoomLevel: 100,
    isRawJsonVisible: false,
    stepperTimer: null
  };

  // DOM Elements Cache
  const DOM = {
    // Screens
    screenUpload: document.getElementById('screen-upload'),
    screenProcessing: document.getElementById('screen-processing'),
    screenResults: document.getElementById('screen-results'),
    
    // Header & Navigation
    brandLogo: document.getElementById('brand-logo'),
    navNewBtn: document.getElementById('nav-new-btn'),
    
    // Upload Screen
    dropZone: document.getElementById('drop-zone'),
    fileInput: document.getElementById('file-input'),
    browseBtn: document.getElementById('browse-btn'),
    sampleTimetable: document.getElementById('sample-timetable'),
    sampleReceipt: document.getElementById('sample-receipt'),
    sampleNotice: document.getElementById('sample-notice'),
    
    // Processing Screen
    step1: document.getElementById('step-1'),
    step2: document.getElementById('step-2'),
    step3: document.getElementById('step-3'),
    divider1: document.getElementById('divider-1'),
    divider2: document.getElementById('divider-2'),
    
    // Results Screen
    toolbarBackBtn: document.getElementById('toolbar-back-btn'),
    toggleJsonBtn: document.getElementById('toggle-json-btn'),
    toggleJsonText: document.getElementById('toggle-json-text'),
    copyJsonBtn: document.getElementById('copy-json-btn'),
    primaryActionBtn: document.getElementById('primary-action-btn'),
    primaryActionText: document.getElementById('primary-action-text'),
    primaryActionIcon: document.getElementById('primary-action-icon'),
    rawJsonPanel: document.getElementById('raw-json-panel'),
    rawJsonContent: document.getElementById('raw-json-content'),
    
    // Image Preview & Zoom
    previewFilename: document.getElementById('preview-filename'),
    previewViewport: document.getElementById('preview-viewport'),
    previewImage: document.getElementById('preview-image'),
    zoomInBtn: document.getElementById('zoom-in-btn'),
    zoomOutBtn: document.getElementById('zoom-out-btn'),
    zoomResetBtn: document.getElementById('zoom-reset-btn'),
    zoomLevelText: document.getElementById('zoom-level-text'),
    
    // Metadata Badges & Stats
    badgeDocType: document.getElementById('badge-doc-type'),
    badgeLanguage: document.getElementById('badge-language'),
    badgeConfidence: document.getElementById('badge-confidence'),
    badgeConfidenceDot: document.getElementById('badge-confidence-dot'),
    badgeConfidenceText: document.getElementById('badge-confidence-text'),
    summaryCards: document.getElementById('summary-cards'),
    
    // Editor Form & Action Panel
    dynamicFormArea: document.getElementById('dynamic-form-area'),
    actionPanelHeading: document.getElementById('action-panel-heading'),
    actionPanelSubheading: document.getElementById('action-panel-subheading'),
    bottomActionBtn: document.getElementById('bottom-action-btn'),
    bottomActionText: document.getElementById('bottom-action-text'),
    bottomActionIcon: document.getElementById('bottom-action-icon'),
    
    // Alerts & Toasts
    errorBanner: document.getElementById('error-banner'),
    errorMessage: document.getElementById('error-message'),
    errorCloseBtn: document.getElementById('error-close-btn'),
    toastContainer: document.getElementById('toast-container')
  };

  // =========================================================================
  // Initial Setup & Event Listeners
  // =========================================================================

  function init() {
    setupUploadHandlers();
    setupSampleHandlers();
    setupZoomControls();
    setupActionHandlers();
    setupGlobalPaste();
  }

  // =========================================================================
  // Screen Management
  // =========================================================================

  function showScreen(screenName, keepError = false) {
    state.currentScreen = screenName;
    if (DOM.screenUpload) DOM.screenUpload.classList.add('hidden');
    if (DOM.screenProcessing) DOM.screenProcessing.classList.add('hidden');
    if (DOM.screenResults) DOM.screenResults.classList.add('hidden');
    if (DOM.navNewBtn) DOM.navNewBtn.classList.add('hidden');

    if (!keepError) {
      hideError();
    }

    if (screenName === 'upload') {
      if (DOM.screenUpload) DOM.screenUpload.classList.remove('hidden');
      resetUploadState();
    } else if (screenName === 'processing') {
      if (DOM.screenProcessing) DOM.screenProcessing.classList.remove('hidden');
      startProcessingAnimation();
    } else if (screenName === 'results') {
      if (DOM.screenResults) DOM.screenResults.classList.remove('hidden');
      if (DOM.navNewBtn) DOM.navNewBtn.classList.remove('hidden');
      stopProcessingAnimation();
      renderResults();
    }
  }

  function resetUploadState() {
    if (state.currentImageUrl) {
      URL.revokeObjectURL(state.currentImageUrl);
    }
    state.currentFile = null;
    state.currentImageUrl = null;
    state.docType = null;
    state.extractedData = null;
    state.zoomLevel = 100;
    if (DOM.fileInput) DOM.fileInput.value = '';
    if (DOM.previewImage) DOM.previewImage.src = '';
    if (DOM.rawJsonPanel) DOM.rawJsonPanel.classList.add('hidden');
    if (DOM.toggleJsonText) DOM.toggleJsonText.textContent = 'View Raw JSON';
    state.isRawJsonVisible = false;
  }

  // =========================================================================
  // Upload & Drag/Drop Handlers
  // =========================================================================

  function setupUploadHandlers() {
    // Prevent file input clicks from bubbling to dropZone to avoid double-trigger recursion
    if (DOM.fileInput) {
      DOM.fileInput.addEventListener('click', (e) => {
        e.stopPropagation();
      });

      // File selected via native picker
      DOM.fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          handleFileSelection(e.target.files[0]);
        }
      });
    }

    // Browse button click inside dropzone
    if (DOM.browseBtn) {
      DOM.browseBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (DOM.fileInput) {
          DOM.fileInput.value = '';
          DOM.fileInput.click();
        }
      });
    }

    // Dropzone container click
    if (DOM.dropZone) {
      DOM.dropZone.addEventListener('click', (e) => {
        // Do nothing if file input was the direct target
        if (e.target === DOM.fileInput) return;
        // Do nothing if browse button was clicked (it has its own listener above)
        if (DOM.browseBtn && (e.target === DOM.browseBtn || DOM.browseBtn.contains(e.target))) {
          return;
        }
        if (DOM.fileInput) {
          DOM.fileInput.value = '';
          DOM.fileInput.click();
        }
      });

      // Keyboard accessibility for dropzone
      DOM.dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (DOM.fileInput) {
            DOM.fileInput.value = '';
            DOM.fileInput.click();
          }
        }
      });

      // Drag over / enter events
      ['dragenter', 'dragover'].forEach(eventName => {
        DOM.dropZone.addEventListener(eventName, (e) => {
          e.preventDefault();
          e.stopPropagation();
          DOM.dropZone.classList.add('drag-active');
        });
      });

      DOM.dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        DOM.dropZone.classList.remove('drag-active');
      });

      DOM.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        DOM.dropZone.classList.remove('drag-active');
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
          handleFileSelection(dt.files[0]);
        }
      });
    }

    // Prevent default browser behavior on window drop/dragover (which opens images in browser tab)
    window.addEventListener('dragover', (e) => e.preventDefault(), false);
    window.addEventListener('drop', (e) => e.preventDefault(), false);

    // Error dismiss
    if (DOM.errorCloseBtn) {
      DOM.errorCloseBtn.addEventListener('click', hideError);
    }

    // New document buttons
    if (DOM.navNewBtn) {
      DOM.navNewBtn.addEventListener('click', () => showScreen('upload'));
    }
    if (DOM.toolbarBackBtn) {
      DOM.toolbarBackBtn.addEventListener('click', () => showScreen('upload'));
    }
    if (DOM.brandLogo) {
      DOM.brandLogo.addEventListener('click', () => showScreen('upload'));
    }
  }

  // Global Paste Listener (Ctrl+V)
  function setupGlobalPaste() {
    window.addEventListener('paste', (e) => {
      const clipboardData = e.clipboardData || window.clipboardData;
      if (!clipboardData) return;

      // 1. Try clipboard items
      if (clipboardData.items && clipboardData.items.length > 0) {
        for (let i = 0; i < clipboardData.items.length; i++) {
          const item = clipboardData.items[i];
          if (item.type && item.type.indexOf('image') !== -1) {
            let file = item.getAsFile();
            if (file) {
              // Ensure valid filename
              if (!file.name || !file.name.includes('.')) {
                const ext = file.type === 'image/jpeg' ? 'jpg' : (file.type === 'image/webp' ? 'webp' : 'png');
                file = new File([file], `pasted_document_${Date.now()}.${ext}`, { type: file.type || 'image/png' });
              }
              showToast('Pasted image from clipboard!', 'success');
              handleFileSelection(file);
              return;
            }
          }
        }
      }

      // 2. Try clipboard files fallback
      if (clipboardData.files && clipboardData.files.length > 0) {
        for (let i = 0; i < clipboardData.files.length; i++) {
          let file = clipboardData.files[i];
          if (file.type && file.type.startsWith('image/')) {
            if (!file.name || !file.name.includes('.')) {
              const ext = file.type === 'image/jpeg' ? 'jpg' : (file.type === 'image/webp' ? 'webp' : 'png');
              file = new File([file], `pasted_document_${Date.now()}.${ext}`, { type: file.type || 'image/png' });
            }
            showToast('Pasted image from clipboard!', 'success');
            handleFileSelection(file);
            return;
          }
        }
      }
    });
  }

  // Sample Documents Click
  function setupSampleHandlers() {
    const samples = [
      { el: DOM.sampleTimetable, file: 'sample_timetable.png', name: 'sample_timetable.png' },
      { el: DOM.sampleReceipt, file: 'sample_receipt.png', name: 'sample_receipt.png' },
      { el: DOM.sampleNotice, file: 'sample_notice.png', name: 'sample_notice.png' }
    ];

    samples.forEach(s => {
      if (!s.el) return;
      const loadSample = async () => {
        try {
          showScreen('processing');
          const response = await fetch(`/static/samples/${s.file}`);
          if (!response.ok) throw new Error("Could not load sample image.");
          const blob = await response.blob();
          const file = new File([blob], s.name, { type: 'image/png' });
          processDocument(file);
        } catch (err) {
          showScreen('upload');
          showError(`Sample loading failed: ${err.message}`);
        }
      };

      s.el.addEventListener('click', loadSample);
      s.el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          loadSample();
        }
      });
    });
  }

  function handleFileSelection(file) {
    if (!file) return;

    // Validate file type
    const validMimes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/x-png', 'image/pjpeg'];
    const ext = file.name ? file.name.split('.').pop().toLowerCase() : '';
    const validExts = ['png', 'jpg', 'jpeg', 'webp'];

    const isValidMime = validMimes.includes((file.type || '').toLowerCase());
    const isValidExt = validExts.includes(ext);

    if (!isValidMime && !isValidExt) {
      showError("Invalid file type. Please upload a PNG, JPG, or WEBP image.");
      return;
    }

    // Validate size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      showError("File size exceeds 5MB limit. Please upload a smaller image.");
      return;
    }

    // Ensure valid filename with extension
    if (!file.name || !file.name.includes('.')) {
      const inferredExt = file.type === 'image/jpeg' ? 'jpg' : (file.type === 'image/webp' ? 'webp' : 'png');
      file = new File([file], `upload_${Date.now()}.${inferredExt}`, { type: file.type || 'image/png' });
    }

    hideError();
    processDocument(file);
  }

  // =========================================================================
  // Backend Extraction & Stepper
  // =========================================================================

  function startProcessingAnimation() {
    // Step 1
    DOM.step1.className = 'step-item active';
    DOM.step2.className = 'step-item';
    DOM.step3.className = 'step-item';
    DOM.divider1.className = 'step-divider';
    DOM.divider2.className = 'step-divider';

    // Simulated progress transitions while waiting for network
    state.stepperTimer = setTimeout(() => {
      DOM.step1.className = 'step-item completed';
      DOM.divider1.className = 'step-divider active';
      DOM.step2.className = 'step-item active';

      state.stepperTimer = setTimeout(() => {
        DOM.step2.className = 'step-item completed';
        DOM.divider2.className = 'step-divider active';
        DOM.step3.className = 'step-item active';
      }, 1600);
    }, 1200);
  }

  function stopProcessingAnimation() {
    if (state.stepperTimer) {
      clearTimeout(state.stepperTimer);
      state.stepperTimer = null;
    }
  }

  async function processDocument(file) {
    state.currentFile = file;
    state.currentImageUrl = URL.createObjectURL(file);
    showScreen('processing');

    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await fetch('/extract', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || `Server responded with status ${response.status}`);
      }

      // Mark final step completed
      DOM.step3.className = 'step-item completed';

      // Update state
      state.docType = result.doc_type;
      state.language = result.language || 'English';
      state.confidence = typeof result.confidence === 'number' ? result.confidence : 0.95;
      state.fieldConfidence = result.field_confidence || {};
      state.extractedData = result.data || {};

      if (result._demo_mode && result._note) {
        showToast(result._note, 'success', 5000);
      }

      // Show results screen
      setTimeout(() => {
        showScreen('results');
      }, 400);

    } catch (err) {
      stopProcessingAnimation();
      showScreen('upload', true);
      showError(err.message || "Failed to extract document. Please try again.");
    }
  }

  // =========================================================================
  // SCREEN 3: Results Rendering & Two-Way Binding
  // =========================================================================

  function renderResults() {
    // 1. Set Image Preview
    DOM.previewImage.src = state.currentImageUrl;
    DOM.previewFilename.textContent = state.currentFile ? state.currentFile.name : 'document.png';
    setZoom(100);

    // 2. Set Badges
    const docTypeLabels = {
      'timetable': 'Timetable Schedule',
      'receipt': 'Purchase Receipt',
      'notice': 'Official Notice'
    };
    DOM.badgeDocType.textContent = docTypeLabels[state.docType] || state.docType;
    DOM.badgeLanguage.textContent = state.language;

    const confPercent = Math.round(state.confidence * 100);
    DOM.badgeConfidenceText.textContent = `${confPercent}% Confidence`;
    
    // Confidence color classes
    DOM.badgeConfidence.className = 'confidence-badge';
    if (state.confidence >= 0.85) {
      DOM.badgeConfidence.classList.add('high');
    } else if (state.confidence >= 0.70) {
      DOM.badgeConfidence.classList.add('mid');
    } else {
      DOM.badgeConfidence.classList.add('low');
    }

    // 3. Render Summary Stats
    renderSummaryStats();

    // 4. Render Dynamic Form / Tables
    renderDynamicForm();

    // 5. Update Action Buttons
    updateActionPanel();

    // 6. Update Raw JSON View
    updateRawJsonView();
  }

  // Render Stats Grid
  function renderSummaryStats() {
    DOM.summaryCards.innerHTML = '';
    const data = state.extractedData;

    if (state.docType === 'timetable') {
      const entries = data.entries || [];
      const days = new Set(entries.map(e => e.day).filter(Boolean));
      const rooms = new Set(entries.map(e => e.room).filter(Boolean));

      addStatCard('Classes Found', `${entries.length} Sessions`);
      addStatCard('Active Days', `${days.size} Days`);
      addStatCard('Rooms / Venues', `${rooms.size} Locations`);
    } else if (state.docType === 'receipt') {
      const items = data.items || [];
      const currency = data.currency || '₹';
      const total = data.total ? `${currency} ${Number(data.total).toLocaleString('en-IN')}` : 'N/A';

      addStatCard('Merchant', data.merchant || 'Store');
      addStatCard('Total Amount', total);
      addStatCard('Category', data.category || 'General');
      addStatCard('Line Items', `${items.length} Items`);
    } else if (state.docType === 'notice') {
      addStatCard('Event Date', data.date || 'Upcoming');
      addStatCard('Timings', (data.start_time && data.end_time) ? `${data.start_time} - ${data.end_time}` : (data.start_time || 'All Day'));
      addStatCard('Venue', data.venue ? (data.venue.length > 20 ? data.venue.substring(0, 18) + '...' : data.venue) : 'Not specified');
    }
  }

  function addStatCard(label, value) {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.innerHTML = `
      <span class="stat-label">${escapeHtml(label)}</span>
      <span class="stat-value">${escapeHtml(value)}</span>
    `;
    DOM.summaryCards.appendChild(card);
  }

  // Dynamic Form Builder
  function renderDynamicForm() {
    DOM.dynamicFormArea.innerHTML = '';
    const data = state.extractedData;

    if (state.docType === 'timetable') {
      renderTimetableForm(data);
    } else if (state.docType === 'receipt') {
      renderReceiptForm(data);
    } else if (state.docType === 'notice') {
      renderNoticeForm(data);
    }
  }

  // 1. Timetable Form
  function renderTimetableForm(data) {
    const container = document.createElement('div');

    // Title Field
    const titleConf = getFieldConfidence('title');
    container.innerHTML = `
      <div class="form-group">
        <div class="form-label-row">
          <label class="form-label" for="tb-title">Schedule / Institution Title</label>
          ${renderConfidenceBadge(titleConf)}
        </div>
        <div class="form-input-wrapper">
          <input type="text" id="tb-title" class="form-input ${titleConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.title || '')}" placeholder="e.g. Computer Science Semester IV Timetable">
          <span class="field-dot" style="background-color: ${getConfidenceColor(titleConf)}"></span>
        </div>
      </div>

      <div class="form-group">
        <div class="form-label-row">
          <label class="form-label">Lecture & Lab Schedule Entries</label>
          <span class="meta-pill" id="tb-entry-count">${(data.entries || []).length} Classes</span>
        </div>
        
        <div class="table-container">
          <table class="data-table" id="timetable-table">
            <thead>
              <tr>
                <th style="width: 140px;">Day</th>
                <th style="width: 110px;">Start</th>
                <th style="width: 110px;">End</th>
                <th>Subject / Course</th>
                <th style="width: 130px;">Room / Lab</th>
                <th style="width: 150px;">Faculty</th>
                <th style="width: 48px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="timetable-rows"></tbody>
          </table>
        </div>

        <div class="table-footer-actions">
          <button type="button" class="btn btn-secondary btn-sm" id="tb-add-row-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            <span>Add Class Entry</span>
          </button>
          <span class="footer-tip">Rows automatically sort into weekly recurring calendar events.</span>
        </div>
      </div>
    `;

    DOM.dynamicFormArea.appendChild(container);

    // Bind title input
    const titleInput = container.querySelector('#tb-title');
    titleInput.addEventListener('input', (e) => {
      data.title = e.target.value;
      updateRawJsonView();
    });

    // Populate rows
    const tbody = container.querySelector('#timetable-rows');
    (data.entries || []).forEach((entry, idx) => {
      renderTimetableRow(tbody, entry, idx);
    });

    // Add row button
    const addRowBtn = container.querySelector('#tb-add-row-btn');
    addRowBtn.addEventListener('click', () => {
      if (!data.entries) data.entries = [];
      const newEntry = {
        subject: "New Class",
        day: "Monday",
        start_time: "09:00",
        end_time: "10:00",
        room: "Room 101",
        faculty: ""
      };
      data.entries.push(newEntry);
      renderTimetableRow(tbody, newEntry, data.entries.length - 1);
      updateTimetableMeta();
      updateRawJsonView();
    });
  }

  function renderTimetableRow(tbody, entry, index) {
    const tr = document.createElement('tr');
    tr.dataset.index = index;

    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    let dayOptions = days.map(d => `<option value="${d}" ${d.toLowerCase() === (entry.day || '').toLowerCase() ? 'selected' : ''}>${d}</option>`).join('');

    const subConf = getFieldConfidence('entries.subject');
    const startConf = getFieldConfidence('entries.start_time');
    const endConf = getFieldConfidence('entries.end_time');
    const roomConf = getFieldConfidence('entries.room');

    tr.innerHTML = `
      <td>
        <select class="form-select table-input row-day">
          ${dayOptions}
        </select>
      </td>
      <td>
        <input type="time" class="table-input row-start ${startConf < 0.7 ? 'low-conf' : ''}" value="${entry.start_time || '09:00'}">
      </td>
      <td>
        <input type="time" class="table-input row-end ${endConf < 0.7 ? 'low-conf' : ''}" value="${entry.end_time || '10:00'}">
      </td>
      <td>
        <input type="text" class="table-input row-subject ${subConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(entry.subject || '')}" placeholder="Course name">
      </td>
      <td>
        <input type="text" class="table-input row-room ${roomConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(entry.room || '')}" placeholder="Room #">
      </td>
      <td>
        <input type="text" class="table-input row-faculty" value="${escapeHtml(entry.faculty || '')}" placeholder="Professor">
      </td>
      <td style="text-align: right;">
        <button type="button" class="btn-delete-row" title="Delete class row" aria-label="Delete class row">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </td>
    `;

    // Bind inputs to data object
    const daySelect = tr.querySelector('.row-day');
    const startInput = tr.querySelector('.row-start');
    const endInput = tr.querySelector('.row-end');
    const subjectInput = tr.querySelector('.row-subject');
    const roomInput = tr.querySelector('.row-room');
    const facultyInput = tr.querySelector('.row-faculty');
    const deleteBtn = tr.querySelector('.btn-delete-row');

    daySelect.addEventListener('change', (e) => { entry.day = e.target.value; updateRawJsonView(); });
    startInput.addEventListener('input', (e) => { entry.start_time = e.target.value; updateRawJsonView(); });
    endInput.addEventListener('input', (e) => { entry.end_time = e.target.value; updateRawJsonView(); });
    subjectInput.addEventListener('input', (e) => { entry.subject = e.target.value; updateRawJsonView(); });
    roomInput.addEventListener('input', (e) => { entry.room = e.target.value; updateRawJsonView(); });
    facultyInput.addEventListener('input', (e) => { entry.faculty = e.target.value; updateRawJsonView(); });

    deleteBtn.addEventListener('click', () => {
      const idx = state.extractedData.entries.indexOf(entry);
      if (idx !== -1) {
        state.extractedData.entries.splice(idx, 1);
        tr.remove();
        updateTimetableMeta();
        updateRawJsonView();
      }
    });

    tbody.appendChild(tr);
  }

  function updateTimetableMeta() {
    const countEl = document.getElementById('tb-entry-count');
    if (countEl) {
      countEl.textContent = `${(state.extractedData.entries || []).length} Classes`;
    }
    renderSummaryStats();
  }

  // 2. Receipt Form
  function renderReceiptForm(data) {
    const container = document.createElement('div');
    const merchConf = getFieldConfidence('merchant');
    const dateConf = getFieldConfidence('date');
    const totalConf = getFieldConfidence('total');
    const catConf = getFieldConfidence('category');

    container.innerHTML = `
      <div class="form-grid-2">
        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="rc-merchant">Merchant / Store Name</label>
            ${renderConfidenceBadge(merchConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="text" id="rc-merchant" class="form-input ${merchConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.merchant || '')}" placeholder="Store Name">
            <span class="field-dot" style="background-color: ${getConfidenceColor(merchConf)}"></span>
          </div>
        </div>

        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="rc-date">Receipt Date</label>
            ${renderConfidenceBadge(dateConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="date" id="rc-date" class="form-input ${dateConf < 0.7 ? 'low-conf' : ''}" value="${data.date || ''}">
            <span class="field-dot" style="background-color: ${getConfidenceColor(dateConf)}"></span>
          </div>
        </div>
      </div>

      <div class="form-grid-3">
        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="rc-total">Total Amount</label>
            ${renderConfidenceBadge(totalConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="number" step="0.01" id="rc-total" class="form-input ${totalConf < 0.7 ? 'low-conf' : ''}" value="${data.total !== undefined ? data.total : ''}" placeholder="0.00">
            <span class="field-dot" style="background-color: ${getConfidenceColor(totalConf)}"></span>
          </div>
        </div>

        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="rc-currency">Currency</label>
          </div>
          <div class="form-input-wrapper">
            <input type="text" id="rc-currency" class="form-input" value="${escapeHtml(data.currency || '₹')}" placeholder="₹">
          </div>
        </div>

        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="rc-category">Expense Category</label>
            ${renderConfidenceBadge(catConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="text" id="rc-category" class="form-input ${catConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.category || 'Food & Dining')}" placeholder="Category">
            <span class="field-dot" style="background-color: ${getConfidenceColor(catConf)}"></span>
          </div>
        </div>
      </div>

      <div class="form-group">
        <div class="form-label-row">
          <label class="form-label">Itemized Line Items</label>
          <span class="meta-pill" id="rc-item-count">${(data.items || []).length} Items</span>
        </div>

        <div class="table-container">
          <table class="data-table" id="receipt-table">
            <thead>
              <tr>
                <th>Item Description</th>
                <th style="width: 90px;">Qty</th>
                <th style="width: 120px;">Price</th>
                <th style="width: 120px;">Line Total</th>
                <th style="width: 48px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="receipt-rows"></tbody>
          </table>
        </div>

        <div class="table-footer-actions">
          <button type="button" class="btn btn-secondary btn-sm" id="rc-add-item-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            <span>Add Item</span>
          </button>
          <span class="footer-tip">Export generates CSV with item breakdown and merchant summary.</span>
        </div>
      </div>
    `;

    DOM.dynamicFormArea.appendChild(container);

    // Bind metadata inputs
    const merchInput = container.querySelector('#rc-merchant');
    const dateInput = container.querySelector('#rc-date');
    const totalInput = container.querySelector('#rc-total');
    const curInput = container.querySelector('#rc-currency');
    const catInput = container.querySelector('#rc-category');

    merchInput.addEventListener('input', (e) => { data.merchant = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    dateInput.addEventListener('input', (e) => { data.date = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    totalInput.addEventListener('input', (e) => { data.total = parseFloat(e.target.value) || 0; renderSummaryStats(); updateRawJsonView(); });
    curInput.addEventListener('input', (e) => { data.currency = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    catInput.addEventListener('input', (e) => { data.category = e.target.value; renderSummaryStats(); updateRawJsonView(); });

    const tbody = container.querySelector('#receipt-rows');
    (data.items || []).forEach((item, idx) => {
      renderReceiptItemRow(tbody, item, idx);
    });

    const addItemBtn = container.querySelector('#rc-add-item-btn');
    addItemBtn.addEventListener('click', () => {
      if (!data.items) data.items = [];
      const newItem = { name: "New Item", qty: 1, price: 0.0 };
      data.items.push(newItem);
      renderReceiptItemRow(tbody, newItem, data.items.length - 1);
      updateReceiptMeta();
      updateRawJsonView();
    });
  }

  function renderReceiptItemRow(tbody, item, index) {
    const tr = document.createElement('tr');
    tr.dataset.index = index;

    const lineTotal = ((item.qty || 1) * (item.price || 0)).toFixed(2);
    const itemConf = getFieldConfidence('items');

    tr.innerHTML = `
      <td>
        <input type="text" class="table-input item-name ${itemConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(item.name || '')}" placeholder="Item description">
      </td>
      <td>
        <input type="number" step="1" min="1" class="table-input item-qty" value="${item.qty || 1}">
      </td>
      <td>
        <input type="number" step="0.01" min="0" class="table-input item-price" value="${item.price !== undefined ? item.price : 0}">
      </td>
      <td>
        <span class="item-line-total" style="font-weight: 600; padding-left: 0.5rem;">${lineTotal}</span>
      </td>
      <td style="text-align: right;">
        <button type="button" class="btn-delete-row" title="Delete item" aria-label="Delete item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </td>
    `;

    const nameInput = tr.querySelector('.item-name');
    const qtyInput = tr.querySelector('.item-qty');
    const priceInput = tr.querySelector('.item-price');
    const lineTotalSpan = tr.querySelector('.item-line-total');
    const deleteBtn = tr.querySelector('.btn-delete-row');

    function updateLine() {
      const q = parseFloat(qtyInput.value) || 1;
      const p = parseFloat(priceInput.value) || 0;
      lineTotalSpan.textContent = (q * p).toFixed(2);
    }

    nameInput.addEventListener('input', (e) => { item.name = e.target.value; updateRawJsonView(); });
    qtyInput.addEventListener('input', (e) => { item.qty = parseFloat(e.target.value) || 1; updateLine(); updateRawJsonView(); });
    priceInput.addEventListener('input', (e) => { item.price = parseFloat(e.target.value) || 0; updateLine(); updateRawJsonView(); });

    deleteBtn.addEventListener('click', () => {
      const idx = state.extractedData.items.indexOf(item);
      if (idx !== -1) {
        state.extractedData.items.splice(idx, 1);
        tr.remove();
        updateReceiptMeta();
        updateRawJsonView();
      }
    });

    tbody.appendChild(tr);
  }

  function updateReceiptMeta() {
    const countEl = document.getElementById('rc-item-count');
    if (countEl) {
      countEl.textContent = `${(state.extractedData.items || []).length} Items`;
    }
    renderSummaryStats();
  }

  // 3. Notice Form
  function renderNoticeForm(data) {
    const container = document.createElement('div');
    const titleConf = getFieldConfidence('title');
    const dateConf = getFieldConfidence('date');
    const startConf = getFieldConfidence('start_time');
    const endConf = getFieldConfidence('end_time');
    const venueConf = getFieldConfidence('venue');
    const descConf = getFieldConfidence('description');

    container.innerHTML = `
      <div class="form-group">
        <div class="form-label-row">
          <label class="form-label" for="nt-title">Notice Title / Headline</label>
          ${renderConfidenceBadge(titleConf)}
        </div>
        <div class="form-input-wrapper">
          <input type="text" id="nt-title" class="form-input ${titleConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.title || '')}" placeholder="Notice Headline">
          <span class="field-dot" style="background-color: ${getConfidenceColor(titleConf)}"></span>
        </div>
      </div>

      <div class="form-grid-3">
        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="nt-date">Event Date</label>
            ${renderConfidenceBadge(dateConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="date" id="nt-date" class="form-input ${dateConf < 0.7 ? 'low-conf' : ''}" value="${data.date || ''}">
            <span class="field-dot" style="background-color: ${getConfidenceColor(dateConf)}"></span>
          </div>
        </div>

        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="nt-start">Start Time</label>
            ${renderConfidenceBadge(startConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="time" id="nt-start" class="form-input ${startConf < 0.7 ? 'low-conf' : ''}" value="${data.start_time || '09:30'}">
            <span class="field-dot" style="background-color: ${getConfidenceColor(startConf)}"></span>
          </div>
        </div>

        <div class="form-group">
          <div class="form-label-row">
            <label class="form-label" for="nt-end">End Time</label>
            ${renderConfidenceBadge(endConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="time" id="nt-end" class="form-input ${endConf < 0.7 ? 'low-conf' : ''}" value="${data.end_time || '17:30'}">
            <span class="field-dot" style="background-color: ${getConfidenceColor(endConf)}"></span>
          </div>
        </div>
      </div>

      <div class="form-group">
        <div class="form-label-row">
          <label class="form-label" for="nt-venue">Venue / Location</label>
          ${renderConfidenceBadge(venueConf)}
        </div>
        <div class="form-input-wrapper">
          <input type="text" id="nt-venue" class="form-input ${venueConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.venue || '')}" placeholder="Auditorium, Hall, Campus">
          <span class="field-dot" style="background-color: ${getConfidenceColor(venueConf)}"></span>
        </div>
      </div>

      <div class="form-group">
        <div class="form-label-row">
          <label class="form-label" for="nt-desc">Event Details / Description</label>
          ${renderConfidenceBadge(descConf)}
        </div>
        <div class="form-input-wrapper">
          <textarea id="nt-desc" class="form-textarea ${descConf < 0.7 ? 'low-conf' : ''}" rows="4" placeholder="Summary of notice contents">${escapeHtml(data.description || '')}</textarea>
        </div>
      </div>
    `;

    DOM.dynamicFormArea.appendChild(container);

    // Bindings
    const titleInput = container.querySelector('#nt-title');
    const dateInput = container.querySelector('#nt-date');
    const startInput = container.querySelector('#nt-start');
    const endInput = container.querySelector('#nt-end');
    const venueInput = container.querySelector('#nt-venue');
    const descInput = container.querySelector('#nt-desc');

    titleInput.addEventListener('input', (e) => { data.title = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    dateInput.addEventListener('input', (e) => { data.date = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    startInput.addEventListener('input', (e) => { data.start_time = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    endInput.addEventListener('input', (e) => { data.end_time = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    venueInput.addEventListener('input', (e) => { data.venue = e.target.value; renderSummaryStats(); updateRawJsonView(); });
    descInput.addEventListener('input', (e) => { data.description = e.target.value; updateRawJsonView(); });
  }

  // =========================================================================
  // Confidence Helpers
  // =========================================================================

  function getFieldConfidence(fieldName) {
    if (state.fieldConfidence && typeof state.fieldConfidence[fieldName] === 'number') {
      return state.fieldConfidence[fieldName];
    }
    return state.confidence || 0.95;
  }

  function getConfidenceColor(conf) {
    if (conf >= 0.85) return 'var(--conf-high)';
    if (conf >= 0.70) return 'var(--conf-mid)';
    return 'var(--conf-low)';
  }

  function renderConfidenceBadge(conf) {
    if (conf < 0.70) {
      return `
        <span class="field-verify-badge" title="Confidence: ${Math.round(conf * 100)}% - Please verify this value">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          Please verify (${Math.round(conf * 100)}%)
        </span>
      `;
    }
    return '';
  }

  // =========================================================================
  // Action Panel & Export Triggers
  // =========================================================================

  function updateActionPanel() {
    let actionLabel = 'Export';
    let heading = 'Ready to sync?';
    let subheading = 'Export your structured data directly into calendar or spreadsheet apps.';

    if (state.docType === 'timetable') {
      actionLabel = 'Add to Calendar (.ics)';
      heading = 'Sync Weekly Schedule';
      subheading = 'Exports recurring weekly events (RRULE WEEKLY) in Asia/Kolkata timezone.';
    } else if (state.docType === 'notice') {
      actionLabel = 'Add Event to Calendar (.ics)';
      heading = 'Add Event to Calendar';
      subheading = 'Creates a calendar event ready for Google Calendar, Apple Calendar, or Outlook.';
    } else if (state.docType === 'receipt') {
      actionLabel = 'Export CSV Spreadsheet';
      heading = 'Export Expense Data';
      subheading = 'Downloads itemized CSV formatted for Excel, Google Sheets, or expense reports.';
    }

    DOM.primaryActionText.textContent = actionLabel;
    DOM.bottomActionText.textContent = actionLabel;
    DOM.actionPanelHeading.textContent = heading;
    DOM.actionPanelSubheading.textContent = subheading;
  }

  function setupActionHandlers() {
    // Primary Top Action
    DOM.primaryActionBtn.addEventListener('click', triggerExport);
    // Bottom Action
    DOM.bottomActionBtn.addEventListener('click', triggerExport);

    // Toggle Raw JSON
    DOM.toggleJsonBtn.addEventListener('click', () => {
      state.isRawJsonVisible = !state.isRawJsonVisible;
      if (state.isRawJsonVisible) {
        DOM.rawJsonPanel.classList.remove('hidden');
        DOM.toggleJsonText.textContent = 'Hide Raw JSON';
        DOM.toggleJsonBtn.setAttribute('aria-expanded', 'true');
      } else {
        DOM.rawJsonPanel.classList.add('hidden');
        DOM.toggleJsonText.textContent = 'View Raw JSON';
        DOM.toggleJsonBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Copy JSON
    DOM.copyJsonBtn.addEventListener('click', () => {
      const payload = getCurrentPayload();
      const jsonStr = JSON.stringify(payload, null, 2);
      navigator.clipboard.writeText(jsonStr).then(() => {
        showToast("JSON payload copied to clipboard!", "success");
      }).catch(() => {
        showError("Unable to copy to clipboard.");
      });
    });
  }

  function getCurrentPayload() {
    return {
      doc_type: state.docType,
      language: state.language,
      confidence: state.confidence,
      field_confidence: state.fieldConfidence,
      data: state.extractedData
    };
  }

  function updateRawJsonView() {
    const payload = getCurrentPayload();
    DOM.rawJsonContent.innerHTML = `<code>${escapeHtml(JSON.stringify(payload, null, 2))}</code>`;
  }

  async function triggerExport() {
    const payload = getCurrentPayload();

    try {
      if (state.docType === 'timetable' || state.docType === 'notice') {
        const response = await fetch('/export/ics', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.error || 'Failed to export .ics calendar file.');
        }

        const blob = await response.blob();
        const filename = state.docType === 'timetable' ? 'schedule.ics' : 'event_notice.ics';
        downloadBlob(blob, filename);
        showToast("Calendar file (.ics) downloaded! Open to import into your calendar.", "success", 4500);

      } else if (state.docType === 'receipt') {
        const response = await fetch('/export/csv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.error || 'Failed to export CSV file.');
        }

        const blob = await response.blob();
        const filename = `receipt_${(state.extractedData.merchant || 'export').replace(/[^a-zA-Z0-9_]/g, '_')}.csv`;
        downloadBlob(blob, filename);
        showToast("CSV exported successfully! Ready for Excel or Sheets.", "success", 4500);
      }
    } catch (err) {
      showError(err.message);
    }
  }

  function downloadBlob(blob, defaultFilename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = defaultFilename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  }

  // =========================================================================
  // Zoom Controls & Pan
  // =========================================================================

  function setupZoomControls() {
    DOM.zoomInBtn.addEventListener('click', () => setZoom(state.zoomLevel + 25));
    DOM.zoomOutBtn.addEventListener('click', () => setZoom(state.zoomLevel - 25));
    DOM.zoomResetBtn.addEventListener('click', () => setZoom(100));

    // Mouse wheel zoom inside preview
    DOM.previewViewport.addEventListener('wheel', (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY < 0 ? 25 : -25;
        setZoom(state.zoomLevel + delta);
      }
    }, { passive: false });
  }

  function setZoom(newZoom) {
    const clamped = Math.max(50, Math.min(300, newZoom));
    state.zoomLevel = clamped;
    DOM.zoomLevelText.textContent = `${clamped}%`;
    DOM.previewImage.style.transform = `scale(${clamped / 100})`;
  }

  // =========================================================================
  // Toast & Alert Helpers
  // =========================================================================

  function showToast(message, type = 'success', duration = 3500) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconSvg = type === 'success' ? 
      `<svg class="toast-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>` :
      `<svg class="toast-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;

    toast.innerHTML = `
      ${iconSvg}
      <span class="toast-message">${escapeHtml(message)}</span>
    `;

    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 250);
    }, duration);
  }

  function showError(msg) {
    DOM.errorMessage.textContent = msg;
    DOM.errorBanner.classList.remove('hidden');
    DOM.errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideError() {
    DOM.errorBanner.classList.add('hidden');
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initialize on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
