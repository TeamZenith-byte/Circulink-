'use strict';

const State = { aiResult: null, imagePath: null, selectedNgo: null };

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initAnimations();
  initUploadZone();
  initAiAnalysis();
  initListingForm();
  initDonationForm();
  initContactForm();
  initFilterChips();
  initNgoCards();
  initCounters();
  maybeAnimateTicker();
});

function initNavbar() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;
  window.addEventListener('scroll', () => navbar.classList.toggle('scrolled', window.scrollY > 30), { passive: true });
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (path !== '/' && href !== '/' && path.startsWith(href))) a.classList.add('active');
    if (path === '/' && href === '/') a.classList.add('active');
  });
}

function initAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 80);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.animate-in').forEach(el => observer.observe(el));
}

function initCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const decimals = el.dataset.decimals ? parseInt(el.dataset.decimals) : 0;
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    let start = null;
    const obs = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      obs.disconnect();
      const step = (ts) => {
        if (!start) start = ts;
        const progress = Math.min((ts - start) / 1800, 1);
        const ease = 1 - Math.pow(1 - progress, 4);
        el.textContent = prefix + (target * ease).toFixed(decimals) + suffix;
        if (progress < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, { threshold: 0.5 });
    obs.observe(el);
  });
}

function initUploadZone() {
  document.querySelectorAll('.upload-zone').forEach(zone => {
    const input = zone.querySelector('input[type="file"]');
    const preview = zone.closest('.form-group')?.querySelector('.image-preview')
                 || zone.parentElement?.querySelector('.image-preview');
    if (!input) return;
    ['dragover','dragleave','drop'].forEach(evt => {
      zone.addEventListener(evt, (e) => {
        e.preventDefault();
        zone.classList.toggle('dragover', evt === 'dragover');
      });
    });
    zone.addEventListener('drop', (e) => {
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file, input, preview, zone);
    });
    input.addEventListener('change', () => {
      if (input.files[0]) handleFileSelect(input.files[0], input, preview, zone);
    });
  });
}

function handleFileSelect(file, input, preview, zone) {
  if (!file.type.startsWith('image/')) { showToast('Please upload an image file.', 'error'); return; }
  const reader = new FileReader();
  reader.onload = (e) => {
    if (preview) {
      preview.src = e.target.result;
      preview.style.display = 'block';
      const uc = zone.querySelector('.upload-content');
      if (uc) uc.style.display = 'none';
    }
  };
  reader.readAsDataURL(file);
}

function initAiAnalysis() {
  const analyzeBtn = document.getElementById('analyzeBtn');
  if (!analyzeBtn) return;
  analyzeBtn.addEventListener('click', async () => {
    const form = document.getElementById('analysisForm');
    if (!form) return;
    const imageInput = form.querySelector('input[type="file"]');
    const catSelect  = form.querySelector('#categoryHint');
    const descInput  = form.querySelector('#itemDescription');
    if (!imageInput?.files[0] && !descInput?.value.trim()) {
      showToast('Please upload an image or add a description.', 'error'); return;
    }
    const fd = new FormData();
    if (imageInput?.files[0]) fd.append('image', imageInput.files[0]);
    if (catSelect)  fd.append('category', catSelect.value);
    if (descInput)  fd.append('description', descInput.value);
    setButtonLoading(analyzeBtn, true);
    showLoader('AI is analyzing your waste...', 'Classifying · Scoring · Pricing');
    try {
      const res  = await fetch('/api/analyze', { method: 'POST', body: fd });
      const data = await res.json();
      hideLoader(); setButtonLoading(analyzeBtn, false);
      if (data.success) {
        State.aiResult = data.result; State.imagePath = data.result.image_path;
        renderAiResult(data.result);
        showToast('Analysis complete!', 'success');
      } else { showToast('Analysis failed.', 'error'); }
    } catch { hideLoader(); setButtonLoading(analyzeBtn, false); showToast('Connection error.', 'error'); }
  });
}

function renderAiResult(r) {
  const panel = document.getElementById('aiResultPanel');
  if (!panel) return;
  setInner('resultCategory', r.category);
  setInner('resultSubcategory', r.subcategory);
  setInner('resultQuality', r.quality);
  setInner('resultQualityDesc', r.quality_description || '');
  setInner('resultPrice', `₹${r.estimated_price.toFixed(2)}`);
  setInner('resultCo2', `${r.co2_saved} kg`);
  setInner('resultTip', r.tips);
  const badge = document.getElementById('qualityBadge');
  if (badge) { badge.className = `quality-badge ${r.quality.toLowerCase()}`; badge.textContent = r.quality; }
  updateScoreRing(r.quality_score);
  const fill  = document.getElementById('confidenceFill');
  const label = document.getElementById('confidenceLabel');
  if (fill)  setTimeout(() => fill.style.width = `${r.confidence * 100}%`, 300);
  if (label) label.textContent = `${Math.round(r.confidence * 100)}%`;
  const buyersEl = document.getElementById('recommendedBuyers');
  if (buyersEl && r.recommended_buyers)
    buyersEl.innerHTML = r.recommended_buyers.map(b => `<span class="buyer-chip">${b}</span>`).join('');
  const listForm = document.getElementById('listingFormSection');
  if (listForm) {
    setVal('listCategory', r.category); setVal('listSubcategory', r.subcategory);
    setVal('listQuality', r.quality);   setVal('listQualityScore', r.quality_score);
    setVal('listPrice', r.estimated_price.toFixed(2));
    setVal('listCo2', r.co2_saved);     setVal('listImagePath', State.imagePath || '');
    listForm.style.display = 'block';
    listForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  const placeholder = document.getElementById('aiPlaceholder');
  if (placeholder) placeholder.style.display = 'none';
  panel.classList.add('active');
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function updateScoreRing(score) {
  const ring = document.querySelector('.score-ring .ring-fill');
  const val  = document.querySelector('.score-ring .ring-value');
  if (!ring || !val) return;
  setTimeout(() => ring.style.strokeDashoffset = 220 - (score / 100) * 220, 300);
  let current = 0;
  const timer = setInterval(() => {
    current++; val.textContent = current;
    if (current >= score) clearInterval(timer);
  }, 1200 / score);
}

function initListingForm() {
  const form = document.getElementById('createListingForm');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    const fd  = new FormData(form);
    if (State.imagePath) fd.set('image_path', State.imagePath);
    setButtonLoading(btn, true);
    try {
      const res  = await fetch('/api/list-waste', { method: 'POST', body: fd });
      const data = await res.json();
      setButtonLoading(btn, false);
      if (data.success) {
        showToast('🎉 Listing created! Redirecting...', 'success');
        setTimeout(() => window.location.href = '/marketplace', 2000);
      } else { showToast('Failed to create listing.', 'error'); }
    } catch { setButtonLoading(btn, false); showToast('Connection error.', 'error'); }
  });
}

