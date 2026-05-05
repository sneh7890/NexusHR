/* ════════════════════════════════════════════════════
   TimeTrack Pro — Frontend
   No async/await — Promise .then() chains only
════════════════════════════════════════════════════ */
'use strict';

var currentUser   = null;
var accessToken   = null;
var tsInterval    = null;
var clockInterval = null;
var workedSecs    = 0;
var prodChart     = null;
var loginUsername = '';
var forgotEmail   = '';
var resendTimers  = {};
var selectedTz    = 'IST';

var TIMEZONES = {
  IST: { label: 'IST', name: 'India Standard Time',  offset: 330,  display: 'UTC+5:30' },
  EST: { label: 'EST', name: 'Eastern Standard Time', offset: -300, display: 'UTC-5:00' },
  CST: { label: 'CST', name: 'Central Standard Time', offset: -360, display: 'UTC-6:00' },
  PST: { label: 'PST', name: 'Pacific Standard Time', offset: -480, display: 'UTC-8:00' }
};

// Spreadsheet
var sheetData = null, sheetId = null, sheetName = '';
var selRow = -1, selCol = -1, colWidths = {};

// Shared sheet
var sharedColumns = [], sharedRows = [];

// Bootstrap modals
var bsExportModal = null, bsAddUserModal = null, bsRoleModal = null, bsSheetConfigModal = null;

// ── Boot ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  startLiveClock();

  bsExportModal      = new bootstrap.Modal(document.getElementById('modal-export'));
  bsAddUserModal     = new bootstrap.Modal(document.getElementById('modal-add-user'));
  bsRoleModal        = new bootstrap.Modal(document.getElementById('modal-role'));
  bsSheetConfigModal = new bootstrap.Modal(document.getElementById('modal-sheet-config'));

  setupOtpInputs('login-otp-box');
  setupOtpInputs('register-otp-box');
  setupOtpInputs('forgot-otp-box');

  api('/api/auth/me').then(function(r) {
    if (r.ok) { currentUser = r.user; showApp(); }
    else       { showStep('step-login'); }
  });
});

// ── Timezone helpers ──────────────────────────────────
function tzTime(offsetMins) {
  var now   = new Date();
  var utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
  var tzDate = new Date(utcMs + offsetMins * 60000);
  return tzDate.toLocaleTimeString('en-US', { hour12: false });
}

// ── Live clock ────────────────────────────────────────
function startLiveClock() {
  function tick() {
    var now   = new Date();
    var t     = now.toLocaleTimeString('en-US', { hour12: false });
    var date  = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    var badge = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    if (el('live-clock'))      el('live-clock').textContent      = t;
    if (el('live-date'))       el('live-date').textContent       = date;
    if (el('live-date-badge')) el('live-date-badge').textContent = badge;
    // Show local timezone name on dashboard
    if (el('local-tz-label')) {
      try {
        var tzName = Intl.DateTimeFormat().resolvedOptions().timeZone;
        el('local-tz-label').textContent = tzName;
      } catch(e2) { el('local-tz-label').textContent = 'Local Time'; }
    }
    // Update world clock times
    Object.keys(TIMEZONES).forEach(function(tz) {
      var timeEl = el('wc-' + tz);
      if (timeEl) timeEl.textContent = tzTime(TIMEZONES[tz].offset);
    });
  }
  tick();
  setInterval(tick, 1000);
}

// ── World Clocks ──────────────────────────────────────
function renderWorldClocks() {
  var wc = el('world-clocks');
  if (!wc) return;
  var html = '';
  Object.keys(TIMEZONES).forEach(function(tz) {
    var t      = TIMEZONES[tz];
    var active = (tz === selectedTz) ? ' active-tz' : '';
    html += '<div class="tz-clock' + active + '" id="wc-card-' + tz + '" onclick="selectTz(\'' + tz + '\')">';
    html += '<div class="tz-label">' + t.label + '</div>';
    html += '<div class="tz-time" id="wc-' + tz + '">' + tzTime(t.offset) + '</div>';
    html += '<div class="tz-diff">' + t.display + '</div>';
    html += '</div>';
  });
  wc.innerHTML = html;
}

function renderTzModal() {
  var wrap = el('tz-options');
  if (!wrap) return;
  var html = '';
  Object.keys(TIMEZONES).forEach(function(tz) {
    var t      = TIMEZONES[tz];
    var active = (tz === selectedTz) ? ' selected-tz' : '';
    html += '<div class="tz-option' + active + '" onclick="selectTz(\'' + tz + '\')">';
    html += '<div><div class="tz-option-label">' + t.label + ' - ' + t.name + '</div>';
    html += '<div class="tz-option-detail">' + t.display + '</div></div>';
    html += '<div class="tz-option-time" id="tzm-' + tz + '">' + tzTime(t.offset) + '</div>';
    html += '</div>';
  });
  wrap.innerHTML = html;
}

function selectTz(tz) {
  selectedTz = tz;
  renderWorldClocks();
  renderTzModal();
}

// ── OTP Input helpers ─────────────────────────────────
function setupOtpInputs(boxId) {
  var box = el(boxId);
  if (!box) return;
  var inputs = box.querySelectorAll('.otp-digit');
  inputs.forEach(function(inp, i) {
    inp.addEventListener('input', function() {
      if (inp.value && i < inputs.length - 1) inputs[i + 1].focus();
    });
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Backspace' && !inp.value && i > 0) inputs[i - 1].focus();
    });
    inp.addEventListener('paste', function(e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
      inputs.forEach(function(d, idx) { d.value = text[idx] || ''; });
      if (inputs[5]) inputs[5].focus();
    });
  });
}

function getOtp(boxId) {
  var box = el(boxId);
  if (!box) return '';
  return Array.from(box.querySelectorAll('.otp-digit')).map(function(i) { return i.value; }).join('');
}

function clearOtp(boxId) {
  var box = el(boxId);
  if (!box) return;
  box.querySelectorAll('.otp-digit').forEach(function(i) { i.value = ''; });
  var first = box.querySelector('.otp-digit');
  if (first) first.focus();
}

function startResendTimer(timerId, seconds, onResend) {
  if (resendTimers[timerId]) clearInterval(resendTimers[timerId]);
  var remaining = seconds;
  var timerEl   = el(timerId);
  function tick() {
    if (!timerEl) return;
    if (remaining > 0) {
      timerEl.innerHTML = 'Resend in <strong>' + remaining + 's</strong>';
      remaining--;
    } else {
      clearInterval(resendTimers[timerId]);
      timerEl.innerHTML = '<a class="resend-link" onclick="' + onResend + '">Resend code</a>';
    }
  }
  tick();
  resendTimers[timerId] = setInterval(tick, 1000);
}

// ── Auth steps ────────────────────────────────────────
function showStep(stepId) {
  var steps = ['step-login', 'step-login-otp', 'step-register', 'step-register-otp',
               'step-forgot-email', 'step-forgot-reset'];
  steps.forEach(function(s) {
    var e = el(s);
    if (e) e.style.display = (s === stepId) ? '' : 'none';
  });
}

function showApp() {
  el('login-page').style.display = 'none';
  el('app').style.display = 'flex';
  buildSidebar();
  if (currentUser.role === 'admin') {
    navigate('pg-admin-dash');
  } else {
    navigate('pg-dashboard');
  }
}

function togglePwd(id, btn) {
  var inp = el(id);
  if (inp.type === 'password') { inp.type = 'text'; btn.innerHTML = '<i class="bi bi-eye-slash"></i>'; }
  else { inp.type = 'password'; btn.innerHTML = '<i class="bi bi-eye"></i>'; }
}

// ── Login Step 1: Send OTP ─────────────────────────────
function doLoginStep1() {
  var username = val('l-user');
  var password = val('l-pass');
  var errEl    = el('l-err');
  errEl.classList.add('d-none');
  if (!username || !password) { errEl.textContent = 'Please enter username and password'; errEl.classList.remove('d-none'); return; }
  loginUsername = username;

  var btn = document.querySelector('#step-login .btn-amber');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="btn-spinner dark"></span>Sending OTP...'; }

  fetch('/api/auth/login/send-otp', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: username, password: password })
  }).then(function(r) { return r.json(); }).then(function(r) {
    var btn2 = document.querySelector('#step-login .btn-amber');
    if (btn2) { btn2.disabled = false; btn2.innerHTML = '<i class="bi bi-arrow-right me-2"></i>Continue'; }
    if (r.ok) {
      el('login-email-hint').textContent = 'Code sent to ' + r.email_hint;
      clearOtp('login-otp-box');
      showStep('step-login-otp');
      startResendTimer('login-resend', 60, 'doLoginResend()');
    } else {
      errEl.textContent = r.message || 'Login failed';
      errEl.classList.remove('d-none');
    }
  }).catch(function(e) {
    var btn3 = document.querySelector('#step-login .btn-amber');
    if (btn3) { btn3.disabled = false; btn3.innerHTML = '<i class="bi bi-arrow-right me-2"></i>Continue'; }
    errEl.textContent = 'Connection error: ' + e.message;
    errEl.classList.remove('d-none');
  });
}

function doLoginResend() { doLoginStep1(); }

// ── Login Step 2: Verify OTP ──────────────────────────
function doLoginStep2() {
  var otp   = getOtp('login-otp-box');
  var errEl = el('login-otp-err');
  errEl.classList.add('d-none');
  if (otp.length !== 6) { errEl.textContent = 'Please enter all 6 digits'; errEl.classList.remove('d-none'); return; }

  fetch('/api/auth/login/verify-otp', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: loginUsername, otp: otp })
  }).then(function(r) { return r.json(); }).then(function(r) {
    if (r.ok) {
      currentUser = r.user;
      accessToken = r.access_token || null;
      showApp();
    } else {
      errEl.textContent = r.message || 'Invalid OTP';
      errEl.classList.remove('d-none');
    }
  }).catch(function(e) {
    errEl.textContent = 'Error: ' + e.message;
    errEl.classList.remove('d-none');
  });
}

