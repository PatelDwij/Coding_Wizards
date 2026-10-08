/**
 * DocSnap - Client-Side Controller & Verification Engine
 * Features:
 * - Multimodal OCR & Document Classification
 * - Field-Level Confidence Auditing
 * - Dedicated Verification Agent (Conflict & Math Audits)
 * - Human-in-the-Loop Visual Verification ("Verify Against Image")
 * - AI Result vs Verified Result (Immutable Version History & Diff Viewer)
 * - Grounded "Ask Your Document" Assistant
 * - Structured Smart Summaries & Translation
 * - Multi-Image Processing (Batch Upload Queue)
 * - Duplicate Detection & Sensitive Data (PII) Warning
 * - Persistent History & Analytics Dashboard
 * - Contextual Exports: Calendar (.ics), Excel (.xlsx), CSV, JSON, Print
 */

(function () {
  'use strict';

  // Global Application State
  const state = {
    currentScreen: 'upload', // 'upload' | 'processing' | 'results' | 'history' | 'dashboard' | 'how-it-works'
    currentFile: null,
    currentImageUrl: null,
    docId: null,
    docType: null,
    language: 'English',
    confidence: 1.0,
    fieldConfidence: {},
    aiExtractedData: null,     // Immutable AI baseline
    currentWorkingData: null,  // Live editable state
    verifiedData: null,        // Approved verified state
    verificationStatus: 'ai_generated', // 'verified' | 'needs_review' | 'warning' | 'ai_generated'
    verificationReport: null,
    sensitiveDataInfo: null,
    duplicateInfo: null,
    versions: [],
    zoomLevel: 100,
    isRawJsonVisible: false,
    isVerifyHighlightActive: false,
    stepperTimer: null,
    
    // Batch processing
    batchQueue: [],
    batchIndex: 0,
    isBatchProcessing: false,
    
    // History & Search
    historyDocs: [],
    historyFilter: {
      q: '',
      docType: 'all',
      status: 'all',
      language: 'all',
      sort: 'newest'
    }
  };

  // DOM Elements Cache
  const DOM = {
    // Top Nav
    brandLogo: document.getElementById('brand-logo'),
    navUpload: document.getElementById('nav-upload'),
    navHistory: document.getElementById('nav-history'),
    navDashboard: document.getElementById('nav-dashboard'),
    navHowItWorks: document.getElementById('nav-how-it-works'),
    navHistoryCount: document.getElementById('nav-history-count'),
    navNewBtn: document.getElementById('nav-new-btn'),
    
    // Screens
    screenUpload: document.getElementById('screen-upload'),
    screenProcessing: document.getElementById('screen-processing'),
    screenResults: document.getElementById('screen-results'),
    screenHistory: document.getElementById('screen-history'),
    screenDashboard: document.getElementById('screen-dashboard'),
    screenHowItWorks: document.getElementById('screen-how-it-works'),
    
    // Upload Screen
    dropZone: document.getElementById('drop-zone'),
    fileInput: document.getElementById('file-input'),
    browseBtn: document.getElementById('browse-btn'),
    sampleTimetable: document.getElementById('sample-timetable'),
    sampleReceipt: document.getElementById('sample-receipt'),
    sampleNotice: document.getElementById('sample-notice'),
    uploadDuplicateBanner: document.getElementById('upload-duplicate-banner'),
    uploadDuplicateMsg: document.getElementById('upload-duplicate-msg'),
    dupViewExistingBtn: document.getElementById('dup-view-existing-btn'),
    dupProcessAnywayBtn: document.getElementById('dup-process-anyway-btn'),
    
    // Batch Processing
    batchQueueContainer: document.getElementById('batch-queue-container'),
    batchProgressText: document.getElementById('batch-progress-text'),
    batchProgressBar: document.getElementById('batch-progress-bar'),
    batchQueueItems: document.getElementById('batch-queue-items'),
    batchCancelBtn: document.getElementById('batch-cancel-btn'),
    
    // Processing Stepper
    step1: document.getElementById('step-1'),
    step2: document.getElementById('step-2'),
    step3: document.getElementById('step-3'),
    step4: document.getElementById('step-4'),
    divider1: document.getElementById('divider-1'),
    divider2: document.getElementById('divider-2'),
    divider3: document.getElementById('divider-3'),
    
    // Results Screen Toolbar
    toolbarBackBtn: document.getElementById('toolbar-back-btn'),
    verifyImageBtn: document.getElementById('verify-image-btn'),
    versionHistoryBtn: document.getElementById('version-history-btn'),
    versionBadgeText: document.getElementById('version-badge-text'),
    askDocBtn: document.getElementById('ask-doc-btn'),
    summaryBtn: document.getElementById('summary-btn'),
    translateBtn: document.getElementById('translate-btn'),
    verifySaveBtn: document.getElementById('verify-save-btn'),
    bottomVerifyBtn: document.getElementById('bottom-verify-btn'),
    
    // Export Dropdown
    exportCenterBtn: document.getElementById('export-center-btn'),
    exportDropdownMenu: document.getElementById('export-dropdown-menu'),
    exportOptIcs: document.getElementById('export-opt-ics'),
    exportOptExcel: document.getElementById('export-opt-excel'),
    exportOptCsv: document.getElementById('export-opt-csv'),
    exportOptJson: document.getElementById('export-opt-json'),
    exportOptPrint: document.getElementById('export-opt-print'),
    
    // Banners & Raw JSON
    sensitiveDataBanner: document.getElementById('sensitive-data-banner'),
    sensitiveDataMsg: document.getElementById('sensitive-data-msg'),
    rawJsonPanel: document.getElementById('raw-json-panel'),
    rawJsonContent: document.getElementById('raw-json-content'),
    copyJsonBtn: document.getElementById('copy-json-btn'),
    closeRawJsonBtn: document.getElementById('close-raw-json-btn'),
    
    // Left Image Preview
    previewFilename: document.getElementById('preview-filename'),
    previewViewport: document.getElementById('preview-viewport'),
    previewImage: document.getElementById('preview-image'),
    zoomInBtn: document.getElementById('zoom-in-btn'),
    zoomOutBtn: document.getElementById('zoom-out-btn'),
    zoomResetBtn: document.getElementById('zoom-reset-btn'),
    zoomLevelText: document.getElementById('zoom-level-text'),
    
    // Right Editor
    badgeDocType: document.getElementById('badge-doc-type'),
    badgeLanguage: document.getElementById('badge-language'),
    badgeVerificationStatus: document.getElementById('badge-verification-status'),
    badgeConfidence: document.getElementById('badge-confidence'),
    badgeConfidenceDot: document.getElementById('badge-confidence-dot'),
    badgeConfidenceText: document.getElementById('badge-confidence-text'),
    
    // Verification Agent Report Card
    verificationCard: document.getElementById('verification-card'),
    vcardStatusIcon: document.getElementById('vcard-status-icon'),
    vcardTitle: document.getElementById('vcard-title'),
    vcardSummary: document.getElementById('vcard-summary'),
    vcardScoreValue: document.getElementById('vcard-score-value'),
    vcardIssuesList: document.getElementById('vcard-issues-list'),
    vcardPassedList: document.getElementById('vcard-passed-list'),
    
    summaryCards: document.getElementById('summary-cards'),
    dynamicFormArea: document.getElementById('dynamic-form-area'),
    
    // Feedback
    feedbackCard: document.getElementById('feedback-card'),
    fbYesBtn: document.getElementById('fb-yes-btn'),
    fbNoBtn: document.getElementById('fb-no-btn'),
    feedbackReasons: document.getElementById('feedback-reasons'),
    fbSubmitBtn: document.getElementById('fb-submit-btn'),
    feedbackThanks: document.getElementById('feedback-thanks'),
    
    // Action Panel
    actionPanelHeading: document.getElementById('action-panel-heading'),
    actionPanelSubheading: document.getElementById('action-panel-subheading'),
    bottomActionBtn: document.getElementById('bottom-action-btn'),
    bottomActionText: document.getElementById('bottom-action-text'),
    bottomActionIcon: document.getElementById('bottom-action-icon'),
    
    // History Screen
    historySearchInput: document.getElementById('history-search-input'),
    filterDocType: document.getElementById('filter-doc-type'),
    filterStatus: document.getElementById('filter-status'),
    filterLanguage: document.getElementById('filter-language'),
    filterSort: document.getElementById('filter-sort'),
    historyItemsContainer: document.getElementById('history-items-container'),
    historyEmptyState: document.getElementById('history-empty-state'),
    historyUploadBtn: document.getElementById('history-upload-btn'),
    emptyUploadBtn: document.getElementById('empty-upload-btn'),
    
    // Dashboard Screen
    metricTotalDocs: document.getElementById('metric-total-docs'),
    metricVerifiedDocs: document.getElementById('metric-verified-docs'),
    metricVerifiedSub: document.getElementById('metric-verified-sub'),
    metricCorrectedDocs: document.getElementById('metric-corrected-docs'),
    metricReviewDocs: document.getElementById('metric-review-docs'),
    metricAvgConf: document.getElementById('metric-avg-conf'),
    typeDistributionList: document.getElementById('type-distribution-list'),
    
    // Modals
    modalVersions: document.getElementById('modal-versions'),
    modalVersionsClose: document.getElementById('modal-versions-close'),
    modalVersionsDismiss: document.getElementById('modal-versions-dismiss'),
    versionsTimeline: document.getElementById('versions-timeline'),
    diffTableWrap: document.getElementById('diff-table-wrap'),
    
    modalAsk: document.getElementById('modal-ask'),
    modalAskClose: document.getElementById('modal-ask-close'),
    askChipsRow: document.getElementById('ask-chips-row'),
    askChatHistory: document.getElementById('ask-chat-history'),
    askInput: document.getElementById('ask-input'),
    askSubmitBtn: document.getElementById('ask-submit-btn'),
    
    modalSummary: document.getElementById('modal-summary'),
    modalSummaryClose: document.getElementById('modal-summary-close'),
    summaryCloseBtn: document.getElementById('summary-close-btn'),
    summaryCopyBtn: document.getElementById('summary-copy-btn'),
    summaryLoading: document.getElementById('summary-loading'),
    summaryContent: document.getElementById('summary-content'),
    summaryPointsList: document.getElementById('summary-points-list'),
    sumDate: document.getElementById('sum-date'),
    sumTime: document.getElementById('sum-time'),
    sumVenue: document.getElementById('sum-venue'),
    sumDeadline: document.getElementById('sum-deadline'),
    
    modalTranslate: document.getElementById('modal-translate'),
    modalTranslateClose: document.getElementById('modal-translate-close'),
    modalTranslateDismiss: document.getElementById('modal-translate-dismiss'),
    translateLangSelect: document.getElementById('translate-lang-select'),
    translateSubmitBtn: document.getElementById('translate-submit-btn'),
    transOrigLang: document.getElementById('trans-orig-lang'),
    transOrigContent: document.getElementById('trans-orig-content'),
    transTargetLang: document.getElementById('trans-target-lang'),
    transResultContent: document.getElementById('trans-result-content'),
    
    // Notifications & Banners
    responsibleAiBanner: document.getElementById('responsible-ai-banner'),
    aiBannerDismiss: document.getElementById('ai-banner-dismiss'),
    errorBanner: document.getElementById('error-banner'),
    errorMessage: document.getElementById('error-message'),
    errorCloseBtn: document.getElementById('error-close-btn'),
    toastContainer: document.getElementById('toast-container')
  };

  // =========================================================================
  // INITIALIZATION
  // =========================================================================

  function init() {
    setupNavigation();
    setupUploadHandlers();
    setupSampleHandlers();
    setupZoomControls();
    setupActionHandlers();
    setupGlobalPaste();
    setupHistoryHandlers();
    setupModalHandlers();
    setupExportDropdown();
    refreshHistoryCount();
    loadHistory();
  }

  // =========================================================================
  // NAVIGATION & SCREEN SWITCHING
  // =========================================================================

  function setupNavigation() {
    const navItems = [
      { el: DOM.navUpload, screen: 'upload' },
      { el: DOM.navHistory, screen: 'history' },
      { el: DOM.navDashboard, screen: 'dashboard' },
      { el: DOM.navHowItWorks, screen: 'how-it-works' }
    ];

    navItems.forEach(item => {
      if (!item.el) return;
      item.el.addEventListener('click', () => {
        showScreen(item.screen);
      });
    });

    if (DOM.brandLogo) {
      DOM.brandLogo.addEventListener('click', () => showScreen('upload'));
    }
    if (DOM.navNewBtn) {
      DOM.navNewBtn.addEventListener('click', () => showScreen('upload'));
    }
    if (DOM.toolbarBackBtn) {
      DOM.toolbarBackBtn.addEventListener('click', () => showScreen('upload'));
    }
    if (DOM.historyUploadBtn) {
      DOM.historyUploadBtn.addEventListener('click', () => showScreen('upload'));
    }
    if (DOM.emptyUploadBtn) {
      DOM.emptyUploadBtn.addEventListener('click', () => showScreen('upload'));
    }
    if (DOM.aiBannerDismiss) {
      DOM.aiBannerDismiss.addEventListener('click', () => {
        if (DOM.responsibleAiBanner) DOM.responsibleAiBanner.style.display = 'none';
      });
    }
  }

  function showScreen(screenName, keepError = false) {
    state.currentScreen = screenName;
    
    // Hide all screen sections
    const screens = [
      DOM.screenUpload,
      DOM.screenProcessing,
      DOM.screenResults,
      DOM.screenHistory,
      DOM.screenDashboard,
      DOM.screenHowItWorks
    ];
    screens.forEach(s => s && s.classList.add('hidden'));

    // Update active nav links
    const navs = [DOM.navUpload, DOM.navHistory, DOM.navDashboard, DOM.navHowItWorks];
    navs.forEach(n => n && n.classList.remove('active'));

    if (screenName === 'upload') {
      if (DOM.screenUpload) DOM.screenUpload.classList.remove('hidden');
      if (DOM.navUpload) DOM.navUpload.classList.add('active');
      if (DOM.navNewBtn) DOM.navNewBtn.classList.add('hidden');
    } else if (screenName === 'processing') {
      if (DOM.screenProcessing) DOM.screenProcessing.classList.remove('hidden');
      if (DOM.navNewBtn) DOM.navNewBtn.classList.add('hidden');
      startProcessingAnimation();
    } else if (screenName === 'results') {
      if (DOM.screenResults) DOM.screenResults.classList.remove('hidden');
      if (DOM.navNewBtn) DOM.navNewBtn.classList.remove('hidden');
      stopProcessingAnimation();
      renderResults();
    } else if (screenName === 'history') {
      if (DOM.screenHistory) DOM.screenHistory.classList.remove('hidden');
      if (DOM.navHistory) DOM.navHistory.classList.add('active');
      if (DOM.navNewBtn) DOM.navNewBtn.classList.remove('hidden');
      loadHistory();
    } else if (screenName === 'dashboard') {
      if (DOM.screenDashboard) DOM.screenDashboard.classList.remove('hidden');
      if (DOM.navDashboard) DOM.navDashboard.classList.add('active');
      if (DOM.navNewBtn) DOM.navNewBtn.classList.remove('hidden');
      loadDashboard();
    } else if (screenName === 'how-it-works') {
      if (DOM.screenHowItWorks) DOM.screenHowItWorks.classList.remove('hidden');
      if (DOM.navHowItWorks) DOM.navHowItWorks.classList.add('active');
      if (DOM.navNewBtn) DOM.navNewBtn.classList.remove('hidden');
    }

    if (!keepError) hideError();
  }

  function resetUploadState() {
    if (state.currentImageUrl && !state.currentImageUrl.startsWith('data:')) {
      try { URL.revokeObjectURL(state.currentImageUrl); } catch (e) {}
    }
    state.currentFile = null;
    state.currentImageUrl = null;
    state.docId = null;
    state.docType = null;
    state.aiExtractedData = null;
    state.currentWorkingData = null;
    state.verifiedData = null;
    state.verificationReport = null;
    state.sensitiveDataInfo = null;
    state.duplicateInfo = null;
    state.versions = [];
    state.zoomLevel = 100;
    state.isVerifyHighlightActive = false;
    
    if (DOM.fileInput) DOM.fileInput.value = '';
    if (DOM.previewImage) DOM.previewImage.src = '';
    if (DOM.rawJsonPanel) DOM.rawJsonPanel.classList.add('hidden');
    if (DOM.uploadDuplicateBanner) DOM.uploadDuplicateBanner.classList.add('hidden');
  }

  // =========================================================================
  // UPLOAD & MULTI-IMAGE HANDLERS
  // =========================================================================

  function setupUploadHandlers() {
    if (DOM.fileInput) {
      DOM.fileInput.addEventListener('click', (e) => e.stopPropagation());
      DOM.fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
          handleFilesSelection(Array.from(e.target.files));
        }
      });
    }

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

    if (DOM.dropZone) {
      DOM.dropZone.addEventListener('click', (e) => {
        if (e.target === DOM.fileInput) return;
        if (DOM.browseBtn && (e.target === DOM.browseBtn || DOM.browseBtn.contains(e.target))) return;
        if (DOM.fileInput) {
          DOM.fileInput.value = '';
          DOM.fileInput.click();
        }
      });

      DOM.dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (DOM.fileInput) {
            DOM.fileInput.value = '';
            DOM.fileInput.click();
          }
        }
      });

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
          handleFilesSelection(Array.from(dt.files));
        }
      });
    }

    window.addEventListener('dragover', (e) => e.preventDefault(), false);
    window.addEventListener('drop', (e) => e.preventDefault(), false);

    if (DOM.errorCloseBtn) {
      DOM.errorCloseBtn.addEventListener('click', hideError);
    }

    // Duplicate Banner buttons
    if (DOM.dupViewExistingBtn) {
      DOM.dupViewExistingBtn.addEventListener('click', () => {
        if (state.duplicateInfo && state.duplicateInfo.existing_id) {
          openDocumentById(state.duplicateInfo.existing_id);
        }
      });
    }
    if (DOM.dupProcessAnywayBtn) {
      DOM.dupProcessAnywayBtn.addEventListener('click', () => {
        if (DOM.uploadDuplicateBanner) DOM.uploadDuplicateBanner.classList.add('hidden');
        showScreen('results');
      });
    }

    // Batch clear
    if (DOM.batchCancelBtn) {
      DOM.batchCancelBtn.addEventListener('click', () => {
        state.batchQueue = [];
        state.isBatchProcessing = false;
        if (DOM.batchQueueContainer) DOM.batchQueueContainer.classList.add('hidden');
      });
    }
  }

  function setupGlobalPaste() {
    window.addEventListener('paste', (e) => {
      const clipboardData = e.clipboardData || window.clipboardData;
      if (!clipboardData) return;

      if (clipboardData.items && clipboardData.items.length > 0) {
        for (let i = 0; i < clipboardData.items.length; i++) {
          const item = clipboardData.items[i];
          if (item.type && item.type.indexOf('image') !== -1) {
            let file = item.getAsFile();
            if (file) {
              const ext = file.type === 'image/jpeg' ? 'jpg' : (file.type === 'image/webp' ? 'webp' : 'png');
              file = new File([file], `screenshot_${Date.now()}.${ext}`, { type: file.type || 'image/png' });
              showToast('Pasted screenshot from clipboard!', 'success');
              handleFilesSelection([file]);
              return;
            }
          }
        }
      }
    });
  }

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
          processSingleDocument(file);
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

  function handleFilesSelection(files) {
    if (!files || files.length === 0) return;

    const validMimes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    const validExts = ['png', 'jpg', 'jpeg', 'webp'];
    const validFiles = files.filter(f => {
      const ext = f.name ? f.name.split('.').pop().toLowerCase() : '';
      return validExts.includes(ext) || validMimes.includes((f.type || '').toLowerCase());
    });

    if (validFiles.length === 0) {
      showError("Please upload supported image formats: PNG, JPG, JPEG, or WEBP.");
      return;
    }

    if (validFiles.length === 1) {
      processSingleDocument(validFiles[0]);
    } else {
      // Batch mode
      startBatchProcessing(validFiles);
    }
  }

  // =========================================================================
  // BATCH MULTI-IMAGE PROCESSING
  // =========================================================================

  async function startBatchProcessing(files) {
    state.batchQueue = files.map((f, idx) => ({
      file: f,
      index: idx,
      status: 'pending',
      result: null
    }));
    state.batchIndex = 0;
    state.isBatchProcessing = true;

    if (DOM.batchQueueContainer) DOM.batchQueueContainer.classList.remove('hidden');
    renderBatchQueueUI();

    for (let i = 0; i < state.batchQueue.length; i++) {
      state.batchIndex = i;
      const item = state.batchQueue[i];
      item.status = 'processing';
      renderBatchQueueUI();

      try {
        const result = await uploadAndExtract(item.file);
        item.status = result.verification_status === 'verified' ? 'verified' : (result.verification_status === 'warning' ? 'warning' : 'needs_review');
        item.result = result;
      } catch (e) {
        item.status = 'error';
        item.error = e.message;
      }
      renderBatchQueueUI();
    }

    state.isBatchProcessing = false;
    refreshHistoryCount();
    
    // Select first processed item
    const firstSuccessful = state.batchQueue.find(b => b.result);
    if (firstSuccessful) {
      loadBatchResultIntoState(firstSuccessful);
      showScreen('results');
      showToast(`Batch completed: ${state.batchQueue.length} documents processed!`, 'success');
    }
  }

  function renderBatchQueueUI() {
    if (!DOM.batchQueueItems) return;
    const total = state.batchQueue.length;
    const processed = state.batchQueue.filter(b => b.status !== 'pending' && b.status !== 'processing').length;
    
    if (DOM.batchProgressText) {
      DOM.batchProgressText.textContent = state.isBatchProcessing ? 
        `Processing ${state.batchIndex + 1} of ${total}...` : 
        `Completed: ${processed} of ${total} Documents`;
    }
    if (DOM.batchProgressBar) {
      const pct = Math.round((processed / total) * 100);
      DOM.batchProgressBar.style.width = `${pct}%`;
    }

    DOM.batchQueueItems.innerHTML = '';
    state.batchQueue.forEach((item, idx) => {
      const chip = document.createElement('div');
      chip.className = `batch-queue-chip ${idx === state.batchIndex ? 'active' : ''}`;
      
      let icon = '⏳';
      if (item.status === 'processing') icon = '🔄';
      else if (item.status === 'verified') icon = '🟢';
      else if (item.status === 'needs_review') icon = '🟡';
      else if (item.status === 'warning') icon = '🔴';
      else if (item.status === 'error') icon = '❌';

      chip.innerHTML = `<span>${icon}</span> <span>${escapeHtml(item.file.name)}</span>`;
      chip.addEventListener('click', () => {
        if (item.result) {
          loadBatchResultIntoState(item);
          showScreen('results');
        }
      });
      DOM.batchQueueItems.appendChild(chip);
    });
  }

  function loadBatchResultIntoState(batchItem) {
    const res = batchItem.result;
    state.currentFile = batchItem.file;
    state.currentImageUrl = res.thumbnail || URL.createObjectURL(batchItem.file);
    state.docId = res.id;
    state.docType = res.doc_type;
    state.language = res.language || 'English';
    state.confidence = res.confidence || 0.95;
    state.fieldConfidence = res.field_confidence || {};
    state.aiExtractedData = JSON.parse(JSON.stringify(res.data || {}));
    state.currentWorkingData = JSON.parse(JSON.stringify(res.data || {}));
    state.verifiedData = res.verified_data || null;
    state.verificationStatus = res.verification_status || 'ai_generated';
    state.verificationReport = res.verification_report || null;
    state.sensitiveDataInfo = res.sensitive_data_info || null;
    state.versions = res.versions || [];
  }

  // =========================================================================
  // SINGLE DOCUMENT EXTRACTION
  // =========================================================================

  function startProcessingAnimation() {
    DOM.step1.className = 'step-item active';
    DOM.step2.className = 'step-item';
    DOM.step3.className = 'step-item';
    DOM.step4.className = 'step-item';
    DOM.divider1.className = 'step-divider';
    DOM.divider2.className = 'step-divider';
    DOM.divider3.className = 'step-divider';

    state.stepperTimer = setTimeout(() => {
      DOM.step1.className = 'step-item completed';
      DOM.divider1.className = 'step-divider active';
      DOM.step2.className = 'step-item active';

      state.stepperTimer = setTimeout(() => {
        DOM.step2.className = 'step-item completed';
        DOM.divider2.className = 'step-divider active';
        DOM.step3.className = 'step-item active';
        
        state.stepperTimer = setTimeout(() => {
          DOM.step3.className = 'step-item completed';
          DOM.divider3.className = 'step-divider active';
          DOM.step4.className = 'step-item active';
        }, 1200);
      }, 1400);
    }, 1000);
  }

  function stopProcessingAnimation() {
    if (state.stepperTimer) {
      clearTimeout(state.stepperTimer);
      state.stepperTimer = null;
    }
  }

  async function uploadAndExtract(file) {
    const formData = new FormData();
    formData.append('image', file);

    const response = await fetch('/extract', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `Server responded with status ${response.status}`);
    }
    return result;
  }

  async function processSingleDocument(file) {
    state.currentFile = file;
    state.currentImageUrl = URL.createObjectURL(file);
    showScreen('processing');

    try {
      const result = await uploadAndExtract(file);

      // Finish stepper
      DOM.step4.className = 'step-item completed';

      // Save into state
      state.docId = result.id;
      state.docType = result.doc_type;
      state.language = result.language || 'English';
      state.confidence = typeof result.confidence === 'number' ? result.confidence : 0.95;
      state.fieldConfidence = result.field_confidence || {};
      state.aiExtractedData = JSON.parse(JSON.stringify(result.data || {}));
      state.currentWorkingData = JSON.parse(JSON.stringify(result.data || {}));
      state.verifiedData = result.verified_data || null;
      state.verificationStatus = result.verification_status || 'ai_generated';
      state.verificationReport = result.verification_report || null;
      state.sensitiveDataInfo = result.sensitive_data_info || null;
      state.duplicateInfo = result.duplicate_info || null;
      state.versions = result.versions || [];

      // Check if duplicate found
      if (result.duplicate_info && result.duplicate_info.found) {
        if (DOM.uploadDuplicateBanner && DOM.uploadDuplicateMsg) {
          DOM.uploadDuplicateMsg.textContent = `A similar document "${result.duplicate_info.existing_filename}" was uploaded on ${new Date(result.duplicate_info.created_at).toLocaleDateString()}.`;
          DOM.uploadDuplicateBanner.classList.remove('hidden');
        }
      }

      if (result._demo_mode && result._note) {
        showToast(result._note, 'success', 4500);
      }

      refreshHistoryCount();

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
  // RESULTS SCREEN: RENDERING & VERIFICATION AGENT
  // =========================================================================

  function renderResults() {
    // 1. Image preview
    DOM.previewImage.src = state.currentImageUrl;
    DOM.previewFilename.textContent = state.currentFile ? state.currentFile.name : 'document.png';
    setZoom(100);

    // 2. Metadata Badges
    const docTypeLabels = {
      'timetable': 'Timetable Schedule',
      'receipt': 'Purchase Receipt',
      'notice': 'Official Notice',
      'poster': 'Event Poster',
      'other': 'Structured Document'
    };
    DOM.badgeDocType.textContent = docTypeLabels[state.docType] || state.docType;
    DOM.badgeLanguage.textContent = state.language;

    // AI Confidence Badge
    const confPercent = Math.round(state.confidence * 100);
    DOM.badgeConfidenceText.textContent = `AI Confidence: ${confPercent}%`;
    DOM.badgeConfidence.className = 'confidence-badge';
    if (state.confidence >= 0.85) DOM.badgeConfidence.classList.add('high');
    else if (state.confidence >= 0.70) DOM.badgeConfidence.classList.add('mid');
    else DOM.badgeConfidence.classList.add('low');

    // Verification Status Badge
    updateVerificationStatusBadge();

    // Sensitive Data Banner
    if (state.sensitiveDataInfo && state.sensitiveDataInfo.has_sensitive_data) {
      DOM.sensitiveDataBanner.classList.remove('hidden');
      DOM.sensitiveDataMsg.textContent = state.sensitiveDataInfo.alert_message || "Contains personal details (e.g. phone, email, or IDs).";
    } else {
      DOM.sensitiveDataBanner.classList.add('hidden');
    }

    // 3. Verification Agent Report Card
    renderVerificationAgentCard();

    // 4. Summary Stats Grid
    renderSummaryStats();

    // 5. Dynamic Form / Table Area
    renderDynamicForm();

    // 6. Action Panel Buttons
    updateActionPanel();

    // 7. Raw JSON View
    updateRawJsonView();
  }

  function updateVerificationStatusBadge() {
    if (!DOM.badgeVerificationStatus) return;
    const status = state.verificationStatus;
    DOM.badgeVerificationStatus.className = 'status-pill';

    if (status === 'verified') {
      DOM.badgeVerificationStatus.classList.add('status-pill-verified');
      DOM.badgeVerificationStatus.textContent = '🟢 Verified';
      if (DOM.versionBadgeText) DOM.versionBadgeText.textContent = 'Version 3 (Verified)';
    } else if (status === 'warning') {
      DOM.badgeVerificationStatus.classList.add('status-pill-warning');
      DOM.badgeVerificationStatus.textContent = '🔴 Verification Warning';
    } else if (status === 'needs_review') {
      DOM.badgeVerificationStatus.classList.add('status-pill-needs-review');
      DOM.badgeVerificationStatus.textContent = '🟡 Needs Review';
    } else {
      DOM.badgeVerificationStatus.classList.add('status-pill-ai');
      DOM.badgeVerificationStatus.textContent = '🔵 AI Generated';
    }
  }

  function renderVerificationAgentCard() {
    const report = state.verificationReport;
    if (!report) {
      if (DOM.verificationCard) DOM.verificationCard.classList.add('hidden');
      return;
    }
    DOM.verificationCard.classList.remove('hidden');

    const score = report.score || 95;
    DOM.vcardScoreValue.textContent = score;
    DOM.vcardScoreValue.className = `vcard-score ${score >= 85 ? '' : (score >= 70 ? 'mid' : 'low')}`;

    DOM.vcardTitle.textContent = `Verification Agent Audit (${report.status.toUpperCase().replace('_', ' ')})`;
    DOM.vcardSummary.textContent = report.summary_text || "Automated consistency and rule verification.";

    // Status icon class
    DOM.vcardStatusIcon.className = `vcard-icon-wrap ${report.status}`;

    // Issues list
    DOM.vcardIssuesList.innerHTML = '';
    const issues = report.issues || [];
    issues.forEach(issue => {
      const item = document.createElement('div');
      item.className = `vcard-issue-item ${issue.severity}`;
      item.innerHTML = `
        <div class="vcard-issue-text">
          <span class="vcard-issue-title">⚠️ ${escapeHtml(issue.message)}</span>
          <span class="vcard-issue-desc">${escapeHtml(issue.details || '')}</span>
        </div>
      `;
      DOM.vcardIssuesList.appendChild(item);
    });

    // Passed checks list
    DOM.vcardPassedList.innerHTML = '';
    const passed = report.passed_checks || [];
    passed.forEach(chk => {
      const p = document.createElement('div');
      p.className = 'vcard-passed-item';
      p.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg> <span>${escapeHtml(chk)}</span>`;
      DOM.vcardPassedList.appendChild(p);
    });
  }

  function renderSummaryStats() {
    DOM.summaryCards.innerHTML = '';
    const data = state.currentWorkingData;
    if (!data) return;

    if (state.docType === 'timetable') {
      const entries = data.entries || [];
      const days = new Set(entries.map(e => e.day).filter(Boolean));
      const rooms = new Set(entries.map(e => e.room).filter(Boolean));
      addStatCard('Classes Found', `${entries.length} Sessions`);
      addStatCard('Active Days', `${days.size} Days`);
      addStatCard('Rooms / Venues', `${rooms.size} Locations`);
    } else if (state.docType === 'receipt') {
      const items = data.items || [];
      const curr = data.currency || '₹';
      const total = data.total !== undefined ? `${curr} ${Number(data.total).toLocaleString('en-IN')}` : 'N/A';
      addStatCard('Merchant', data.merchant || 'Store');
      addStatCard('Total Amount', total);
      addStatCard('Line Items', `${items.length} Items`);
      addStatCard('Category', data.category || 'General');
    } else if (state.docType in ('notice', 'poster')) {
      addStatCard('Event Date', data.date || 'Upcoming');
      addStatCard('Timings', (data.start_time && data.end_time) ? `${data.start_time} - ${data.end_time}` : (data.start_time || 'All Day'));
      addStatCard('Venue', data.venue ? (data.venue.length > 20 ? data.venue.substring(0, 18) + '...' : data.venue) : 'Not specified');
    } else {
      addStatCard('Fields Detected', `${Object.keys(data).length} Fields`);
      addStatCard('Confidence', `${Math.round(state.confidence * 100)}%`);
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

  // =========================================================================
  // DYNAMIC FORM / TABLE RENDERING & TWO-WAY BINDING
  // =========================================================================

  function renderDynamicForm() {
    DOM.dynamicFormArea.innerHTML = '';
    const data = state.currentWorkingData;
    if (!data) return;

    if (state.docType === 'timetable') {
      renderTimetableForm(data);
    } else if (state.docType === 'receipt') {
      renderReceiptForm(data);
    } else if (state.docType in ('notice', 'poster')) {
      renderNoticeForm(data);
    } else {
      renderOtherDocumentForm(data);
    }
  }

  // 1. Timetable Form
  function renderTimetableForm(data) {
    const container = document.createElement('div');
    const titleConf = getFieldConfidence('title');

    container.innerHTML = `
      <div class="form-group" id="group-tb-title">
        <div class="form-label-row">
          <label class="form-label" for="tb-title">Schedule / Institution Title</label>
          ${renderConfidenceBadge(titleConf)}
        </div>
        <div class="form-input-wrapper">
          <input type="text" id="tb-title" class="form-input ${titleConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.title || '')}" placeholder="e.g. Semester IV Schedule">
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
                <th style="width: 130px;">Day</th>
                <th style="width: 105px;">Start</th>
                <th style="width: 105px;">End</th>
                <th>Subject / Course</th>
                <th style="width: 125px;">Room / Lab</th>
                <th style="width: 140px;">Faculty</th>
                <th style="width: 44px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="timetable-rows"></tbody>
          </table>
        </div>

        <div class="table-footer-actions">
          <button type="button" class="btn btn-secondary btn-sm" id="tb-add-row-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            <span>Add Class Entry</span>
          </button>
          <span class="footer-tip">Rows automatically sort into recurring weekly calendar events (.ics).</span>
        </div>
      </div>
    `;

    DOM.dynamicFormArea.appendChild(container);

    const titleInput = container.querySelector('#tb-title');
    titleInput.addEventListener('input', (e) => {
      data.title = e.target.value;
      onDataFieldEdited();
    });

    const tbody = container.querySelector('#timetable-rows');
    (data.entries || []).forEach((entry, idx) => {
      renderTimetableRow(tbody, entry, idx);
    });

    const addRowBtn = container.querySelector('#tb-add-row-btn');
    addRowBtn.addEventListener('click', () => {
      if (!data.entries) data.entries = [];
      const newEntry = { subject: "New Class", day: "Monday", start_time: "09:00", end_time: "10:00", room: "Room 101", faculty: "" };
      data.entries.push(newEntry);
      renderTimetableRow(tbody, newEntry, data.entries.length - 1);
      updateTimetableMeta();
      onDataFieldEdited();
    });
  }

  function renderTimetableRow(tbody, entry, index) {
    const tr = document.createElement('tr');
    tr.dataset.index = index;

    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    const dayOptions = days.map(d => `<option value="${d}" ${d.toLowerCase() === (entry.day || '').toLowerCase() ? 'selected' : ''}>${d}</option>`).join('');

    const subConf = getFieldConfidence('entries.subject');
    const startConf = getFieldConfidence('entries.start_time');
    const endConf = getFieldConfidence('entries.end_time');
    const roomConf = getFieldConfidence('entries.room');

    tr.innerHTML = `
      <td><select class="form-select table-input row-day">${dayOptions}</select></td>
      <td><input type="time" class="table-input row-start ${startConf < 0.7 ? 'low-conf' : ''}" value="${entry.start_time || '09:00'}"></td>
      <td><input type="time" class="table-input row-end ${endConf < 0.7 ? 'low-conf' : ''}" value="${entry.end_time || '10:00'}"></td>
      <td><input type="text" class="table-input row-subject ${subConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(entry.subject || '')}" placeholder="Subject"></td>
      <td><input type="text" class="table-input row-room ${roomConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(entry.room || '')}" placeholder="Room"></td>
      <td><input type="text" class="table-input row-faculty" value="${escapeHtml(entry.faculty || '')}" placeholder="Faculty"></td>
      <td style="text-align: right;">
        <button type="button" class="btn-delete-row" title="Delete class row" aria-label="Delete class row">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </td>
    `;

    const daySelect = tr.querySelector('.row-day');
    const startInput = tr.querySelector('.row-start');
    const endInput = tr.querySelector('.row-end');
    const subjectInput = tr.querySelector('.row-subject');
    const roomInput = tr.querySelector('.row-room');
    const facultyInput = tr.querySelector('.row-faculty');
    const deleteBtn = tr.querySelector('.btn-delete-row');

    daySelect.addEventListener('change', (e) => { entry.day = e.target.value; onDataFieldEdited(); });
    startInput.addEventListener('input', (e) => { entry.start_time = e.target.value; onDataFieldEdited(); });
    endInput.addEventListener('input', (e) => { entry.end_time = e.target.value; onDataFieldEdited(); });
    subjectInput.addEventListener('input', (e) => { entry.subject = e.target.value; onDataFieldEdited(); });
    roomInput.addEventListener('input', (e) => { entry.room = e.target.value; onDataFieldEdited(); });
    facultyInput.addEventListener('input', (e) => { entry.faculty = e.target.value; onDataFieldEdited(); });

    deleteBtn.addEventListener('click', () => {
      const idx = state.currentWorkingData.entries.indexOf(entry);
      if (idx !== -1) {
        state.currentWorkingData.entries.splice(idx, 1);
        tr.remove();
        updateTimetableMeta();
        onDataFieldEdited();
      }
    });

    tbody.appendChild(tr);
  }

  function updateTimetableMeta() {
    const countEl = document.getElementById('tb-entry-count');
    if (countEl) {
      countEl.textContent = `${(state.currentWorkingData.entries || []).length} Classes`;
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
        <div class="form-group" id="group-rc-merchant">
          <div class="form-label-row">
            <label class="form-label" for="rc-merchant">Merchant / Store Name</label>
            ${renderConfidenceBadge(merchConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="text" id="rc-merchant" class="form-input ${merchConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.merchant || '')}" placeholder="Store Name">
            <span class="field-dot" style="background-color: ${getConfidenceColor(merchConf)}"></span>
          </div>
        </div>

        <div class="form-group" id="group-rc-date">
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
        <div class="form-group" id="group-rc-total">
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
                <th style="width: 85px;">Qty</th>
                <th style="width: 110px;">Unit Price</th>
                <th style="width: 110px;">Line Total</th>
                <th style="width: 44px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="receipt-rows"></tbody>
          </table>
        </div>

        <div class="table-footer-actions">
          <button type="button" class="btn btn-secondary btn-sm" id="rc-add-item-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            <span>Add Item</span>
          </button>
          <span class="footer-tip">Verification Agent checks line items sum vs total amount.</span>
        </div>
      </div>
    `;

    DOM.dynamicFormArea.appendChild(container);

    const merchInput = container.querySelector('#rc-merchant');
    const dateInput = container.querySelector('#rc-date');
    const totalInput = container.querySelector('#rc-total');
    const curInput = container.querySelector('#rc-currency');
    const catInput = container.querySelector('#rc-category');

    merchInput.addEventListener('input', (e) => { data.merchant = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    dateInput.addEventListener('input', (e) => { data.date = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    totalInput.addEventListener('input', (e) => { data.total = parseFloat(e.target.value) || 0; renderSummaryStats(); onDataFieldEdited(); });
    curInput.addEventListener('input', (e) => { data.currency = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    catInput.addEventListener('input', (e) => { data.category = e.target.value; renderSummaryStats(); onDataFieldEdited(); });

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
      onDataFieldEdited();
    });
  }

  function renderReceiptItemRow(tbody, item, index) {
    const tr = document.createElement('tr');
    tr.dataset.index = index;

    const lineTotal = ((item.qty || 1) * (item.price || 0)).toFixed(2);
    const itemConf = getFieldConfidence('items');

    tr.innerHTML = `
      <td><input type="text" class="table-input item-name ${itemConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(item.name || '')}" placeholder="Item description"></td>
      <td><input type="number" step="1" min="1" class="table-input item-qty" value="${item.qty || 1}"></td>
      <td><input type="number" step="0.01" min="0" class="table-input item-price" value="${item.price !== undefined ? item.price : 0}"></td>
      <td><span class="item-line-total" style="font-weight: 600; padding-left: 0.5rem;">${lineTotal}</span></td>
      <td style="text-align: right;">
        <button type="button" class="btn-delete-row" title="Delete item" aria-label="Delete item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
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

    nameInput.addEventListener('input', (e) => { item.name = e.target.value; onDataFieldEdited(); });
    qtyInput.addEventListener('input', (e) => { item.qty = parseFloat(e.target.value) || 1; updateLine(); onDataFieldEdited(); });
    priceInput.addEventListener('input', (e) => { item.price = parseFloat(e.target.value) || 0; updateLine(); onDataFieldEdited(); });

    deleteBtn.addEventListener('click', () => {
      const idx = state.currentWorkingData.items.indexOf(item);
      if (idx !== -1) {
        state.currentWorkingData.items.splice(idx, 1);
        tr.remove();
        updateReceiptMeta();
        onDataFieldEdited();
      }
    });

    tbody.appendChild(tr);
  }

  function updateReceiptMeta() {
    const countEl = document.getElementById('rc-item-count');
    if (countEl) {
      countEl.textContent = `${(state.currentWorkingData.items || []).length} Items`;
    }
    renderSummaryStats();
  }

  // 3. Notice / Poster Form
  function renderNoticeForm(data) {
    const container = document.createElement('div');
    const titleConf = getFieldConfidence('title');
    const dateConf = getFieldConfidence('date');
    const startConf = getFieldConfidence('start_time');
    const endConf = getFieldConfidence('end_time');
    const venueConf = getFieldConfidence('venue');
    const descConf = getFieldConfidence('description');

    container.innerHTML = `
      <div class="form-group" id="group-nt-title">
        <div class="form-label-row">
          <label class="form-label" for="nt-title">Headline / Title</label>
          ${renderConfidenceBadge(titleConf)}
        </div>
        <div class="form-input-wrapper">
          <input type="text" id="nt-title" class="form-input ${titleConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.title || '')}" placeholder="Notice Headline">
          <span class="field-dot" style="background-color: ${getConfidenceColor(titleConf)}"></span>
        </div>
      </div>

      <div class="form-grid-3">
        <div class="form-group" id="group-nt-date">
          <div class="form-label-row">
            <label class="form-label" for="nt-date">Event Date</label>
            ${renderConfidenceBadge(dateConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="date" id="nt-date" class="form-input ${dateConf < 0.7 ? 'low-conf' : ''}" value="${data.date || ''}">
            <span class="field-dot" style="background-color: ${getConfidenceColor(dateConf)}"></span>
          </div>
        </div>

        <div class="form-group" id="group-nt-start">
          <div class="form-label-row">
            <label class="form-label" for="nt-start">Start Time</label>
            ${renderConfidenceBadge(startConf)}
          </div>
          <div class="form-input-wrapper">
            <input type="time" id="nt-start" class="form-input ${startConf < 0.7 ? 'low-conf' : ''}" value="${data.start_time || '09:30'}">
            <span class="field-dot" style="background-color: ${getConfidenceColor(startConf)}"></span>
          </div>
        </div>

        <div class="form-group" id="group-nt-end">
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

      <div class="form-group" id="group-nt-venue">
        <div class="form-label-row">
          <label class="form-label" for="nt-venue">Venue / Location</label>
          ${renderConfidenceBadge(venueConf)}
        </div>
        <div class="form-input-wrapper">
          <input type="text" id="nt-venue" class="form-input ${venueConf < 0.7 ? 'low-conf' : ''}" value="${escapeHtml(data.venue || '')}" placeholder="Auditorium, Hall, Campus">
          <span class="field-dot" style="background-color: ${getConfidenceColor(venueConf)}"></span>
        </div>
      </div>

      <div class="form-group" id="group-nt-desc">
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

    const titleInput = container.querySelector('#nt-title');
    const dateInput = container.querySelector('#nt-date');
    const startInput = container.querySelector('#nt-start');
    const endInput = container.querySelector('#nt-end');
    const venueInput = container.querySelector('#nt-venue');
    const descInput = container.querySelector('#nt-desc');

    titleInput.addEventListener('input', (e) => { data.title = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    dateInput.addEventListener('input', (e) => { data.date = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    startInput.addEventListener('input', (e) => { data.start_time = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    endInput.addEventListener('input', (e) => { data.end_time = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    venueInput.addEventListener('input', (e) => { data.venue = e.target.value; renderSummaryStats(); onDataFieldEdited(); });
    descInput.addEventListener('input', (e) => { data.description = e.target.value; onDataFieldEdited(); });
  }

  // 4. Other Document Type Form
  function renderOtherDocumentForm(data) {
    const container = document.createElement('div');
    container.innerHTML = `
      <div class="form-group">
        <label class="form-label">Document Key-Value Fields</label>
        <div class="table-container">
          <table class="data-table" id="other-table">
            <thead>
              <tr>
                <th style="width: 200px;">Key</th>
                <th>Extracted Value</th>
              </tr>
            </thead>
            <tbody id="other-rows"></tbody>
          </table>
        </div>
      </div>
    `;

    const tbody = container.querySelector('#other-rows');
    Object.keys(data).forEach(k => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${escapeHtml(k)}</strong></td>
        <td><input type="text" class="table-input" value="${escapeHtml(String(data[k] || ''))}"></td>
      `;
      tr.querySelector('input').addEventListener('input', (e) => {
        data[k] = e.target.value;
        onDataFieldEdited();
      });
      tbody.appendChild(tr);
    });

    DOM.dynamicFormArea.appendChild(container);
  }

  // =========================================================================
  // TWO-WAY BINDING, LIVE EDITS & VERSION CREATION
  // =========================================================================

  let editDebounceTimer = null;
  function onDataFieldEdited() {
    updateRawJsonView();

    // Mark as user edited
    if (state.verificationStatus === 'verified') {
      state.verificationStatus = 'needs_review';
      updateVerificationStatusBadge();
    }

    if (DOM.versionBadgeText) {
      DOM.versionBadgeText.textContent = 'Version 2 (User Edited)';
    }

    clearTimeout(editDebounceTimer);
    editDebounceTimer = setTimeout(async () => {
      if (state.docId) {
        try {
          const res = await fetch(`/api/documents/${state.docId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: state.currentWorkingData })
          });
          if (res.ok) {
            const updated = await res.json();
            state.verificationReport = updated.verification_report;
            state.versions = updated.versions || [];
            renderVerificationAgentCard();
          }
        } catch (e) {}
      }
    }, 800);
  }

  // =========================================================================
  // HUMAN VERIFICATION MODE & "VERIFY AGAINST IMAGE"
  // =========================================================================

  function setupActionHandlers() {
    // "Verify Against Image" button
    if (DOM.verifyImageBtn) {
      DOM.verifyImageBtn.addEventListener('click', () => {
        state.isVerifyHighlightActive = !state.isVerifyHighlightActive;
        const lowConfInputs = document.querySelectorAll('.form-input.low-conf, .table-input.low-conf');
        
        if (state.isVerifyHighlightActive) {
          DOM.verifyImageBtn.classList.add('btn-primary');
          DOM.verifyImageBtn.classList.remove('btn-secondary');
          lowConfInputs.forEach(el => el.classList.add('verify-highlight-active'));
          
          if (lowConfInputs.length > 0) {
            lowConfInputs[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            lowConfInputs[0].focus();
            showToast("Visual Verification Mode Active: Comparing low-confidence fields.", "success");
          } else {
            showToast("All fields have high AI confidence! Inspecting image side-by-side.", "success");
          }
        } else {
          DOM.verifyImageBtn.classList.remove('btn-primary');
          DOM.verifyImageBtn.classList.add('btn-secondary');
          lowConfInputs.forEach(el => el.classList.remove('verify-highlight-active'));
        }
      });
    }

    // Verify & Save buttons
    if (DOM.verifySaveBtn) DOM.verifySaveBtn.addEventListener('click', verifyAndSaveCurrentDocument);
    if (DOM.bottomVerifyBtn) DOM.bottomVerifyBtn.addEventListener('click', verifyAndSaveCurrentDocument);

    // Primary context-aware bottom action button
    if (DOM.bottomActionBtn) {
      DOM.bottomActionBtn.addEventListener('click', () => {
        if (state.docType === 'timetable') triggerCalendarExport();
        else if (state.docType === 'receipt') triggerExcelExport();
        else if (state.docType in ('notice', 'poster')) triggerCalendarExport();
        else triggerCsvExport();
      });
    }

    // Feedback handlers
    if (DOM.fbYesBtn) {
      DOM.fbYesBtn.addEventListener('click', () => {
        DOM.fbYesBtn.classList.add('btn-primary');
        DOM.fbNoBtn.classList.remove('btn-primary');
        DOM.feedbackReasons.classList.add('hidden');
        DOM.feedbackThanks.classList.remove('hidden');
        saveFeedback(true, []);
      });
    }
    if (DOM.fbNoBtn) {
      DOM.fbNoBtn.addEventListener('click', () => {
        DOM.fbNoBtn.classList.add('btn-primary');
        DOM.fbYesBtn.classList.remove('btn-primary');
        DOM.feedbackReasons.classList.remove('hidden');
        DOM.feedbackThanks.classList.add('hidden');
      });
    }
    if (DOM.fbSubmitBtn) {
      DOM.fbSubmitBtn.addEventListener('click', () => {
        const checked = Array.from(DOM.feedbackReasons.querySelectorAll('input:checked')).map(i => i.value);
        saveFeedback(false, checked);
        DOM.feedbackReasons.classList.add('hidden');
        DOM.feedbackThanks.classList.remove('hidden');
      });
    }

    // Raw JSON toggling
    if (DOM.closeRawJsonBtn) {
      DOM.closeRawJsonBtn.addEventListener('click', () => {
        DOM.rawJsonPanel.classList.add('hidden');
      });
    }
    if (DOM.copyJsonBtn) {
      DOM.copyJsonBtn.addEventListener('click', () => {
        const payload = state.verifiedData || state.currentWorkingData;
        navigator.clipboard.writeText(JSON.stringify(payload, null, 2)).then(() => {
          showToast("JSON payload copied to clipboard!", "success");
        });
      });
    }
  }

  async function verifyAndSaveCurrentDocument() {
    if (!state.docId) {
      showToast("Document verified!", "success");
      state.verificationStatus = 'verified';
      updateVerificationStatusBadge();
      return;
    }

    try {
      const response = await fetch(`/api/documents/${state.docId}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: state.currentWorkingData })
      });

      if (!response.ok) throw new Error("Verification failed.");
      const updated = await response.json();
      
      state.verifiedData = JSON.parse(JSON.stringify(state.currentWorkingData));
      state.verificationStatus = 'verified';
      state.versions = updated.versions || [];
      state.verificationReport = updated.verification_report;
      
      updateVerificationStatusBadge();
      renderVerificationAgentCard();
      refreshHistoryCount();
      showToast("Document verified and saved! Version history updated.", "success", 4000);

    } catch (e) {
      showError(e.message || "Could not verify document.");
    }
  }

  async function saveFeedback(isAccurate, issues) {
    if (!state.docId) return;
    try {
      await fetch(`/api/documents/${state.docId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accurate: isAccurate, issues })
      });
    } catch (e) {}
  }

  // =========================================================================
  // VERSION HISTORY & DIFF VIEWER MODAL
  // =========================================================================

  function setupModalHandlers() {
    // 1. Version History Modal
    if (DOM.versionHistoryBtn) {
      DOM.versionHistoryBtn.addEventListener('click', openVersionHistoryModal);
    }
    if (DOM.modalVersionsClose) DOM.modalVersionsClose.addEventListener('click', () => DOM.modalVersions.classList.add('hidden'));
    if (DOM.modalVersionsDismiss) DOM.modalVersionsDismiss.addEventListener('click', () => DOM.modalVersions.classList.add('hidden'));

    // 2. Ask Document Modal
    if (DOM.askDocBtn) DOM.askDocBtn.addEventListener('click', openAskDocModal);
    if (DOM.modalAskClose) DOM.modalAskClose.addEventListener('click', () => DOM.modalAsk.classList.add('hidden'));
    if (DOM.askSubmitBtn) DOM.askSubmitBtn.addEventListener('click', submitAskQuestion);
    if (DOM.askInput) {
      DOM.askInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          submitAskQuestion();
        }
      });
    }

    // 3. Smart Summary Modal
    if (DOM.summaryBtn) DOM.summaryBtn.addEventListener('click', openSummaryModal);
    if (DOM.modalSummaryClose) DOM.modalSummaryClose.addEventListener('click', () => DOM.modalSummary.classList.add('hidden'));
    if (DOM.summaryCloseBtn) DOM.summaryCloseBtn.addEventListener('click', () => DOM.modalSummary.classList.add('hidden'));
    if (DOM.summaryCopyBtn) {
      DOM.summaryCopyBtn.addEventListener('click', () => {
        const text = extractSummaryAsText();
        navigator.clipboard.writeText(text).then(() => {
          showToast("Summary copied to clipboard!", "success");
        });
      });
    }

    // 4. Translate Modal
    if (DOM.translateBtn) DOM.translateBtn.addEventListener('click', openTranslateModal);
    if (DOM.modalTranslateClose) DOM.modalTranslateClose.addEventListener('click', () => DOM.modalTranslate.classList.add('hidden'));
    if (DOM.modalTranslateDismiss) DOM.modalTranslateDismiss.addEventListener('click', () => DOM.modalTranslate.classList.add('hidden'));
    if (DOM.translateSubmitBtn) DOM.translateSubmitBtn.addEventListener('click', submitTranslation);
  }

  async function openVersionHistoryModal() {
    if (!state.docId) {
      showToast("Save document first to view version history.", "info");
      return;
    }
    DOM.modalVersions.classList.remove('hidden');

    try {
      const response = await fetch(`/api/documents/${state.docId}/versions`);
      if (!response.ok) throw new Error("Could not load versions.");
      const data = await response.json();
      
      const versions = data.versions || [];
      renderVersionsTimeline(versions);
      renderDiffTable(data.ai_extracted_data, data.verified_data || data.user_corrected_data || data.ai_extracted_data);
    } catch (e) {
      showError(e.message);
    }
  }

  function renderVersionsTimeline(versions) {
    if (!DOM.versionsTimeline) return;
    DOM.versionsTimeline.innerHTML = '';

    versions.forEach(v => {
      const item = document.createElement('div');
      item.className = 'mini-step';
      const timeStr = new Date(v.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      item.innerHTML = `
        <span class="mini-step-num">${v.version_number}</span>
        <div style="flex: 1;">
          <strong>${escapeHtml(v.version_label)}</strong>
          <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">Created at ${timeStr} by ${escapeHtml(v.changed_by)}</span>
        </div>
      `;
      DOM.versionsTimeline.appendChild(item);
    });
  }

  function renderDiffTable(aiData, finalData) {
    if (!DOM.diffTableWrap) return;
    const diffs = computeDiffList(aiData, finalData);

    if (diffs.length === 0) {
      DOM.diffTableWrap.innerHTML = `
        <div style="padding: 1rem; text-align: center; color: var(--text-muted); font-size: 0.8125rem;">
          No field modifications found. The verified data matches the original AI extraction 100%.
        </div>
      `;
      return;
    }

    let rowsHtml = diffs.map(d => `
      <tr>
        <td><code>${escapeHtml(d.field)}</code></td>
        <td><span class="diff-pill-old">${escapeHtml(String(d.old_value !== null ? d.old_value : 'null'))}</span></td>
        <td>➔</td>
        <td><span class="diff-pill-new">${escapeHtml(String(d.new_value !== null ? d.new_value : 'null'))}</span></td>
      </tr>
    `).join('');

    DOM.diffTableWrap.innerHTML = `
      <table class="diff-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Original AI Value</th>
            <th></th>
            <th>Final Verified Value</th>
          </tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    `;
  }

  function computeDiffList(oldObj, newObj, prefix = '') {
    let diffs = [];
    if (!oldObj || !newObj) return diffs;

    if (typeof oldObj !== 'object' || typeof newObj !== 'object') {
      if (oldObj !== newObj) {
        diffs.push({ field: prefix || 'value', old_value: oldObj, new_value: newObj });
      }
      return diffs;
    }

    const allKeys = Array.from(new Set([...Object.keys(oldObj), ...Object.keys(newObj)]));
    allKeys.forEach(k => {
      const keyName = prefix ? `${prefix}.${k}` : k;
      const vOld = oldObj[k];
      const vNew = newObj[k];

      if (typeof vOld === 'object' && typeof vNew === 'object' && vOld !== null && vNew !== null) {
        diffs.push(...computeDiffList(vOld, vNew, keyName));
      } else if (vOld !== vNew) {
        diffs.push({ field: keyName, old_value: vOld, new_value: vNew });
      }
    });
    return diffs;
  }

  // =========================================================================
  // ASK YOUR DOCUMENT ASSISTANT
  // =========================================================================

  function openAskDocModal() {
    DOM.modalAsk.classList.remove('hidden');
    DOM.askChipsRow.innerHTML = '';

    // Suggestions tailored to document type
    const suggestionsMap = {
      'timetable': [
        "When is the next exam?",
        "Where is the DSA lecture?",
        "Who is the professor for Maths?",
        "List all Friday classes"
      ],
      'receipt': [
        "What is the total amount?",
        "What items were ordered?",
        "What is the store name?",
        "Is there any discount or tax?"
      ],
      'notice': [
        "When is the event date and time?",
        "Where is the venue?",
        "What is the registration deadline?",
        "Who is eligible to participate?"
      ],
      'poster': [
        "What is the event title?",
        "What are the contact details?",
        "Where does it take place?"
      ]
    };

    const chips = suggestionsMap[state.docType] || ["Summarize this document", "What are the key dates?"];
    chips.forEach(c => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ask-chip';
      btn.textContent = c;
      btn.addEventListener('click', () => {
        DOM.askInput.value = c;
        submitAskQuestion();
      });
      DOM.askChipsRow.appendChild(btn);
    });
  }

  async function submitAskQuestion() {
    const q = DOM.askInput.value.trim();
    if (!q) return;

    // Append user message
    appendChatMessage('user', q);
    DOM.askInput.value = '';

    // Show typing assistant message
    const typingId = appendChatMessage('assistant', 'Consulting document context...');

    try {
      const response = await fetch('/api/document/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q,
          data: state.currentWorkingData,
          doc_type: state.docType
        })
      });

      const res = await response.json();
      updateChatMessage(typingId, res.answer || "I couldn't find that information in this document.");
    } catch (e) {
      updateChatMessage(typingId, "Error connecting to document assistant. Please try again.");
    }
  }

  function appendChatMessage(role, text) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${role}`;
    msg.id = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    msg.innerHTML = `<span>${escapeHtml(text)}</span>`;
    DOM.askChatHistory.appendChild(msg);
    DOM.askChatHistory.scrollTop = DOM.askChatHistory.scrollHeight;
    return msg.id;
  }

  function updateChatMessage(msgId, text) {
    const el = document.getElementById(msgId);
    if (el) {
      el.innerHTML = `<span>${escapeHtml(text)}</span>`;
      DOM.askChatHistory.scrollTop = DOM.askChatHistory.scrollHeight;
    }
  }

  // =========================================================================
  // SMART SUMMARY MODAL
  // =========================================================================

  async function openSummaryModal() {
    DOM.modalSummary.classList.remove('hidden');
    DOM.summaryLoading.classList.remove('hidden');
    DOM.summaryContent.classList.add('hidden');

    try {
      const response = await fetch('/api/document/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data: state.currentWorkingData,
          doc_type: state.docType,
          doc_id: state.docId
        })
      });

      const sum = await response.json();
      DOM.summaryLoading.classList.add('hidden');
      DOM.summaryContent.classList.remove('hidden');

      // Populate bullet points
      DOM.summaryPointsList.innerHTML = '';
      (sum.important_points || []).forEach(pt => {
        const li = document.createElement('li');
        li.textContent = pt;
        DOM.summaryPointsList.appendChild(li);
      });

      DOM.sumDate.textContent = sum.date || 'Refer to Document';
      DOM.sumTime.textContent = sum.time || 'N/A';
      DOM.sumVenue.textContent = sum.venue || 'N/A';
      DOM.sumDeadline.textContent = sum.deadline_or_total || 'N/A';

    } catch (e) {
      DOM.summaryLoading.classList.add('hidden');
      showError("Failed to generate document summary.");
    }
  }

  function extractSummaryAsText() {
    const points = Array.from(DOM.summaryPointsList.querySelectorAll('li')).map(l => `• ${l.textContent}`).join('\n');
    return `DOCSNAP SMART SUMMARY\n\nImportant Points:\n${points}\n\nDate: ${DOM.sumDate.textContent}\nTime: ${DOM.sumTime.textContent}\nVenue: ${DOM.sumVenue.textContent}\nDeadline/Total: ${DOM.sumDeadline.textContent}`;
  }

  // =========================================================================
  // TRANSLATION MODAL
  // =========================================================================

  function openTranslateModal() {
    DOM.modalTranslate.classList.remove('hidden');
    DOM.transOrigLang.textContent = state.language;
    DOM.transOrigContent.textContent = JSON.stringify(state.currentWorkingData, null, 2);
    DOM.transResultContent.textContent = 'Select target language and click Translate...';
  }

  async function submitTranslation() {
    const targetLang = DOM.translateLangSelect.value;
    DOM.transTargetLang.textContent = targetLang;
    DOM.transResultContent.textContent = `Translating document fields to ${targetLang}...`;

    try {
      const response = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data: state.currentWorkingData,
          target_language: targetLang
        })
      });

      const res = await response.json();
      DOM.transResultContent.textContent = JSON.stringify(res.translated, null, 2);
      showToast(`Translated to ${targetLang}! Original preserved.`, 'success');
    } catch (e) {
      DOM.transResultContent.textContent = "Translation failed. Please try again.";
    }
  }

  // =========================================================================
  // EXPORT CENTER (ICS, EXCEL, CSV, JSON, PRINT)
  // =========================================================================

  function setupExportDropdown() {
    if (DOM.exportCenterBtn && DOM.exportDropdownMenu) {
      DOM.exportCenterBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        DOM.exportDropdownMenu.classList.toggle('hidden');
      });

      document.addEventListener('click', () => {
        if (!DOM.exportDropdownMenu.classList.contains('hidden')) {
          DOM.exportDropdownMenu.classList.add('hidden');
        }
      });
    }

    if (DOM.exportOptIcs) DOM.exportOptIcs.addEventListener('click', triggerCalendarExport);
    if (DOM.exportOptExcel) DOM.exportOptExcel.addEventListener('click', triggerExcelExport);
    if (DOM.exportOptCsv) DOM.exportOptCsv.addEventListener('click', triggerCsvExport);
    if (DOM.exportOptJson) DOM.exportOptJson.addEventListener('click', triggerJsonExport);
    if (DOM.exportOptPrint) DOM.exportOptPrint.addEventListener('click', () => window.print());
  }

  function getExportPayload() {
    return {
      doc_type: state.docType,
      language: state.language,
      confidence: state.confidence,
      data: state.currentWorkingData,
      verified_data: state.verifiedData || state.currentWorkingData,
      version_type: state.verificationStatus === 'verified' ? 'verified' : 'ai_generated'
    };
  }

  async function triggerCalendarExport() {
    const payload = getExportPayload();
    try {
      const response = await fetch('/export/ics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Failed to export calendar file.');
      }
      const blob = await response.blob();
      const fn = state.docType === 'timetable' ? 'schedule.ics' : 'notice_event.ics';
      downloadBlob(blob, fn);
      showToast("Calendar (.ics) downloaded! Ready to import.", "success");
    } catch (e) {
      showError(e.message);
    }
  }

  async function triggerExcelExport() {
    const payload = getExportPayload();
    try {
      const response = await fetch('/export/excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Failed to export Excel file.');
      }
      const blob = await response.blob();
      const fn = `${state.docType}_verified_data.xlsx`;
      downloadBlob(blob, fn);
      showToast("Excel spreadsheet (.xlsx) exported successfully!", "success");
    } catch (e) {
      showError(e.message);
    }
  }

  async function triggerCsvExport() {
    const payload = getExportPayload();
    try {
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
      const fn = `${state.docType}_data.csv`;
      downloadBlob(blob, fn);
      showToast("CSV file exported successfully!", "success");
    } catch (e) {
      showError(e.message);
    }
  }

  function triggerJsonExport() {
    const payload = getExportPayload();
    const str = JSON.stringify(payload.verified_data || payload.data, null, 2);
    const blob = new Blob([str], { type: 'application/json' });
    downloadBlob(blob, `${state.docType}_data.json`);
    showToast("JSON payload downloaded!", "success");
  }

  function updateActionPanel() {
    let actionLabel = 'Export';
    let heading = 'Ready to sync?';
    let subheading = 'Export your structured data directly into calendar or spreadsheet apps.';

    if (state.docType === 'timetable') {
      actionLabel = 'Add to Calendar (.ics)';
      heading = 'Sync Weekly Schedule';
      subheading = 'Exports recurring weekly events (RRULE WEEKLY) in Asia/Kolkata timezone.';
    } else if (state.docType in ('notice', 'poster')) {
      actionLabel = 'Add Event to Calendar (.ics)';
      heading = 'Add Event to Calendar';
      subheading = 'Creates a calendar event ready for Google Calendar, Apple Calendar, or Outlook.';
    } else if (state.docType === 'receipt') {
      actionLabel = 'Export Excel Spreadsheet';
      heading = 'Export Expense Data';
      subheading = 'Downloads itemized Excel (.xlsx) or CSV formatted for finance and accounting.';
    }

    if (DOM.bottomActionText) DOM.bottomActionText.textContent = actionLabel;
    if (DOM.actionPanelHeading) DOM.actionPanelHeading.textContent = heading;
    if (DOM.actionPanelSubheading) DOM.actionPanelSubheading.textContent = subheading;
  }

  // =========================================================================
  // PERSISTENT HISTORY & GLOBAL SEARCH
  // =========================================================================

  function setupHistoryHandlers() {
    let searchTimer = null;
    if (DOM.historySearchInput) {
      DOM.historySearchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
          state.historyFilter.q = e.target.value.trim();
          loadHistory();
        }, 300);
      });
    }

    if (DOM.filterDocType) {
      DOM.filterDocType.addEventListener('change', (e) => {
        state.historyFilter.docType = e.target.value;
        loadHistory();
      });
    }

    if (DOM.filterStatus) {
      DOM.filterStatus.addEventListener('change', (e) => {
        state.historyFilter.status = e.target.value;
        loadHistory();
      });
    }

    if (DOM.filterLanguage) {
      DOM.filterLanguage.addEventListener('change', (e) => {
        state.historyFilter.language = e.target.value;
        loadHistory();
      });
    }

    if (DOM.filterSort) {
      DOM.filterSort.addEventListener('change', (e) => {
        state.historyFilter.sort = e.target.value;
        loadHistory();
      });
    }
  }

  async function loadHistory() {
    const f = state.historyFilter;
    const params = new URLSearchParams({
      q: f.q,
      doc_type: f.docType,
      status: f.status,
      language: f.language,
      sort: f.sort
    });

    try {
      const response = await fetch(`/api/documents?${params.toString()}`);
      if (!response.ok) throw new Error("Could not fetch history.");
      const data = await response.json();
      state.historyDocs = data.documents || [];
      renderHistoryGrid(state.historyDocs);
      if (DOM.navHistoryCount) DOM.navHistoryCount.textContent = state.historyDocs.length;
    } catch (e) {
      showError(e.message);
    }
  }

  async function refreshHistoryCount() {
    try {
      const response = await fetch('/api/documents');
      if (response.ok) {
        const data = await response.json();
        if (DOM.navHistoryCount) DOM.navHistoryCount.textContent = (data.documents || []).length;
      }
    } catch (e) {}
  }

  function renderHistoryGrid(docs) {
    if (!DOM.historyItemsContainer) return;
    DOM.historyItemsContainer.innerHTML = '';

    if (docs.length === 0) {
      DOM.historyEmptyState.classList.remove('hidden');
      return;
    }
    DOM.historyEmptyState.classList.add('hidden');

    docs.forEach(doc => {
      const card = document.createElement('div');
      card.className = 'history-card';

      const statusPillClass = doc.verification_status === 'verified' ? 'status-pill-verified' : 
        (doc.verification_status === 'warning' ? 'status-pill-warning' : 
        (doc.verification_status === 'needs_review' ? 'status-pill-needs-review' : 'status-pill-ai'));
      
      const statusText = doc.verification_status === 'verified' ? '🟢 Verified' : 
        (doc.verification_status === 'warning' ? '🔴 Warning' : 
        (doc.verification_status === 'needs_review' ? '🟡 Needs Review' : '🔵 AI Generated'));

      // Document title resolution
      let docTitle = doc.filename;
      const data = doc.verified_data || doc.user_corrected_data || doc.ai_extracted_data || {};
      if (data.title) docTitle = data.title;
      else if (data.merchant) docTitle = data.merchant;

      const dateStr = new Date(doc.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
      const confPct = Math.round((doc.ai_confidence || 0.95) * 100);

      const thumbSrc = doc.thumbnail || '/static/samples/sample_timetable.png';

      card.innerHTML = `
        <div class="history-card-header">
          <img src="${thumbSrc}" alt="Document Preview" class="history-card-thumb" onerror="this.style.display='none'">
          <span class="status-pill ${statusPillClass} history-card-status-badge">${statusText}</span>
          <span class="sample-badge badge-${doc.doc_type} history-card-type-badge">${doc.doc_type.toUpperCase()}</span>
        </div>
        <div class="history-card-body">
          <h4 class="history-card-title" title="${escapeHtml(docTitle)}">${escapeHtml(docTitle)}</h4>
          <div class="history-card-meta">
            <span>📅 ${dateStr}</span>
            <span>🌐 ${escapeHtml(doc.language || 'English')}</span>
            <span>🎯 ${confPct}% Conf.</span>
          </div>
          <div class="history-card-actions">
            <button type="button" class="btn btn-primary btn-xs btn-open-doc" style="flex: 1;">Open & Verify</button>
            <button type="button" class="btn btn-secondary btn-xs btn-versions-doc" title="View Version History">Versions</button>
            <button type="button" class="btn btn-ghost btn-xs btn-del-doc" title="Delete from history">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `;

      card.querySelector('.btn-open-doc').addEventListener('click', () => openDocumentById(doc.id));
      card.querySelector('.btn-versions-doc').addEventListener('click', () => {
        state.docId = doc.id;
        openVersionHistoryModal();
      });
      card.querySelector('.btn-del-doc').addEventListener('click', async () => {
        if (confirm(`Delete "${docTitle}" from history?`)) {
          await deleteDocumentById(doc.id);
        }
      });

      DOM.historyItemsContainer.appendChild(card);
    });
  }

  async function openDocumentById(docId) {
    try {
      showScreen('processing');
      const response = await fetch(`/api/documents/${docId}`);
      if (!response.ok) throw new Error("Could not load document.");
      const doc = await response.json();

      state.docId = doc.id;
      state.docType = doc.doc_type;
      state.language = doc.language || 'English';
      state.confidence = doc.ai_confidence || 0.95;
      state.aiExtractedData = doc.ai_extracted_data || {};
      state.currentWorkingData = doc.verified_data || doc.user_corrected_data || doc.ai_extracted_data || {};
      state.verifiedData = doc.verified_data;
      state.verificationStatus = doc.verification_status || 'ai_generated';
      state.verificationReport = doc.verification_report;
      state.sensitiveDataInfo = doc.sensitive_data_info;
      state.versions = doc.versions || [];
      state.currentImageUrl = doc.thumbnail || '';

      showScreen('results');
    } catch (e) {
      showScreen('history');
      showError(e.message);
    }
  }

  async function deleteDocumentById(docId) {
    try {
      const response = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error("Failed to delete.");
      showToast("Document deleted.", "info");
      loadHistory();
      refreshHistoryCount();
    } catch (e) {
      showError(e.message);
    }
  }

  // =========================================================================
  // ANALYTICS DASHBOARD
  // =========================================================================

  async function loadDashboard() {
    try {
      const response = await fetch('/api/analytics');
      if (!response.ok) throw new Error("Could not load analytics.");
      const data = await response.json();

      if (DOM.metricTotalDocs) DOM.metricTotalDocs.textContent = data.total_documents;
      if (DOM.metricVerifiedDocs) DOM.metricVerifiedDocs.textContent = data.verified_count;
      if (DOM.metricVerifiedSub) DOM.metricVerifiedSub.textContent = `${data.verification_rate}% Verification Rate`;
      if (DOM.metricCorrectedDocs) DOM.metricCorrectedDocs.textContent = data.corrected_count;
      if (DOM.metricReviewDocs) DOM.metricReviewDocs.textContent = (data.needs_review_count + data.warning_count);
      if (DOM.metricAvgConf) DOM.metricAvgConf.textContent = `${data.avg_confidence}%`;

      // Document Type Distribution
      if (DOM.typeDistributionList) {
        DOM.typeDistributionList.innerHTML = '';
        const types = data.type_counts || {};
        const total = data.total_documents || 1;

        const allTypes = ['timetable', 'receipt', 'notice', 'poster', 'other'];
        allTypes.forEach(t => {
          const count = types[t] || 0;
          const pct = Math.round((count / total) * 100);

          const row = document.createElement('div');
          row.className = 'type-bar-row';
          row.innerHTML = `
            <div class="type-bar-label-row">
              <span>${t.toUpperCase()}</span>
              <span>${count} docs (${pct}%)</span>
            </div>
            <div class="type-bar-bg">
              <div class="type-bar-fill" style="width: ${pct}%"></div>
            </div>
          `;
          DOM.typeDistributionList.appendChild(row);
        });
      }
    } catch (e) {
      showError("Could not load dashboard metrics.");
    }
  }

  // =========================================================================
  // IMAGE ZOOM & PAN HELPERS
  // =========================================================================

  function setupZoomControls() {
    DOM.zoomInBtn.addEventListener('click', () => setZoom(state.zoomLevel + 25));
    DOM.zoomOutBtn.addEventListener('click', () => setZoom(state.zoomLevel - 25));
    DOM.zoomResetBtn.addEventListener('click', () => setZoom(100));

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
  // CONFIDENCE HELPERS
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
        <span class="field-verify-badge" title="AI Confidence: ${Math.round(conf * 100)}% - Please verify this value">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Please verify (AI Confidence: ${Math.round(conf * 100)}%)
        </span>
      `;
    }
    return '';
  }

  function updateRawJsonView() {
    const payload = state.verifiedData || state.currentWorkingData || {};
    DOM.rawJsonContent.innerHTML = `<code>${escapeHtml(JSON.stringify(payload, null, 2))}</code>`;
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
  // TOAST & ALERT HELPERS
  // =========================================================================

  function showToast(message, type = 'success', duration = 3500) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconSvg = type === 'success' ? 
      `<svg class="toast-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>` :
      `<svg class="toast-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;

    toast.innerHTML = `${iconSvg}<span class="toast-message">${escapeHtml(message)}</span>`;
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