function initDonationForm() {
  const form = document.getElementById('donationForm');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    setButtonLoading(btn, true);
    try {
      const res  = await fetch('/api/donate', { method: 'POST', body: new FormData(form) });
      const data = await res.json();
      setButtonLoading(btn, false);
      if (data.success) {
        showToast('❤️ ' + data.message, 'success');
        form.reset();
        document.querySelectorAll('.image-preview').forEach(p => p.style.display = 'none');
        document.querySelectorAll('.upload-content').forEach(c => c.style.display = '');
        document.querySelectorAll('.ngo-card').forEach(c => c.classList.remove('selected'));
      } else { showToast('Submission failed.', 'error'); }
    } catch { setButtonLoading(btn, false); showToast('Connection error.', 'error'); }
  });
}

function initContactForm() {
  const form = document.getElementById('contactForm');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    setButtonLoading(btn, true);
    try {
      const res  = await fetch('/api/contact', { method: 'POST', body: new FormData(form) });
      const data = await res.json();
      setButtonLoading(btn, false);
      if (data.success) { showToast('✅ ' + data.message, 'success'); form.reset(); }
    } catch { setButtonLoading(btn, false); showToast('Connection error.', 'error'); }
  });
}

function initFilterChips() {
  document.querySelectorAll('.filter-chip[data-filter]').forEach(chip => {
    chip.addEventListener('click', () => {
      const group = chip.dataset.group;
      const value = chip.dataset.filter;
      if (group) document.querySelectorAll(`.filter-chip[data-group="${group}"]`).forEach(c => c.classList.remove('active'));
      chip.classList.toggle('active');
      const input = document.querySelector(`input[name="${group}"]`);
      if (input) input.value = chip.classList.contains('active') ? value : '';
      const ff = document.getElementById('filterForm');
      if (ff) setTimeout(() => ff.submit(), 100);
    });
  });
}

function initNgoCards() {
  document.querySelectorAll('.ngo-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.ngo-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      State.selectedNgo = card.dataset.ngo;
      const input = document.getElementById('ngoPreference');
      if (input) input.value = State.selectedNgo;
    });
  });
}

function maybeAnimateTicker() {
  const ticker = document.querySelector('.ticker');
  if (!ticker) return;
  ticker.parentElement.appendChild(ticker.cloneNode(true));
}

function showLoader(text = 'Processing...', sub = '') {
  let ov = document.getElementById('loadingOverlay');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'loadingOverlay'; ov.className = 'loading-overlay';
    ov.innerHTML = `<div style="position:relative;width:80px;height:80px;"><div class="scanner-ring"></div></div>
      <div class="loading-text" id="loaderText">${text}</div>
      <div class="loading-subtext" id="loaderSub">${sub}</div>`;
    document.body.appendChild(ov);
  } else { setInner('loaderText', text); setInner('loaderSub', sub); }
  requestAnimationFrame(() => ov.classList.add('active'));
}

function hideLoader() {
  const ov = document.getElementById('loadingOverlay');
  if (ov) { ov.classList.remove('active'); setTimeout(() => ov.remove(), 400); }
}

function showToast(message, type = 'info', duration = 4500) {
  let container = document.querySelector('.toast-container');
  if (!container) { container = document.createElement('div'); container.className = 'toast-container'; document.body.appendChild(container); }
  const icons = { success:'✅', error:'❌', info:'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type]||'ℹ️'}</span><span class="toast-msg">${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.animation = 'slideInRight 0.4s ease reverse both'; setTimeout(() => toast.remove(), 400); }, duration);
}

function setButtonLoading(btn, loading) {
  if (!btn) return;
  let spinner = btn.querySelector('.btn-spinner');
  let textEl  = btn.querySelector('.btn-text');
  if (!spinner) {
    const text = btn.textContent.trim();
    btn.innerHTML = `<div class="btn-spinner"></div><span class="btn-text">${text}</span>`;
    spinner = btn.querySelector('.btn-spinner');
    textEl  = btn.querySelector('.btn-text');
  }
  btn.classList.toggle('loading', loading);
  btn.disabled = loading;
  if (spinner) spinner.style.display = loading ? 'block' : 'none';
}

function setInner(id, value) { const el = document.getElementById(id); if (el) el.textContent = value; }
function setVal(id, value)   { const el = document.getElementById(id); if (el) el.value = value; }

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideLoader(); });
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', (e) => {
    const t = document.querySelector(a.getAttribute('href'));
    if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth' }); }
  });
});