// ── Register Step 1: Send OTP ─────────────────────────
function doRegisterStep1() {
  var errEl = el('r-err');
  errEl.classList.add('d-none');
  var name  = val('r-name');
  var user  = val('r-user');
  var email = val('r-email');
  var pass  = val('r-pass');
  if (!name || !user || !email || !pass) { errEl.textContent = 'All fields are required'; errEl.classList.remove('d-none'); return; }
  if (pass.length < 8) { errEl.textContent = 'Password must be at least 8 characters'; errEl.classList.remove('d-none'); return; }

  var rbtn = document.querySelector('#step-register .btn-amber');
  if (rbtn) { rbtn.disabled = true; rbtn.innerHTML = '<span class="btn-spinner dark"></span>Sending OTP...'; }

  // var invite = val('r-invite');
  api('/api/auth/register/send-otp', 'POST', { email: email, full_name: name}).then(function(r) {
    var rbtn2 = document.querySelector('#step-register .btn-amber');
    if (rbtn2) { rbtn2.disabled = false; rbtn2.innerHTML = '<i class="bi bi-envelope me-2"></i>Send Verification Code'; }
    if (r.ok) {
      el('register-email-hint').textContent = 'Code sent to ' + email;
      clearOtp('register-otp-box');
      showStep('step-register-otp');
      startResendTimer('register-resend', 60, 'doRegisterResend()');
    } else {
      errEl.textContent = r.message || 'Failed to send OTP';
      errEl.classList.remove('d-none');
    }
  });
}

function doRegisterResend() { doRegisterStep1(); }

// ── Register Step 2: Verify OTP ──────────────────────
function doRegisterStep2() {
  var otp   = getOtp('register-otp-box');
  var errEl = el('register-otp-err');
  errEl.classList.add('d-none');
  if (otp.length !== 6) { errEl.textContent = 'Please enter all 6 digits'; errEl.classList.remove('d-none'); return; }

  api('/api/auth/register', 'POST', {
    username:   val('r-user'),
    email:      val('r-email'),
    password:   val('r-pass'),
    full_name:  val('r-name'),
    department: val('r-dept'),
    role:       val('r-role'),
    otp:        otp
  }).then(function(r) {
    if (r.ok) {
      toast('Account created! Please sign in.', 'success');
      showStep('step-login');
    } else {
      errEl.textContent = r.message || 'Registration failed';
      errEl.classList.remove('d-none');
    }
  });
}

// ── Forgot Step 1: Send OTP ───────────────────────────
function doForgotStep1() {
  var email = val('fp-email');
  var errEl = el('fp-err');
  errEl.classList.add('d-none');
  if (!email) { errEl.textContent = 'Email is required'; errEl.classList.remove('d-none'); return; }
  forgotEmail = email;

  var fbtn = document.querySelector('#step-forgot-email .btn-amber');
  if (fbtn) { fbtn.disabled = true; fbtn.innerHTML = '<span class="btn-spinner dark"></span>Sending OTP...'; }

  api('/api/auth/forgot-password/send-otp', 'POST', { email: email }).then(function(r) {
    var fbtn2 = document.querySelector('#step-forgot-email .btn-amber');
    if (fbtn2) { fbtn2.disabled = false; fbtn2.innerHTML = '<i class="bi bi-envelope me-2"></i>Send Reset Code'; }
    if (r.ok) {
      el('forgot-email-hint').textContent = 'Code sent to ' + email;
      clearOtp('forgot-otp-box');
      showStep('step-forgot-reset');
      startResendTimer('forgot-resend', 60, 'doForgotResend()');
    } else {
      errEl.textContent = r.message || 'Error';
      errEl.classList.remove('d-none');
    }
  });
}

function doForgotResend() { doForgotStep1(); }

// ── Forgot: Verify OTP + Reset ────────────────────────
function doForgotReset() {
  var otp     = getOtp('forgot-otp-box');
  var newpwd  = val('fp-newpwd');
  var confirm = val('fp-confirmpwd');
  var errEl   = el('fp-reset-err');
  errEl.classList.add('d-none');
  if (otp.length !== 6)   { errEl.textContent = 'Please enter all 6 digits'; errEl.classList.remove('d-none'); return; }
  if (!newpwd)            { errEl.textContent = 'New password is required'; errEl.classList.remove('d-none'); return; }
  if (newpwd.length < 8)  { errEl.textContent = 'Password must be at least 8 characters'; errEl.classList.remove('d-none'); return; }
  if (newpwd !== confirm)  { errEl.textContent = 'Passwords do not match'; errEl.classList.remove('d-none'); return; }

  api('/api/auth/forgot-password/reset-with-otp', 'POST', {
    email: forgotEmail, otp: otp, new_password: newpwd
  }).then(function(r) {
    if (r.ok) { toast(r.message, 'success'); showStep('step-login'); }
    else { errEl.textContent = r.message || 'Reset failed'; errEl.classList.remove('d-none'); }
  });
}

// ── Logout ────────────────────────────────────────────
function doLogout() {
  api('/api/auth/logout', 'POST').then(function() {
    currentUser = null; accessToken = null;
    if (tsInterval)    { clearInterval(tsInterval);    tsInterval    = null; }
    if (clockInterval) { clearInterval(clockInterval); clockInterval = null; }
    el('login-page').style.display = 'flex';
    el('app').style.display = 'none';
    showStep('step-login');
  });
}

// ── Sidebar ───────────────────────────────────────────
function buildSidebar() {
  var u        = currentUser;
  var initials = u.full_name.split(' ').map(function(w) { return w[0]; }).join('').slice(0, 2).toUpperCase();
  // Set sidebar avatar — photo or initials
  var avText = el('sb-av-text');
  var avImg  = el('sb-av-img');
  if (avText) avText.textContent = initials;
  if (u.photo && avImg) {
    avImg.src = u.photo;
    avImg.style.display = '';
    if (avText) avText.style.display = 'none';
  } else if (avImg) {
    avImg.style.display = 'none';
    if (avText) avText.style.display = '';
  }
  el('sb-name').textContent = u.full_name.split(' ')[0];
  var roleEl = el('sb-role');
  if (roleEl) {
    roleEl.textContent = u.role.charAt(0).toUpperCase() + u.role.slice(1);
    roleEl.className   = 'user-role-badge ' + u.role;
  }

  var isAdmin   = (u.role === 'admin');
  var isManager = (u.role === 'manager');
  selectedTz = u.timezone || 'IST';

  var I = {
    dash:   '<i class="bi bi-grid-1x2"></i>',
    ts:     '<i class="bi bi-card-list"></i>',
    users:  '<i class="bi bi-people"></i>',
    over:   '<i class="bi bi-bar-chart-line"></i>',
    sheet:  '<i class="bi bi-file-earmark-spreadsheet"></i>',
    shared: '<i class="bi bi-table"></i>'
  };

  var html = '';

  // Employee and Manager get personal dashboard with clock in/out
  if (!isAdmin) {
    html += navSec('My Workspace');
    html += navBtn(I.dash, 'Dashboard',     'pg-dashboard');
    html += navBtn(I.ts,   'My Timesheets', 'pg-history');
  }

  // Manager and Admin get team section
  if (isAdmin || isManager) {
    html += navSec('Team');
    html += navBtn(I.over, 'Overview',       'pg-admin-dash');
    html += navBtn(I.ts,   'All Timesheets', 'pg-admin-ts');
  }

  // Only admin gets user management
  if (isAdmin) {
    html += navSec('Administration');
    html += navBtn(I.users, 'Manage Users', 'pg-users');
    html += navBtn('<i class="bi bi-clock"></i>', 'Shifts', 'pg-shifts');
    html += navBtn('<i class="bi bi-calendar-x"></i>', 'Holidays', 'pg-holidays');
  }

  html += navSec('Workspace');
  html += navBtn(I.shared, 'Shared Sheet', 'pg-shared-sheet');
  html += navBtn(I.sheet,  'My Sheets',    'pg-spreadsheet');

  el('sidebar-nav').innerHTML = html;
}

function navSec(t) { return '<div class="nav-section">' + t + '</div>'; }
function navBtn(icon, label, pg) {
  return '<button class="nav-btn" data-pg="' + pg + '" onclick="navigate(\'' + pg + '\')">' + icon + '<span>' + label + '</span></button>';
}

// ── Navigation ────────────────────────────────────────
function navigate(pgId) {
  document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); p.style.display = 'none'; });
  var pg = el(pgId);
  if (pg) { pg.classList.add('active'); pg.style.display = ''; }
  document.querySelectorAll('.nav-btn[data-pg]').forEach(function(b) { b.classList.toggle('active', b.dataset.pg === pgId); });
  if (pgId === 'pg-dashboard')    loadDashboard();
  if (pgId === 'pg-history')      loadHistory();
  if (pgId === 'pg-admin-dash')   loadAdminDash();
  if (pgId === 'pg-admin-ts')     loadAdminTs();
  if (pgId === 'pg-users')        loadUsers();
  if (pgId === 'pg-shifts')       loadShifts();
  if (pgId === 'pg-holidays')     loadHolidays();
  if (pgId === 'pg-shared-sheet') loadSharedSheet();
  if (pgId === 'pg-spreadsheet')  loadSpreadsheet();
}

// ════ DASHBOARD (all roles) ══════════════════════════

function loadDashboard() {
  var h = new Date().getHours();
  var greet = h < 12 ? 'Good morning' : (h < 17 ? 'Good afternoon' : 'Good evening');
  el('dash-greeting').textContent = greet + ', ' + currentUser.full_name.split(' ')[0];
  el('dash-sub').textContent = "Here's your workspace for today";

  renderWorldClocks();
  refreshTsStatus();

  if (tsInterval) clearInterval(tsInterval);
  tsInterval = setInterval(refreshTsStatus, 8000);

  api('/api/timesheets/monthly-stats').then(function(ms) {
    if (ms.ok) {
      el('k-today').textContent = hrsLabel(ms.today_seconds);
      el('k-month').textContent = hrsLabel(ms.total_seconds);
      el('k-avg').textContent   = hrsLabel(ms.avg_seconds);
      el('k-days').textContent  = ms.days_present;
    }
  });

  var now = new Date();
  api('/api/timesheets/history?year=' + now.getFullYear() + '&month=' + (now.getMonth() + 1)).then(function(hist) {
    var ra = el('recent-activity');
    if (hist.ok && hist.timesheets && hist.timesheets.length) {
      ra.innerHTML = hist.timesheets.slice(0, 5).map(function(t) {
        return '<div class="activity-item"><div>' +
          '<div class="act-date">' + t.date + '</div>' +
          '<div class="act-time">' + (t.clock_in || '-') + ' to ' + (t.clock_out || 'In Progress') + '</div>' +
          '</div><div class="act-val">' + t.worked_display + '</div></div>';
      }).join('');
    } else {
      ra.innerHTML = '<div class="text-muted text-center py-3 small">No activity this month</div>';
    }
  });
}

function refreshTsStatus() {
  api('/api/timesheets/status').then(function(r) {
    if (!r.ok) return;
    var pill  = el('status-pill');
    var stext = el('status-text');
    var wwrap = el('worked-wrap');
    var wval  = el('worked-val');
    var btns  = el('clock-btns');
    if (!pill || !btns) return;

    if (r.status === 'idle') {
      if (clockInterval) { clearInterval(clockInterval); clockInterval = null; }
      workedSecs = 0;
      pill.className = 'status-pill idle';
      stext.textContent = 'Not clocked in';
      wwrap.style.display = 'none';
      btns.innerHTML = '<button class="btn btn-clock-in px-4" onclick="clockIn()"><i class="bi bi-play-circle me-2"></i>Clock In</button>';

    } else if (r.status === 'clocked_in') {
      pill.className = 'status-pill in';
      stext.textContent = 'Working';
      wwrap.style.display = 'flex';
      btns.innerHTML = '<button class="btn btn-break px-3" onclick="breakIn()"><i class="bi bi-cup-hot me-2"></i>Break</button>' +
                       '<button class="btn btn-clock-out px-3" onclick="clockOut()"><i class="bi bi-stop-circle me-2"></i>Clock Out</button>';
      if (!clockInterval) {
        workedSecs = Math.floor(r.worked_seconds || 0);
        clockInterval = setInterval(function() {
          workedSecs++;
          if (el('worked-val')) el('worked-val').textContent = hms(workedSecs);
          if (el('k-today'))    el('k-today').textContent    = hrsLabel(workedSecs);
        }, 1000);
      }
      if (wval) wval.textContent = hms(workedSecs);

    } else if (r.status === 'on_break') {
      if (clockInterval) { clearInterval(clockInterval); clockInterval = null; }
      workedSecs = Math.floor(r.worked_seconds || 0);
      pill.className = 'status-pill brk';
      stext.textContent = 'On Break';
      wwrap.style.display = 'flex';
      if (wval) wval.textContent = hms(workedSecs);
      btns.innerHTML = '<button class="btn btn-resume px-3" onclick="breakOut()"><i class="bi bi-play me-2"></i>Resume</button>' +
                       '<button class="btn btn-clock-out px-3" onclick="clockOut()"><i class="bi bi-stop-circle me-2"></i>Clock Out</button>';
    }
  });
}

// ── Clock In — check holiday first, then timezone modal ──
function clockIn() {
  api('/api/admin/holidays/today').then(function(r) {
    if (r.ok && r.is_holiday && r.holiday) {
      var holidayName = r.holiday.name;
      var proceed = confirm('Today is a Holiday: ' + holidayName + '. Do you still want to clock in?');
      if (!proceed) return;
    }
    renderTzModal();
    var modalEl = document.getElementById('modal-timezone');
    if (!modalEl) { doClockInWithTz(); return; }
    var tzModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    tzModal.show();
  }).catch(function() {
    // If check fails, proceed normally
    renderTzModal();
    var modalEl = document.getElementById('modal-timezone');
    if (!modalEl) { doClockInWithTz(); return; }
    var tzModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    tzModal.show();
  });
}

function doClockInWithTz() {
  var modalEl = document.getElementById('modal-timezone');
  if (modalEl) {
    var tzModal = bootstrap.Modal.getInstance(modalEl);
    if (tzModal) tzModal.hide();
  }
  api('/api/timesheets/clock-in', 'POST', { timezone: selectedTz }).then(function(r) {
    toast(r.message || (r.ok ? 'Clocked in!' : 'Error'), r.ok ? 'success' : 'error');
    if (r.ok) refreshTsStatus();
  });
}

function clockOut() {
  api('/api/timesheets/clock-out', 'POST').then(function(r) {
    if (r.ok) {
      toast('Clocked out! Worked: ' + r.worked_display, 'success');
      if (clockInterval) { clearInterval(clockInterval); clockInterval = null; }
      workedSecs = 0;
      refreshTsStatus();
      api('/api/timesheets/monthly-stats').then(function(ms) {
        if (ms.ok) {
          if (el('k-today')) el('k-today').textContent = hrsLabel(ms.today_seconds);
          if (el('k-month')) el('k-month').textContent = hrsLabel(ms.total_seconds);
          if (el('k-avg'))   el('k-avg').textContent   = hrsLabel(ms.avg_seconds);
          if (el('k-days'))  el('k-days').textContent  = ms.days_present;
        }
      });
    } else {
      toast(r.message || 'Error', 'error');
    }
  });
}

function breakIn() {
  api('/api/timesheets/break-in', 'POST').then(function(r) {
    toast(r.message || (r.ok ? 'Break started' : 'Error'), r.ok ? 'info' : 'error');
    if (r.ok) refreshTsStatus();
  });
}

function breakOut() {
  api('/api/timesheets/break-out', 'POST').then(function(r) {
    toast(r.message || (r.ok ? 'Back to work!' : 'Error'), r.ok ? 'success' : 'error');
    if (r.ok) { if (clockInterval) { clearInterval(clockInterval); clockInterval = null; } refreshTsStatus(); }
  });
}

// ── My Timesheets ─────────────────────────────────────
var histView = 'table'; // 'table' or 'calendar'
var histData = [];
var histHolidays = [];

function loadHistory() {
  populateYears('h-year');
  var year  = val('h-year')  || new Date().getFullYear();
  var month = val('h-month') || (new Date().getMonth() + 1);

  // Fetch timesheets and holidays in parallel
  api('/api/timesheets/history?year=' + year + '&month=' + month).then(function(r) {
    histData = (r.ok && r.timesheets) ? r.timesheets : [];
    if (r.ok) {
      var tbody = el('hist-body');
      if (!histData.length) {
        if (tbody) tbody.innerHTML = emptyRow(6, 'No records found');
        if (el('hist-total')) el('hist-total').textContent = '00:00:00';
      } else {
        if (tbody) tbody.innerHTML = histData.map(function(t) {
          return '<tr>' +
            '<td class="mono">' + t.date + '</td>' +
            '<td class="mono">' + (t.clock_in  || '-') + '</td>' +
            '<td class="mono">' + (t.clock_out || '-') + '</td>' +
            '<td class="mono">' + t.break_display + '</td>' +
            '<td class="mono fw-700" style="color:var(--tt-accent)">' + t.worked_display + '</td>' +
            '<td><span class="badge" style="background:rgba(245,158,11,.12);color:#f59e0b;font-size:10px">' + (t.timezone || 'IST') + '</span></td>' +
            '<td><span class="badge ' + (t.clock_out ? 'badge-done' : 'badge-active') + '">' + (t.clock_out ? 'Done' : 'Active') + '</span></td>' +
            '</tr>';
        }).join('');
        if (el('hist-total')) el('hist-total').textContent = r.total_display;
      }
    }
    // Fetch holidays for this month
    api('/api/admin/holidays?year=' + year + '&month=' + month).then(function(hr) {
      histHolidays = (hr.ok && hr.holidays) ? hr.holidays : [];
      if (histView === 'calendar') renderHistCalendar();
    });
    if (histView === 'calendar') renderHistCalendar();
  });
}

function toggleHistView(view) {
  histView = view;
  var tableWrap = el('hist-table-wrap');
  var calWrap   = el('hist-cal-wrap');
  var btnTable  = el('hist-btn-table');
  var btnCal    = el('hist-btn-cal');
  if (tableWrap) tableWrap.style.display = (view === 'table') ? '' : 'none';
  if (calWrap)   calWrap.style.display   = (view === 'calendar') ? '' : 'none';
  if (btnTable)  btnTable.classList.toggle('active', view === 'table');
  if (btnCal)    btnCal.classList.toggle('active', view === 'calendar');
  if (view === 'calendar') renderHistCalendar();
}

function renderHistCalendar() {
  var wrap = el('hist-cal-wrap');
  if (!wrap) return;
  var year  = parseInt(val('h-year')  || new Date().getFullYear());
  var month = parseInt(val('h-month') || (new Date().getMonth() + 1));

  // Build lookup maps
  var tsMap = {};
  histData.forEach(function(t) { tsMap[t.date] = t; });
  var holMap = {};
  histHolidays.forEach(function(h) { holMap[h.date] = h; });

  var MONTHS = ['','January','February','March','April','May','June','July','August','September','October','November','December'];
  var DAYS   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  var today  = new Date().toISOString().slice(0,10);

  var firstDay = new Date(year, month-1, 1).getDay();
  var daysInMonth = new Date(year, month, 0).getDate();

  var html = '<div class="cal-grid">';
  // Day headers
  DAYS.forEach(function(d) {
    html += '<div class="cal-header">' + d + '</div>';
  });
  // Empty cells before first day
  for (var i = 0; i < firstDay; i++) {
    html += '<div class="cal-cell empty"></div>';
  }
  // Day cells
  for (var day = 1; day <= daysInMonth; day++) {
    var dateStr = year + '-' + String(month).padStart(2,'0') + '-' + String(day).padStart(2,'0');
    var dow = new Date(year, month-1, day).getDay();
    var isWeekend = (dow === 0 || dow === 6);
    var isToday   = (dateStr === today);
    var tsRec     = tsMap[dateStr];
    var holRec    = holMap[dateStr];

    var cls = 'cal-cell';
    var badge = '';
    var info  = '';

    if (holRec) {
      cls += ' cal-holiday';
      badge = '<div class="cal-badge cal-badge-holiday">' + escHtml(holRec.name) + '</div>';
    } else if (tsRec && tsRec.clock_out) {
      cls += ' cal-present';
      badge = '<div class="cal-badge cal-badge-present">' + tsRec.worked_display + '</div>';
    } else if (tsRec && !tsRec.clock_out) {
      cls += ' cal-active';
      badge = '<div class="cal-badge cal-badge-active">Active</div>';
    } else if (isWeekend) {
      cls += ' cal-weekend';
    } else if (dateStr < today) {
      cls += ' cal-absent';
      badge = '<div class="cal-badge cal-badge-absent">Absent</div>';
    }

    if (isToday) cls += ' cal-today';

    html += '<div class="' + cls + '">';
    html += '<div class="cal-day-num">' + day + '</div>';
    html += badge;
    html += '</div>';
  }
  html += '</div>';

  // Legend
  html += '<div class="cal-legend">';
  html += '<span class="cal-leg-item"><span class="cal-leg-dot" style="background:#22c55e"></span>Present</span>';
  html += '<span class="cal-leg-item"><span class="cal-leg-dot" style="background:#ef4444"></span>Absent</span>';
  html += '<span class="cal-leg-item"><span class="cal-leg-dot" style="background:#f59e0b"></span>Holiday</span>';
  html += '<span class="cal-leg-item"><span class="cal-leg-dot" style="background:#94a3b8"></span>Weekend</span>';
  html += '<span class="cal-leg-item"><span class="cal-leg-dot" style="background:#38bdf8"></span>Active</span>';
  html += '</div>';

  wrap.innerHTML = html;
}

// ════ ADMIN / MANAGER ════════════════════════════════

function loadAdminDash() {
  api('/api/admin/overview').then(function(ov) {
    if (ov.ok) {
      el('a-emp').textContent = ov.total_employees;
      el('a-in').textContent  = ov.clocked_in_today;
      el('a-brk').textContent = ov.on_break;
      el('a-avg').textContent = ov.avg_hours_month;
    }
  });
  drawProdChart();
}

function showClockedInList() {
  api('/api/admin/clocked-in').then(function(r) {
    var modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-attendance-detail'));
    el('attendance-modal-title').textContent = 'Currently Clocked In';
    if (!r.ok || !r.users || !r.users.length) {
      el('attendance-modal-body').innerHTML = '<div class="text-muted text-center py-4">Nobody is clocked in right now.</div>';
    } else {
      el('attendance-modal-body').innerHTML = attendanceTable(r.users, false);
    }
    modal.show();
  });
}

function showOnBreakList() {
  api('/api/admin/on-break').then(function(r) {
    var modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-attendance-detail'));
    el('attendance-modal-title').textContent = 'Currently On Break';
    if (!r.ok || !r.users || !r.users.length) {
      el('attendance-modal-body').innerHTML = '<div class="text-muted text-center py-4">Nobody is on break right now.</div>';
    } else {
      el('attendance-modal-body').innerHTML = attendanceTable(r.users, true);
    }
    modal.show();
  });
}

function attendanceTable(users, isBreak) {
  var html = '<div class="table-responsive"><table class="table tt-table mb-0">';
  html += '<thead><tr><th>Employee</th><th>Department</th><th>Clock In</th><th>Timezone</th>';
  if (isBreak) html += '<th>Break Since</th>';
  html += '<th class="text-end">Action</th></tr></thead><tbody>';
  users.forEach(function(u) {
    var ci = u.clock_in ? u.clock_in.slice(11,16) : '-';
    var tz = u.ts_tz || u.user_tz || '-';
    html += '<tr>' +
      '<td class="fw-600">' + escHtml(u.full_name) + '</td>' +
      '<td><span class="badge bg-secondary">' + (u.department || '-') + '</span></td>' +
      '<td class="mono">' + ci + '</td>' +
      '<td><span class="badge" style="background:rgba(245,158,11,.15);color:#f59e0b">' + tz + '</span></td>';
    if (isBreak) {
      var bi = u.break_in ? u.break_in.slice(11,16) : '-';
      html += '<td class="mono">' + bi + '</td>';
    }
    html += '<td class="text-end">' +
      '<button class="btn btn-sm btn-outline-danger py-1 px-2" data-tsid="' + u.ts_id + '" data-name="' + u.full_name.replace(/"/g,"") + '" onclick="doAutoClockout(this.dataset.tsid,this.dataset.name)" title="Force clock out at 23:59">' +
      '<i class="bi bi-stop-circle me-1"></i>Auto Clock Out</button>' +
      '</td></tr>';
  });
  html += '</tbody></table></div>';
  html += '<div class="mt-3 p-3 rounded" style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);font-size:12px;color:#94a3b8;">';
  html += '<i class="bi bi-info-circle me-2"></i>Auto Clock Out sets the clock-out time to 23:59 of the user timezone date.';
  html += '</div>';
  return html;
}

function doAutoClockout(tsId, name) {
  if (!confirm('Force clock out "' + name + '" at 23:59? This cannot be undone.')) return;
  api('/api/admin/auto-clockout', 'POST', { ts_id: tsId }).then(function(r) {
    if (r.ok) {
      toast(name + ' clocked out at 23:59', 'success');
      // Refresh the modal list
      var title = el('attendance-modal-title');
      if (title && title.textContent === 'Currently On Break') showOnBreakList();
      else showClockedInList();
      // Refresh overview cards
      loadAdminDash();
    } else {
      toast(r.message || 'Error', 'error');
    }
  });
}

function drawProdChart() {
  api('/api/admin/productivity?months=6').then(function(r) {
    if (!r.ok) return;
    var COLORS = ['#f59e0b', '#22c55e', '#38bdf8', '#818cf8', '#ef4444', '#fb923c', '#a3e635', '#34d399'];
    var ctx = el('prod-chart').getContext('2d');
    if (prodChart) prodChart.destroy();
    prodChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: r.labels,
        datasets: r.data.map(function(emp, i) {
          return {
            label: emp.name, data: emp.monthly_hours,
            borderColor: COLORS[i % COLORS.length],
            backgroundColor: COLORS[i % COLORS.length] + '18',
            borderWidth: 2.5, tension: 0.45, fill: true, pointRadius: 4, pointHoverRadius: 6
          };
        })
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend:  { labels: { color: '#94a3b8', font: { family: 'Outfit', size: 12 }, boxWidth: 12 }},
          tooltip: { backgroundColor: '#1a1d27', borderColor: '#2e3248', borderWidth: 1, titleColor: '#e2e8f0', bodyColor: '#94a3b8' }
        },
        scales: {
          x: { grid: { color: '#1a1d27' }, ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 11 }}},
          y: { grid: { color: '#1a1d27' }, ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 11 }},
               title: { display: true, text: 'Hours', color: '#475569', font: { size: 11 }}}
        }
      }
    });
  });
}

function loadAdminTs() {
  populateYears('at-year');
  var empEl = el('at-emp');
  // Only populate employee dropdown if empty (preserve selection on filter change)
  if (!empEl || empEl.options.length <= 1) {
    fillEmpSelect('at-emp', true).then(function() {
      fetchAdminTs();
    });
  } else {
    fetchAdminTs();
  }
}

function fetchAdminTs() {
  var empId = val('at-emp');
  var url = '/api/admin/timesheets?year=' + val('at-year') + '&month=' + val('at-month') +
            (empId ? '&emp_id=' + empId : '');
  api(url).then(function(r) {
    var tbody = el('admin-ts-body');
    if (!r.ok || !r.timesheets || !r.timesheets.length) { tbody.innerHTML = emptyRow(8, 'No records'); return; }
    tbody.innerHTML = r.timesheets.map(function(t) {
      return '<tr>' +
        '<td class="fw-600">' + escHtml(t.full_name) + '</td>' +
        '<td><span class="badge bg-secondary">' + (t.department || '-') + '</span></td>' +
        '<td class="mono">' + t.date + '</td>' +
        '<td class="mono">' + (t.clock_in  || '-') + '</td>' +
        '<td class="mono">' + (t.clock_out || '-') + '</td>' +
        '<td class="mono">' + t.break_display + '</td>' +
        '<td class="mono fw-700" style="color:var(--tt-accent)">' + t.worked_display + '</td>' +
        '<td><span class="badge" style="background:rgba(245,158,11,.12);color:#f59e0b;font-size:10px">' + (t.timezone || 'IST') + '</span></td>' +
        '<td><span class="badge ' + (t.clock_out ? 'badge-done' : 'badge-active') + '">' + (t.clock_out ? 'Done' : 'Active') + '</span></td>' +
        '</tr>';
    }).join('');
  });
}

// ── Users ─────────────────────────────────────────────
function loadUsers() {
  api('/api/admin/users').then(function(r) {
    var tbody = el('users-body');
    if (!r.ok || !r.users || !r.users.length) { tbody.innerHTML = emptyRow(7, 'No users found'); return; }
    tbody.innerHTML = r.users.map(function(u) {
      var ini = u.full_name.split(' ').map(function(w) { return w[0]; }).join('').slice(0, 2).toUpperCase();
      var avatarHtml = u.photo
        ? '<div style="width:34px;height:34px;border-radius:8px;overflow:hidden;flex-shrink:0"><img src="' + u.photo + '" style="width:100%;height:100%;object-fit:cover"/></div>'
        : '<div style="width:34px;height:34px;background:linear-gradient(135deg,var(--tt-accent),#f97316);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;color:#000;flex-shrink:0">' + ini + '</div>';
      return '<tr>' +
        '<td><div class="d-flex align-items-center gap-2">' +
          avatarHtml +
          '<div><div class="fw-600">' + escHtml(u.full_name) + '</div><div class="mono text-muted" style="font-size:11px">@' + u.username + '</div></div>' +
        '</div></td>' +
        '<td class="text-muted small">' + escHtml(u.email) + '</td>' +
        '<td><span class="badge bg-secondary">' + (u.department || '-') + '</span></td>' +
        '<td><span class="badge badge-role-' + u.role + '">' + u.role + '</span></td>' +
        '<td class="mono text-muted" style="font-size:12px">' + (u.shift_start || '-') + ' - ' + (u.shift_end || '-') + '</td>' +
        '<td><span class="badge ' + (u.is_active ? 'badge-done' : 'badge-inactive') + '">' + (u.is_active ? 'Active' : 'Inactive') + '</span></td>' +
        '<td class="text-end"><div class="d-flex gap-1 justify-content-end">' +
          '<button class="btn btn-sm btn-outline-secondary py-1 px-2" title="Edit" onclick="openEditUserModal(' + u.id + ')"><i class="bi bi-pencil"></i></button>' +
          '<button class="btn btn-sm btn-outline-secondary py-1 px-2" onclick="openRoleModal(' + u.id + ',\'' + escHtml(u.full_name) + '\',\'' + u.role + '\')"><i class="bi bi-shield-lock"></i></button>' +
          '<button class="btn btn-sm btn-outline-secondary py-1 px-2" onclick="toggleActive(' + u.id + ',' + u.is_active + ')"><i class="bi bi-person-' + (u.is_active ? 'dash' : 'check') + '"></i></button>' +
          '<button class="btn btn-sm btn-danger py-1 px-2" onclick="deleteUser(' + u.id + ',\'' + escHtml(u.full_name) + '\')"><i class="bi bi-trash3"></i></button>' +
        '</div></td>' +
        '</tr>';
    }).join('');
  });
}

function openAddUserModal() { bsAddUserModal.show(); }

function doAddUser() {
  var errEl = el('nu-err');
  errEl.classList.add('d-none');
  var data = {
    full_name: val('nu-name'), username: val('nu-user'), email: val('nu-email'),
    password: val('nu-pass'), department: val('nu-dept'), role: val('nu-role'),
    shift_start: val('nu-start'), shift_end: val('nu-end')
  };
  if (!data.full_name || !data.username || !data.email || !data.password) {
    errEl.textContent = 'Full name, username, email and password required';
    errEl.classList.remove('d-none'); return;
  }
  api('/api/admin/users', 'POST', data).then(function(r) {
    if (r.ok) {
      bsAddUserModal.hide(); toast('User created!', 'success'); loadUsers();
      ['nu-name', 'nu-user', 'nu-email', 'nu-pass', 'nu-dept'].forEach(function(id) { if (el(id)) el(id).value = ''; });
    } else { errEl.textContent = r.message || 'Failed'; errEl.classList.remove('d-none'); }
  });
}

function openRoleModal(uid, name, role) {
  el('role-target-id').value = uid;
  el('role-target-name').textContent = name;
  el('role-select').value = role;
  bsRoleModal.show();
}

function doChangeRole() {
  var uid = el('role-target-id').value, role = val('role-select');
  api('/api/admin/users/' + uid + '/role', 'PATCH', { role: role }).then(function(r) {
    if (r.ok) { bsRoleModal.hide(); toast('Role updated to "' + role + '"', 'success'); loadUsers(); }
    else toast(r.message || 'Failed', 'error');
  });
}

function toggleActive(uid, isActive) {
  api('/api/admin/users/' + uid, 'PUT', { is_active: !isActive }).then(function(r) {
    if (r.ok) { toast(isActive ? 'Deactivated' : 'Activated', 'info'); loadUsers(); }
    else toast(r.message, 'error');
  });
}

function deleteUser(uid, name) {
  if (!confirm('Delete "' + name + '"?')) return;
  api('/api/admin/users/' + uid, 'DELETE').then(function(r) {
    if (r.ok) { toast('Deleted', 'success'); loadUsers(); }
    else toast(r.message, 'error');
  });
}

function openExportModal() {
  populateYears('exp-year');
  fillEmpSelect('exp-emp', true).then(function() {
    // Default to current month
    el('exp-month').value = new Date().getMonth() + 1;
    // Pre-fill year/month from All Timesheets filter (but NOT the employee)
    var atYear  = val('at-year');
    var atMonth = val('at-month');
    if (atYear  && el('exp-year'))  el('exp-year').value  = atYear;
    if (atMonth && el('exp-month')) el('exp-month').value = atMonth;
    // Always default to All Users (empty) so admin can choose
    if (el('exp-emp')) el('exp-emp').value = '';
    bsExportModal.show();
  });
}

function doExport() {
  var emp_id = val('exp-emp');
  var year   = parseInt(val('exp-year'));
  var month  = parseInt(val('exp-month'));
  // emp_id empty means "All Users"
  var payload = { year: year, month: month };
  if (emp_id) payload.emp_id = parseInt(emp_id);
  console.log('Export payload:', JSON.stringify(payload));
  api('/api/admin/export', 'POST', payload).then(function(r) {
    if (!r.ok) { toast(r.message || 'Export failed', 'error'); return; }
    var bytes = atob(r.csv_b64), arr = new Uint8Array(bytes.length);
    for (var i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([arr], { type: 'text/csv' }));
    a.download = r.filename; a.click(); URL.revokeObjectURL(a.href);
    bsExportModal.hide();
    toast('Downloaded: ' + r.filename, 'success');
  });
}

// ════ SHARED SHEET (per-user, My Sheets style) ══════

var ssColumns = [];
var ssRows    = [];
var ssCurRow  = -1;
var ssCurCol  = -1;

function loadSharedSheet() {
  var isAdmin = currentUser && currentUser.role === 'admin';
  var configBtn = el('btn-config-sheet');
  if (configBtn) configBtn.style.display = isAdmin ? '' : 'none';

  api('/api/shared-sheet/').then(function(r) {
    if (!r.ok) {
      el('ss-empty').style.display = '';
      el('ss-scroll').style.display = 'none';
      if (el('ss-toolbar')) el('ss-toolbar').style.display = 'none';
      if (el('ss-empty-msg')) el('ss-empty-msg').textContent = 'Failed to load. Please refresh.';
      return;
    }
    ssColumns = r.sheet.columns || [];
    ssRows    = r.sheet.rows    || [];
    if (el('shared-sheet-title')) el('shared-sheet-title').textContent = r.sheet.name || 'Shared Sheet';
    renderSharedSheet();
  });
}

function renderSharedSheet() {
  var emptyEl   = el('ss-empty');
  var scrollEl  = el('ss-scroll');
  var toolbarEl = el('ss-toolbar');

  if (!ssColumns.length) {
    if (emptyEl)   emptyEl.style.display   = '';
    if (scrollEl)  scrollEl.style.display  = 'none';
    if (toolbarEl) toolbarEl.style.display = 'none';
    if (el('ss-empty-msg')) {
      el('ss-empty-msg').innerHTML = (currentUser.role === 'admin')
        ? 'Click <strong>Configure Columns</strong> above to set up the sheet.'
        : 'Contact your admin to set up columns.';
    }
    return;
  }

  if (emptyEl)   emptyEl.style.display   = 'none';
  if (scrollEl)  scrollEl.style.display  = '';
  if (toolbarEl) toolbarEl.style.display = '';

  if (!ssRows.length) ssRows.push(makeSsRow());

  var h = '<table class="sheet-grid"><thead><tr><th></th>';
  ssColumns.forEach(function(col) {
    h += '<th style="min-width:150px;width:150px">' + escHtml(col.label) + '</th>';
  });
  h += '<th style="width:34px"></th></tr></thead><tbody>';

  ssRows.forEach(function(row, ri) {
    h += '<tr><td>' + (ri + 1) + '</td>';
    ssColumns.forEach(function(col, ci) {
      var v     = (row[col.key] !== undefined && row[col.key] !== null) ? String(row[col.key]) : '';
      var isSel = (ri === ssCurRow && ci === ssCurCol);
      var iType = (col.type === 'date') ? 'date' : (col.type === 'number' ? 'number' : 'text');
      h += '<td data-r="' + ri + '" data-c="' + ci + '" class="' + (isSel ? 'sel' : '') + '" onclick="ssSelCell(' + ri + ',' + ci + ')">';
      h += '<input type="' + iType + '" class="cell-inp ss-cell" value="' + escHtml(v) + '"';
      h += ' data-r="' + ri + '" data-c="' + ci + '" data-key="' + escHtml(col.key) + '"';
      h += ' onfocus="ssSelCell(' + ri + ',' + ci + ')"';
      h += ' onkeydown="ssCellKey(event,' + ri + ',' + ci + ')"';
      h += '/></td>';
    });
    h += '<td style="padding:0;text-align:center;background:var(--tt-surface)">';
    h += '<button class="btn btn-link text-danger p-0" style="font-size:11px;line-height:1" onclick="ssDelRow(' + ri + ')"><i class="bi bi-x-lg"></i></button>';
    h += '</td></tr>';
  });

  h += '</tbody></table>';
  scrollEl.innerHTML = h;

  // Attach input listeners
  document.querySelectorAll('#ss-scroll .ss-cell').forEach(function(inp) {
    inp.addEventListener('input', function() {
      var r2  = parseInt(inp.dataset.r);
      var key = inp.dataset.key;
      if (!ssRows[r2]) ssRows[r2] = makeSsRow();
      ssRows[r2][key] = inp.value;
    });
  });
}

function makeSsRow() {
  var row = {};
  ssColumns.forEach(function(col) { row[col.key] = ''; });
  return row;
}
function makeSsRow() {
  var row = {};
  ssColumns.forEach(function(col) { row[col.key] = ''; });
  return row;
}

function ssUpdateFormulaBar() {
  var fb  = el('ss-formula-bar');
  var ref = el('ss-cell-ref');
  if (!fb || ssCurRow < 0 || ssCurCol < 0) return;
  var col = ssColumns[ssCurCol];
  if (!col) return;
  var v   = (ssRows[ssCurRow] && ssRows[ssCurRow][col.key] !== undefined) ? ssRows[ssCurRow][col.key] : '';
  fb.value = String(v);
  var L = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  var colLetter = ssCurCol < 26 ? L[ssCurCol] : L[Math.floor(ssCurCol/26)-1] + L[ssCurCol%26];
  if (ref) ref.textContent = colLetter + (ssCurRow + 1);
}

function ssFormulaBarIn(v) {
  if (ssCurRow < 0 || ssCurCol < 0) return;
  var col = ssColumns[ssCurCol];
  if (!col) return;
  if (!ssRows[ssCurRow]) ssRows[ssCurRow] = makeSsRow();
  ssRows[ssCurRow][col.key] = v;
  var inp = document.querySelector('#ss-scroll .ss-cell[data-r="' + ssCurRow + '"][data-c="' + ssCurCol + '"]');
  if (inp) inp.value = v;
}

function ssSelCell(r, c) {
  ssCurRow = r; ssCurCol = c;
  document.querySelectorAll('#ss-scroll td[data-r]').forEach(function(td) {
    td.classList.toggle('sel', +td.dataset.r === r && +td.dataset.c === c);
  });
}

function ssCellIn(r, colKey, v) {
  if (!ssRows[r]) ssRows[r] = {};
  ssRows[r][colKey] = v;
}

function ssCellKey(e, r, c) {
  if (e.key === 'Enter') {
    e.preventDefault();
    if (r + 1 < ssRows.length) {
      ssSelCell(r + 1, c);
      var inp = document.querySelector('#ss-scroll .cell-inp[data-r="' + (r+1) + '"][data-c="' + c + '"]');
      if (inp) inp.focus();
    } else {
      ssAddRow(c);
    }
  }
  if (e.key === 'Tab') {
    e.preventDefault();
    if (c + 1 < ssColumns.length) {
      ssSelCell(r, c + 1);
      var inp2 = document.querySelector('#ss-scroll .cell-inp[data-r="' + r + '"][data-c="' + (c+1) + '"]');
      if (inp2) inp2.focus();
    }
  }
}

function ssAddRow(focusCol) {
  var newRow = {};
  ssColumns.forEach(function(col) { newRow[col.key] = ''; });
  ssRows.push(newRow);
  ssCurRow = ssRows.length - 1;
  ssCurCol = (focusCol !== undefined) ? focusCol : 0;
  renderSharedSheet();
  setTimeout(function() {
    var inp = document.querySelector('#ss-scroll .cell-inp[data-r="' + (ssRows.length-1) + '"][data-c="' + ssCurCol + '"]');
    if (inp) inp.focus();
  }, 30);
}

function ssDelRow(idx) {
  if (idx < 0 || idx >= ssRows.length) return;
  ssRows.splice(idx, 1);
  if (!ssRows.length) ssRows.push({});
  ssCurRow = -1; ssCurCol = -1;
  renderSharedSheet();
}

function saveSharedData() {
  api('/api/shared-sheet/save', 'POST', { rows: ssRows }).then(function(r) {
    toast(r.ok ? 'Saved!' : (r.message || 'Save failed'), r.ok ? 'success' : 'error');
  });
}

function downloadSharedCSV() {
  if (!ssColumns.length) { toast('No columns configured', 'error'); return; }
  var header = ssColumns.map(function(c) { return '"' + escHtml(c.label) + '"'; }).join(',');
  var rows   = ssRows.map(function(row) {
    return ssColumns.map(function(c) {
      var v = (row[c.key] !== undefined && row[c.key] !== null) ? row[c.key] : '';
      return '"' + v.toString().replace(/"/g, '""') + '"';
    }).join(',');
  });
  var csv = [header].concat(rows).join('\n');
  var a   = document.createElement('a');
  a.href  = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = 'my-shared-sheet.csv';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('CSV downloaded!', 'success');
}

function openSheetConfig() {
  api('/api/shared-sheet/').then(function(r) {
    if (!r.ok) return;
    el('sc-name').value = r.sheet.name || 'Shared Sheet';
    el('sc-columns').innerHTML = '';
    var cols = r.sheet.columns || [];
    if (!cols.length) cols = [{ key: 'col1', label: 'Column 1', type: 'text' }];
    cols.forEach(function(col) { renderConfigColumn(col); });
    bsSheetConfigModal.show();
  });
}

function renderConfigColumn(col) {
  var div = document.createElement('div');
  div.className = 'col-row';
  div.innerHTML =
    '<input type="text" class="form-control form-control-sm" placeholder="Column label" value="' + escHtml(col.label || '') + '" style="flex:1;background:#13151c;border-color:#2e3248;color:#e2e8f0;" data-field="label"/>' +
    '<input type="text" class="form-control form-control-sm" placeholder="Key (no spaces)" value="' + escHtml(col.key || '') + '" style="width:110px;background:#13151c;border-color:#2e3248;color:#e2e8f0;" data-field="key"/>' +
    '<select class="form-select form-select-sm" style="width:90px;background:#13151c;border-color:#2e3248;color:#e2e8f0;" data-field="type">' +
      '<option value="text"'   + (col.type === 'text'   ? ' selected' : '') + '>Text</option>' +
      '<option value="number"' + (col.type === 'number' ? ' selected' : '') + '>Number</option>' +
      '<option value="date"'   + (col.type === 'date'   ? ' selected' : '') + '>Date</option>' +
    '</select>' +
    '<button class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()"><i class="bi bi-trash3"></i></button>';
  el('sc-columns').appendChild(div);
}

function addSheetColumn() {
  var idx = el('sc-columns').children.length + 1;
  renderConfigColumn({ key: 'col' + idx, label: 'Column ' + idx, type: 'text' });
}

function saveSheetConfig() {
  var errEl = el('sc-err');
  errEl.classList.add('d-none');
  var name = val('sc-name') || 'Shared Sheet';
  var cols = [];
  el('sc-columns').querySelectorAll('.col-row').forEach(function(row, i) {
    var label = row.querySelector('[data-field="label"]').value.trim();
    var key   = row.querySelector('[data-field="key"]').value.trim().replace(/\s+/g, '_') || ('col' + (i+1));
    var type  = row.querySelector('[data-field="type"]').value;
    if (label) cols.push({ key: key, label: label, type: type });
  });
  if (!cols.length) { errEl.textContent = 'Add at least one column'; errEl.classList.remove('d-none'); return; }
  api('/api/shared-sheet/config', 'PUT', { name: name, columns: cols }).then(function(r) {
    if (r.ok) { bsSheetConfigModal.hide(); toast('Columns configured!', 'success'); loadSharedSheet(); }
    else { errEl.textContent = r.message || 'Failed'; errEl.classList.remove('d-none'); }
  });
}

// ════ PERSONAL SPREADSHEET ══════════════════════════

function loadSpreadsheet() {
  api('/api/spreadsheet/').then(function(r) { renderSheetList(r.ok ? r.sheets : []); });
}

function renderSheetList(sheets) {
  var wrap = el('sheet-list');
  if (!sheets || !sheets.length) { wrap.innerHTML = '<div class="text-muted small text-center">No sheets yet</div>'; return; }
  wrap.innerHTML = sheets.map(function(s) {
    return '<div class="sheet-item ' + (s.id === sheetId ? 'active' : '') + '" onclick="openSheet(' + s.id + ')">' +
      '<span><i class="bi bi-file-earmark me-1"></i>' + escHtml(s.name) + '</span>' +
      '<button class="sheet-del-btn" onclick="event.stopPropagation();delSheet(' + s.id + ')" title="Delete">x</button></div>';
  }).join('');
}

function newSheet() {
  var name = prompt('Sheet name:', 'My Sheet');
  if (!name) return;
  api('/api/spreadsheet/', 'POST', { name: name }).then(function(r) { if (r.ok) { loadSpreadsheet(); openSheet(r.id); } });
}

function openSheet(id) {
  api('/api/spreadsheet/' + id).then(function(r) {
    if (!r.ok) return;
    sheetId = r.sheet.id; sheetName = r.sheet.name; sheetData = r.sheet.data;
    colWidths = {}; selRow = -1; selCol = -1;
    el('sheet-current-name').textContent = sheetName;
    el('sheet-empty').style.display = 'none';
    el('sheet-editor').style.display = 'flex';
    renderSheet(); loadSpreadsheet();
  });
}

function delSheet(id) {
  if (!confirm('Delete?')) return;
  api('/api/spreadsheet/' + id, 'DELETE').then(function() {
    if (id === sheetId) { sheetId = null; sheetData = null; el('sheet-empty').style.display = ''; el('sheet-editor').style.display = 'none'; el('sheet-current-name').textContent = 'No sheet open'; }
    loadSpreadsheet();
  });
}

function renderSheet() {
  if (!sheetData) return;
  var rows = sheetData.length, cols = sheetData[0] ? sheetData[0].length : 0, L = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  function CL(c) { return c < 26 ? L[c] : L[Math.floor(c / 26) - 1] + L[c % 26]; }
  var h = '<table class="sheet-grid"><thead><tr><th></th>';
  for (var c = 0; c < cols; c++) h += '<th style="width:' + (colWidths[c] || 110) + 'px" data-col="' + c + '">' + CL(c) + '</th>';
  h += '</tr></thead><tbody>';
  for (var ri = 0; ri < rows; ri++) {
    h += '<tr><td>' + (ri + 1) + '</td>';
    for (var ci = 0; ci < cols; ci++) {
      var cell = (sheetData[ri] && sheetData[ri][ci]) ? sheetData[ri][ci] : {};
      var isSel = (ri === selRow && ci === selCol);
      var sty = [cell.bold ? 'font-weight:700' : '', cell.italic ? 'font-style:italic' : '',
        'text-align:' + (cell.align || 'left'), 'color:' + (cell.color || '#e2e8f0'),
        'background:' + (cell.bg || 'transparent'), 'width:' + (colWidths[ci] || 110) + 'px'].filter(Boolean).join(';');
      h += '<td data-r="' + ri + '" data-c="' + ci + '" class="' + (isSel ? 'sel' : '') + '" onclick="selCell(' + ri + ',' + ci + ')" style="' + sty + '">' +
           '<input class="cell-inp mono" style="' + sty + '" value="' + escHtml(cell.v || '') + '" data-r="' + ri + '" data-c="' + ci + '" ' +
           'oninput="cellIn(' + ri + ',' + ci + ',this.value)" onfocus="selCell(' + ri + ',' + ci + ')" onkeydown="cellKey(event,' + ri + ',' + ci + ')"/></td>';
    }
    h += '</tr>';
  }
  h += '</tbody></table>';
  el('sheet-scroll').innerHTML = h;
}

function selCell(r, c) {
  selRow = r; selCol = c;
  document.querySelectorAll('.sheet-grid td[data-r]').forEach(function(td) { td.classList.toggle('sel', +td.dataset.r === r && +td.dataset.c === c); });
  var cell = (sheetData[r] && sheetData[r][c]) ? sheetData[r][c] : {};
  if (el('formula-bar-input')) el('formula-bar-input').value = cell.v || '';
  if (el('txt-color')) el('txt-color').value = cell.color || '#e2e8f0';
  if (el('bg-color'))  el('bg-color').value  = cell.bg    || '#ffffff';
}

function cellIn(r, c, v) {
  if (!sheetData[r]) return;
  if (!sheetData[r][c]) sheetData[r][c] = emptyCell();
  sheetData[r][c].v = v;
  if (r === selRow && c === selCol && el('formula-bar-input')) el('formula-bar-input').value = v;
}

function cellKey(e, r, c) {
  if (e.key === 'Enter') { e.preventDefault(); if (r + 1 < sheetData.length) { selCell(r + 1, c); var i1 = document.querySelector('.cell-inp[data-r="' + (r + 1) + '"][data-c="' + c + '"]'); if (i1) i1.focus(); }}
  if (e.key === 'Tab')   { e.preventDefault(); if (sheetData[0] && c + 1 < sheetData[0].length) { selCell(r, c + 1); var i2 = document.querySelector('.cell-inp[data-r="' + r + '"][data-c="' + (c + 1) + '"]'); if (i2) i2.focus(); }}
}

function applyFormulaBar(v) {
  if (selRow < 0) return;
  if (!sheetData[selRow][selCol]) sheetData[selRow][selCol] = emptyCell();
  sheetData[selRow][selCol].v = v;
  var inp = document.querySelector('.cell-inp[data-r="' + selRow + '"][data-c="' + selCol + '"]');
  if (inp) inp.value = v;
}

function fmt(t)         { if (selRow < 0) return; sheetData[selRow][selCol][t] = !sheetData[selRow][selCol][t]; renderSheet(); selCell(selRow, selCol); }
function fmtAlign(a)    { if (selRow < 0) return; sheetData[selRow][selCol].align = a; renderSheet(); selCell(selRow, selCol); }
function fmtColor(c)    { if (selRow < 0) return; sheetData[selRow][selCol].color = c; renderSheet(); selCell(selRow, selCol); }
function fmtBg(c)       { if (selRow < 0) return; sheetData[selRow][selCol].bg    = c; renderSheet(); selCell(selRow, selCol); }
function setColWidth(w) { if (selCol < 0) return; colWidths[selCol] = +w; renderSheet(); selCell(selRow, selCol); }

function addRow() { if (!sheetData) return; sheetData.push(Array.from({ length: sheetData[0] ? sheetData[0].length : 10 }, emptyCell)); renderSheet(); }
function addCol() { if (!sheetData) return; sheetData.forEach(function(r) { r.push(emptyCell()); }); renderSheet(); }
function delRow() { if (!sheetData || sheetData.length <= 1) return; sheetData.splice(selRow >= 0 ? selRow : sheetData.length - 1, 1); selRow = -1; renderSheet(); }
function delCol() { if (!sheetData || !sheetData[0] || sheetData[0].length <= 1) return; sheetData.forEach(function(r) { r.splice(selCol >= 0 ? selCol : r.length - 1, 1); }); selCol = -1; renderSheet(); }

function evalFormulas() {
  if (!sheetData) return;
  var L = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  function ref(s) { var m = s.match(/^([A-Z]+)(\d+)$/i); if (!m) return 0; return parseFloat((sheetData[parseInt(m[2]) - 1] && sheetData[parseInt(m[2]) - 1][L.indexOf(m[1].toUpperCase())]) ? sheetData[parseInt(m[2]) - 1][L.indexOf(m[1].toUpperCase())].v : 0) || 0; }
  function range(expr) { var m = expr.match(/([A-Z]\d+):([A-Z]\d+)/i); if (!m) return []; var r1 = m[1].match(/([A-Z])(\d+)/i), r2 = m[2].match(/([A-Z])(\d+)/i), vals = []; for (var ri = parseInt(r1[2]) - 1; ri <= parseInt(r2[2]) - 1; ri++) for (var ci = L.indexOf(r1[1].toUpperCase()); ci <= L.indexOf(r2[1].toUpperCase()); ci++) { var v = parseFloat((sheetData[ri] && sheetData[ri][ci]) ? sheetData[ri][ci].v : ''); if (!isNaN(v)) vals.push(v); } return vals; }
  sheetData.forEach(function(row) {
    row.forEach(function(cell) {
      if (!cell || !cell.v || !cell.v.toString().startsWith('=')) return;
      var expr = cell.v.slice(1).trim().toUpperCase();
      try {
        if      (expr.startsWith('SUM('))      cell.v = '' + range(expr).reduce(function(a, b) { return a + b; }, 0);
        else if (expr.match(/^AVG|^AVERAGE/))  { var v = range(expr); cell.v = v.length ? '' + (v.reduce(function(a, b) { return a + b; }, 0) / v.length).toFixed(2) : '0'; }
        else if (expr.startsWith('MAX('))      cell.v = '' + Math.max.apply(null, range(expr));
        else if (expr.startsWith('MIN('))      cell.v = '' + Math.min.apply(null, range(expr));
        else if (expr.startsWith('COUNT('))    cell.v = '' + range(expr).length;
        else { var res = cell.v.slice(1).replace(/[A-Z]+\d+/gi, function(m) { return ref(m.toUpperCase()); }); cell.v = '' + Function('"use strict";return(' + res + ')')(); }
      } catch(e2) { cell.v = '#ERR'; }
    });
  });
  renderSheet(); toast('Formulas evaluated', 'success');
}

function saveSheet() {
  if (!sheetId) return;
  api('/api/spreadsheet/' + sheetId, 'PUT', { name: sheetName, data: sheetData }).then(function(r) { toast(r.ok ? 'Saved' : 'Failed', r.ok ? 'success' : 'error'); });
}

function downloadCSV() {
  if (!sheetData) return;
  var csv = sheetData.map(function(row) { return row.map(function(c) { return '"' + ((c && c.v) ? c.v : '').replace(/"/g, '""') + '"'; }).join(','); }).join('\n');
  var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = (sheetName || 'sheet') + '.csv'; a.click(); URL.revokeObjectURL(a.href);
}


// ════ HOLIDAYS ════════════════════════════════════════

var bsHolidayModal = null;

function loadHolidays() {
  var year = new Date().getFullYear();
  api('/api/admin/holidays?year=' + year).then(function(r) {
    var wrap = el('holidays-list');
    if (!wrap) return;
    var holidays = (r.ok && r.holidays) ? r.holidays : [];
    if (!holidays.length) {
      wrap.innerHTML = '<div class="text-muted text-center py-4">No holidays added yet for ' + year + '</div>';
      return;
    }
    wrap.innerHTML = '<div class="table-responsive"><table class="table tt-table mb-0">' +
      '<thead><tr><th>Date</th><th>Holiday Name</th><th>Description</th><th class="text-end">Action</th></tr></thead><tbody>' +
      holidays.map(function(h) {
        var d = new Date(h.date + 'T00:00:00');
        var dayName = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][d.getDay()];
        return '<tr>' +
          '<td class="mono fw-600">' + h.date + ' <span class="text-muted small">(' + dayName + ')</span></td>' +
          '<td class="fw-600" style="color:var(--tt-accent)">' + escHtml(h.name) + '</td>' +
          '<td class="text-muted small">' + escHtml(h.description || '-') + '</td>' +
          '<td class="text-end"><button class="btn btn-sm btn-danger py-1 px-2" onclick="deleteHoliday(' + h.id + ',\'' + escHtml(h.name) + '\')"><i class="bi bi-trash3"></i></button></td>' +
          '</tr>';
      }).join('') +
      '</tbody></table></div>';
  });
}

function openAddHolidayModal() {
  if (!bsHolidayModal) bsHolidayModal = new bootstrap.Modal(document.getElementById('modal-holiday'));
  el('hol-date').value = '';
  el('hol-name').value = '';
  el('hol-desc').value = '';
  el('hol-err').classList.add('d-none');
  bsHolidayModal.show();
}

function doAddHoliday() {
  var errEl = el('hol-err');
  errEl.classList.add('d-none');
  var date = val('hol-date');
  var name = val('hol-name');
  var desc = val('hol-desc');
  if (!date) { errEl.textContent = 'Date is required'; errEl.classList.remove('d-none'); return; }
  if (!name) { errEl.textContent = 'Holiday name is required'; errEl.classList.remove('d-none'); return; }
  api('/api/admin/holidays', 'POST', { date: date, name: name, description: desc }).then(function(r) {
    if (r.ok) {
      bsHolidayModal.hide();
      toast('Holiday added!', 'success');
      loadHolidays();
    } else {
      errEl.textContent = r.message || 'Failed to add holiday';
      errEl.classList.remove('d-none');
    }
  });
}

function deleteHoliday(hid, name) {
  if (!confirm('Delete holiday "' + name + '"?')) return;
  api('/api/admin/holidays/' + hid, 'DELETE').then(function(r) {
    if (r.ok) { toast('Holiday deleted', 'success'); loadHolidays(); }
    else toast(r.message || 'Error', 'error');
  });
}


// ════ SHIFTS ══════════════════════════════════════════

var bsShiftModal    = null;
var bsEditUserModal = null;
var euPhotoData     = null; // base64 photo for edit modal
var euRemovePhoto   = false;

function loadShifts() {
  api('/api/admin/shifts').then(function(r) {
    var list = el('shifts-list');
    if (!list) return;
    var shifts = (r.ok && r.shifts) ? r.shifts : [];
    if (!shifts.length) {
      list.innerHTML = '<div class="text-muted text-center py-4">No shifts defined yet.</div>';
    } else {
      list.innerHTML = shifts.map(function(s) {
        return '<div class="d-flex align-items-center justify-content-between p-3 mb-2 rounded" style="background:var(--tt-surface2);border:1px solid var(--tt-border2)">' +
          '<div>' +
            '<div class="fw-700" style="color:var(--tt-text)">' + escHtml(s.name) + '</div>' +
            '<div class="mono small" style="color:var(--tt-accent)">' + s.start_time + ' — ' + s.end_time + '</div>' +
            (s.description ? '<div class="text-muted small">' + escHtml(s.description) + '</div>' : '') +
          '</div>' +
          '<div class="d-flex gap-1">' +
            '<button class="btn btn-sm btn-outline-secondary py-1 px-2" onclick="openEditShiftModal(' + s.id + ')"><i class="bi bi-pencil"></i></button>' +
            '<button class="btn btn-sm btn-danger py-1 px-2" data-sid="' + s.id + '" data-name="' + escHtml(s.name) + '" onclick="doDeleteShift(this.dataset.sid,this.dataset.name)"><i class="bi bi-trash3"></i></button>' +
          '</div>' +
          '</div>';
      }).join('');
    }
    // Populate assign shift select
    var sel = el('assign-shift-select');
    if (sel) {
      sel.innerHTML = '<option value="">Select a shift...</option>' +
        shifts.map(function(s) { return '<option value="' + s.id + '">' + escHtml(s.name) + ' (' + s.start_time + '-' + s.end_time + ')</option>'; }).join('');
    }
    // Populate assign users list
    loadAssignUsersList();
  });
}

function loadAssignUsersList() {
  api('/api/admin/users').then(function(r) {
    var wrap = el('assign-users-list');
    if (!wrap || !r.ok) return;
    var users = (r.users || []).filter(function(u) { return u.role !== 'admin' && u.is_active; });
    wrap.innerHTML = users.map(function(u) {
      return '<label class="d-flex align-items-center gap-2 p-2 rounded" style="cursor:pointer">' +
        '<input type="checkbox" class="assign-user-cb" value="' + u.id + '" style="accent-color:var(--tt-accent)"/>' +
        '<span class="fw-600">' + escHtml(u.full_name) + '</span>' +
        '<span class="text-muted small">(' + u.role + ')</span>' +
        '<span class="ms-auto mono small text-muted">' + (u.shift_start || '-') + '-' + (u.shift_end || '-') + '</span>' +
        '</label>';
    }).join('');
  });
}

function openAddShiftModal() {
  if (!bsShiftModal) bsShiftModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-shift'));
  el('shift-modal-title').innerHTML = '<i class="bi bi-clock me-2"></i>Add Shift';
  el('shift-edit-id').value = '';
  el('shift-name').value  = '';
  el('shift-start').value = '09:00';
  el('shift-end').value   = '18:00';
  el('shift-desc').value  = '';
  el('shift-err').classList.add('d-none');
  bsShiftModal.show();
}

function openEditShiftModal(sid) {
  api('/api/admin/shifts').then(function(r) {
    var shift = (r.shifts || []).find(function(s) { return s.id === sid; });
    if (!shift) return;
    if (!bsShiftModal) bsShiftModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-shift'));
    el('shift-modal-title').innerHTML = '<i class="bi bi-pencil me-2"></i>Edit Shift';
    el('shift-edit-id').value = shift.id;
    el('shift-name').value    = shift.name;
    el('shift-start').value   = shift.start_time;
    el('shift-end').value     = shift.end_time;
    el('shift-desc').value    = shift.description || '';
    el('shift-err').classList.add('d-none');
    bsShiftModal.show();
  });
}

function doSaveShift() {
  var errEl = el('shift-err');
  errEl.classList.add('d-none');
  var sid   = val('shift-edit-id');
  var name  = val('shift-name');
  var start = val('shift-start');
  var end   = val('shift-end');
  var desc  = val('shift-desc');
  if (!name || !start || !end) { errEl.textContent = 'Name, start and end are required'; errEl.classList.remove('d-none'); return; }
  var url    = sid ? '/api/admin/shifts/' + sid : '/api/admin/shifts';
  var method = sid ? 'PUT' : 'POST';
  var payload = sid
    ? { name: name, start_time: start, end_time: end, description: desc }
    : { name: name, start: start, end: end, description: desc };
  api(url, method, payload).then(function(r) {
    if (r.ok) {
      bsShiftModal.hide();
      toast(sid ? 'Shift updated!' : 'Shift created!', 'success');
      loadShifts();
    } else {
      errEl.textContent = r.message || 'Failed';
      errEl.classList.remove('d-none');
    }
  });
}

function doDeleteShift(sid, name) {
  if (!confirm('Delete shift "' + name + '"?')) return;
  api('/api/admin/shifts/' + sid, 'DELETE').then(function(r) {
    if (r.ok) { toast('Shift deleted', 'success'); loadShifts(); }
    else toast(r.message || 'Error', 'error');
  });
}

function doAssignShift() {
  var sid  = val('assign-shift-select');
  if (!sid) { toast('Please select a shift', 'error'); return; }
  var cbs  = document.querySelectorAll('.assign-user-cb:checked');
  var uids = Array.from(cbs).map(function(cb) { return parseInt(cb.value); });
  if (!uids.length) { toast('Please select at least one user', 'error'); return; }
  api('/api/admin/shifts/' + sid + '/assign', 'POST', { user_ids: uids }).then(function(r) {
    if (r.ok) {
      toast(r.message, 'success');
      // Uncheck all
      cbs.forEach(function(cb) { cb.checked = false; });
      loadShifts();
    } else toast(r.message || 'Error', 'error');
  });
}

// ════ EDIT USER ════════════════════════════════════════

function openEditUserModal(uid) {
  api('/api/admin/users').then(function(r) {
    var user = (r.users || []).find(function(u) { return u.id === uid; });
    if (!user) return;
    if (!bsEditUserModal) bsEditUserModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-edit-user'));
    el('eu-id').value    = uid;
    el('eu-name').value  = user.full_name || '';
    el('eu-email').value = user.email || '';
    el('eu-dept').value  = user.department || '';
    el('eu-start').value = user.shift_start || '09:00';
    el('eu-end').value   = user.shift_end   || '18:00';
    el('eu-err').classList.add('d-none');
    euPhotoData   = null;
    euRemovePhoto = false;
    // Set avatar preview
    var initials = user.full_name.split(' ').map(function(w){return w[0];}).join('').slice(0,2).toUpperCase();
    var avIni = el('eu-av-initials');
    var avImg = el('eu-av-img');
    if (avIni) avIni.textContent = initials;
    if (user.photo && avImg) {
      avImg.src = user.photo;
      avImg.style.display = '';
      if (avIni) avIni.style.display = 'none';
    } else if (avImg) {
      avImg.style.display = 'none';
      if (avIni) avIni.style.display = '';
    }
    bsEditUserModal.show();
  });
}

function previewPhoto(input) {
  if (!input.files || !input.files[0]) return;
  var file = input.files[0];
  if (file.size > 600000) { toast('Image too large. Max 500KB.', 'error'); return; }
  var reader = new FileReader();
  reader.onload = function(e) {
    euPhotoData   = e.target.result;
    euRemovePhoto = false;
    var avImg = el('eu-av-img');
    var avIni = el('eu-av-initials');
    if (avImg) { avImg.src = euPhotoData; avImg.style.display = ''; }
    if (avIni) avIni.style.display = 'none';
  };
  reader.readAsDataURL(file);
}

function removePhoto() {
  euPhotoData   = null;
  euRemovePhoto = true;
  var avImg = el('eu-av-img');
  var avIni = el('eu-av-initials');
  if (avImg) { avImg.src = ''; avImg.style.display = 'none'; }
  if (avIni) avIni.style.display = '';
  var inp = el('eu-photo-input');
  if (inp) inp.value = '';
}

function doEditUser() {
  var errEl = el('eu-err');
  errEl.classList.add('d-none');
  var uid  = el('eu-id').value;
  var data = {
    full_name:   val('eu-name'),
    email:       val('eu-email'),
    department:  val('eu-dept'),
    shift_start: val('eu-start'),
    shift_end:   val('eu-end')
  };
  if (!data.full_name || !data.email) {
    errEl.textContent = 'Full name and email are required';
    errEl.classList.remove('d-none');
    return;
  }
  api('/api/admin/users/' + uid, 'PUT', data).then(function(r) {
    if (!r.ok) {
      errEl.textContent = r.message || 'Update failed';
      errEl.classList.remove('d-none');
      return;
    }
    // Handle photo separately
    if (euPhotoData) {
      api('/api/admin/users/' + uid + '/photo', 'POST', { photo_b64: euPhotoData }).then(function(pr) {
        if (!pr.ok) toast('User updated but photo failed: ' + pr.message, 'info');
        else toast('User updated with photo!', 'success');
        bsEditUserModal.hide();
        loadUsers();
      });
    } else if (euRemovePhoto) {
      api('/api/admin/users/' + uid + '/photo', 'DELETE').then(function() {
        toast('User updated, photo removed.', 'success');
        bsEditUserModal.hide();
        loadUsers();
      });
    } else {
      toast('User updated!', 'success');
      bsEditUserModal.hide();
      loadUsers();
    }
  });
}

// ════ UTILITIES ══════════════════════════════════════

function api(url, method, body) {
  method = method || 'GET'; body = body || null;
  var headers = { 'Content-Type': 'application/json' };
  if (accessToken) headers['Authorization'] = 'Bearer ' + accessToken;
  var opts = { method: method, headers: headers, credentials: 'include' };
  if (body) opts.body = JSON.stringify(body);
  return fetch(url, opts).then(function(resp) {
    var ct = resp.headers.get('content-type') || '';
    if (!ct.includes('application/json')) { console.error('Non-JSON', url, resp.status); return { ok: false, message: 'Server error ' + resp.status }; }
    var status = resp.status;
    return resp.json().then(function(data) {
      if (status === 401 && url !== '/api/auth/login/send-otp' && url !== '/api/auth/login/verify-otp' && url !== '/api/auth/refresh') {
        return fetch('/api/auth/refresh', { method: 'POST', headers: headers, credentials: 'include' }).then(function(rr) {
          if (rr.ok) { return rr.json().then(function(rd) { if (rd.access_token) { accessToken = rd.access_token; opts.headers['Authorization'] = 'Bearer ' + accessToken; } return fetch(url, opts).then(function(r2) { return r2.json(); }); }); }
          else { currentUser = null; accessToken = null; el('login-page').style.display = 'flex'; el('app').style.display = 'none'; showStep('step-login'); return { ok: false, message: 'Session expired' }; }
        });
      }
      return data;
    });
  }).catch(function(e) { console.error('API error:', url, e.message); return { ok: false, message: e.message }; });
}

function el(id)  { return typeof id === 'string' ? document.getElementById(id) : document.querySelector(id); }
function val(id) { var e = el(id); return e ? e.value.trim() : ''; }
function hms(secs) { secs = Math.floor(Math.max(0, secs)); return [Math.floor(secs / 3600), Math.floor(secs % 3600 / 60), secs % 60].map(function(n) { return String(n).padStart(2, '0'); }).join(':'); }
function hrsLabel(s) { return (s / 3600).toFixed(1) + 'h'; }
function emptyCell() { return { v: '', bold: false, italic: false, align: 'left', color: '#e2e8f0', bg: 'transparent' }; }
function emptyRow(cols, msg) { return '<tr><td colspan="' + cols + '" class="text-center text-muted py-4">' + msg + '</td></tr>'; }
function escHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

function populateYears(id) {
  var el2 = el(id); if (!el2 || el2.options.length) return;
  var y = new Date().getFullYear();
  for (var i = y; i >= y - 3; i--) { var o = document.createElement('option'); o.value = i; o.textContent = i; el2.appendChild(o); }
}

function fillEmpSelect(id, addAll) {
  if (addAll === undefined) addAll = true;
  return api('/api/admin/users').then(function(r) {
    var el2 = el(id); if (!r.ok || !el2) return;
    // Always clear and repopulate
    el2.innerHTML = addAll ? '<option value="">All Users</option>' : '<option value="">Select user...</option>';
    // Include employees AND managers (exclude admin only)
    (r.users || []).filter(function(u) {
      return u.role !== 'admin';
    }).forEach(function(u) {
      var o = document.createElement('option');
      o.value = u.id;
      o.textContent = u.full_name + ' (' + u.role + ')';
      el2.appendChild(o);
    });
  });
}

function toast(message, type) {
  type = type || 'info';
  var icons  = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', info: 'bi-info-circle-fill' };
  var colors = { success: 'var(--tt-green)', error: 'var(--tt-red)', info: 'var(--tt-accent)' };
  var id = 'toast-' + Date.now();
  el('toast-container').insertAdjacentHTML('beforeend',
    '<div id="' + id + '" class="toast toast-' + type + ' show" role="alert">' +
    '<div class="toast-body"><i class="bi ' + icons[type] + '" style="color:' + colors[type] + ';font-size:16px;flex-shrink:0"></i>' +
    '<span>' + message + '</span></div></div>');
  setTimeout(function() { var t = document.getElementById(id); if (t) t.remove(); }, 4500);
}

window.addEventListener('load', function() {
  var m = new Date().getMonth() + 1;
  ['h-month', 'at-month'].forEach(function(id) { var e = el(id); if (e) e.value = m; });
});