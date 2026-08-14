/**
 * Smart HR Management System — Main JS
 * Provides: auth guard, API helpers, sidebar, AI chat, flash messages, pagination.
 */

/* ── Auth Guard ───────────────────────────────────────────── */
(function authGuard() {
  const publicPaths = ['/login', '/'];
  const path = window.location.pathname;
  const isPublic = publicPaths.some(p => path === p || path.startsWith('/login'));
  if (isPublic) return;

  const token = localStorage.getItem('access_token');
  if (!token) {
    window.location.href = '/login';
    return;
  }

  // Decode JWT payload (base64) — no verification, just for display
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
  } catch (e) { /* ignore decode errors */ }
})();

/* ── API Helper ───────────────────────────────────────────── */
window.hrAPI = {
  _headers() {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  },

  async _fetch(url, options = {}) {
    try {
      const res = await fetch(url, { headers: this._headers(), ...options });
      // Try to refresh token on 401
      if (res.status === 401) {
        const refreshed = await this._tryRefresh();
        if (refreshed) {
          const retry = await fetch(url, { headers: this._headers(), ...options });
          return retry.json();
        } else {
          localStorage.clear();
          window.location.href = '/login';
          return { success: false, message: 'Session expired.' };
        }
      }
      return res.json();
    } catch (err) {
      console.error('API error:', err);
      return { success: false, message: 'Network error. Please try again.' };
    }
  },

  async _tryRefresh() {
    const refresh_token = localStorage.getItem('refresh_token');
    if (!refresh_token) return false;
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${refresh_token}`,
        },
      });
      const data = await res.json();
      if (data.success && data.data.access_token) {
        localStorage.setItem('access_token', data.data.access_token);
        return true;
      }
    } catch (e) { /* ignore */ }
    return false;
  },

  get(url)          { return this._fetch(url); },
  post(url, body)   { return this._fetch(url, { method: 'POST',   body: JSON.stringify(body) }); },
  put(url, body)    { return this._fetch(url, { method: 'PUT',    body: JSON.stringify(body) }); },
  del(url)          { return this._fetch(url, { method: 'DELETE' }); },
};

/* ── Flash Messages ───────────────────────────────────────── */
window.showFlash = function(message, type = 'info') {
  const container = document.getElementById('flashContainer');
  if (!container) return;

  const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' };
  const el = document.createElement('div');
  el.className = `flash flash-${type === 'error' ? 'error' : type}`;
  el.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i> ${message}`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
};

/* ── Pagination Helper ────────────────────────────────────── */
window.renderPagination = function(containerId, pagination, onPageChange) {
  const container = document.getElementById(containerId);
  if (!container || !pagination) return;

  const { page, total_pages } = pagination;
  if (total_pages <= 1) { container.innerHTML = ''; return; }

  let html = '';
  html += `<button class="page-btn" ${page <= 1 ? 'disabled' : ''} onclick="(${onPageChange})(${page - 1})">
    <i class="fa-solid fa-chevron-left"></i>
  </button>`;

  const start = Math.max(1, page - 2);
  const end   = Math.min(total_pages, page + 2);

  if (start > 1) html += `<button class="page-btn" onclick="(${onPageChange})(1)">1</button>`;
  if (start > 2) html += `<span style="padding:.3rem .4rem;color:var(--text-muted)">…</span>`;

  for (let i = start; i <= end; i++) {
    html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="(${onPageChange})(${i})">${i}</button>`;
  }

  if (end < total_pages - 1) html += `<span style="padding:.3rem .4rem;color:var(--text-muted)">…</span>`;
  if (end < total_pages) html += `<button class="page-btn" onclick="(${onPageChange})(${total_pages})">${total_pages}</button>`;

  html += `<button class="page-btn" ${page >= total_pages ? 'disabled' : ''} onclick="(${onPageChange})(${page + 1})">
    <i class="fa-solid fa-chevron-right"></i>
  </button>`;

  html += `<span style="font-size:.78rem;color:var(--text-muted);margin-left:.5rem">
    Page ${page} of ${total_pages} (${pagination.total} total)
  </span>`;

  container.innerHTML = html;
};

/* ── Topbar — user info ───────────────────────────────────── */
(function setUserInfo() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const nameEl   = document.getElementById('userName');
  const roleEl   = document.getElementById('userRole');
  const avatarEl = document.getElementById('userAvatar');

  if (nameEl)   nameEl.textContent   = user.username || 'User';
  if (roleEl)   roleEl.textContent   = (user.role || '').replace('_', ' ');
  if (avatarEl) avatarEl.textContent = (user.username || 'U')[0].toUpperCase();

  // Role-based badge color
  const roleColors = { admin: 'danger', hr_manager: 'warning', manager: 'info', employee: 'success' };
  if (roleEl) {
    roleEl.classList.remove('badge-success','badge-warning','badge-danger','badge-info','badge-secondary');
    roleEl.classList.add(`badge-${roleColors[user.role] || 'secondary'}`);
    roleEl.classList.add('badge');
  }
})();

/* ── Sidebar Toggle (mobile) ──────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const toggle  = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const layout  = document.getElementById('appLayout');

  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    // Close on outside click
    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) &&
          !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // Highlight active nav item
  const current = window.location.pathname.split('/')[1] || 'dashboard';
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.dataset.page === current) item.classList.add('active');
  });

  // Logout
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    });
  }
});

/* ── AI Chat Drawer ───────────────────────────────────────── */
(function initAIChat() {
  const openBtn  = document.getElementById('openAiChat');
  const closeBtn = document.getElementById('closeAiChat');
  const drawer   = document.getElementById('aiDrawer');
  const overlay  = document.getElementById('aiOverlay');
  const input    = document.getElementById('aiInput');
  const sendBtn  = document.getElementById('aiSend');
  const messages = document.getElementById('aiMessages');

  if (!drawer) return;

  let chatHistory = [];

  function openDrawer() {
    drawer.classList.add('open');
    overlay.style.display = 'block';
    if (input) input.focus();
  }
  function closeDrawer() {
    drawer.classList.remove('open');
    overlay.style.display = 'none';
  }

  if (openBtn)  openBtn.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (overlay)  overlay.addEventListener('click', closeDrawer);

  function appendMessage(text, role) {
    const msg = document.createElement('div');
    msg.className = `ai-msg ${role}`;
    msg.innerHTML = role === 'user'
      ? `<i class="fa-solid fa-user"></i><div class="bubble">${text}</div>`
      : `<i class="fa-solid fa-robot"></i><div class="bubble">${text}</div>`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    appendMessage(text, 'user');
    chatHistory.push({ role: 'user', content: text });

    // Typing indicator
    const typing = document.createElement('div');
    typing.className = 'ai-msg bot';
    typing.innerHTML = '<i class="fa-solid fa-robot"></i><div class="bubble"><i class="fa-solid fa-spinner fa-spin"></i></div>';
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;

    const res = await window.hrAPI.post('/api/ai/chat', {
      message: text,
      history: chatHistory.slice(-10),
    });

    typing.remove();

    const reply = res.success ? res.data.reply : "Sorry, I'm having trouble right now. Please try again.";
    appendMessage(reply, 'bot');
    chatHistory.push({ role: 'assistant', content: reply });
  }

  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
  }
})();


/* ── Notification Bell ────────────────────────────────────── */
(function initNotifications() {
  const bell     = document.getElementById('notifBell');
  const badge    = document.getElementById('notifBadge');
  const list     = document.getElementById('notifList');
  const markAll  = document.getElementById('markAllRead');
  if (!bell) return;

  async function fetchCount() {
    const r = await window.hrAPI.get('/api/notifications/unread-count');
    if (!r.success) return;
    const count = r.data.unread_count;
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : count;
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  }

  async function fetchNotifications() {
    const r = await window.hrAPI.get('/api/notifications?limit=15');
    if (!r.success) return;
    const notifs = r.data.notifications;
    if (!notifs.length) {
      list.innerHTML = '<p class="empty-state">No notifications.</p>';
      return;
    }
    const timeAgo = (iso) => {
      const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
      if (diff < 60) return `${diff}s ago`;
      if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
      return `${Math.floor(diff/86400)}d ago`;
    };
    list.innerHTML = notifs.map(n => `
      <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markNotifRead('${n.id}', this, '${n.link||''}')">
        <div class="notif-item-title">${n.title}</div>
        <div class="notif-item-msg">${n.message}</div>
        <div class="notif-item-time">${n.created_at ? timeAgo(n.created_at) : ''}</div>
      </div>
    `).join('');
  }

  bell.addEventListener('click', (e) => {
    e.stopPropagation();
    bell.classList.toggle('open');
    if (bell.classList.contains('open')) fetchNotifications();
  });

  document.addEventListener('click', (e) => {
    if (!bell.contains(e.target)) bell.classList.remove('open');
  });

  if (markAll) {
    markAll.addEventListener('click', async (e) => {
      e.stopPropagation();
      await window.hrAPI.put('/api/notifications/read-all', {});
      badge.style.display = 'none';
      fetchNotifications();
    });
  }

  // Expose globally for inline onclick
  window.markNotifRead = async (id, el, link) => {
    await window.hrAPI.put(`/api/notifications/${id}/read`, {});
    el.classList.remove('unread');
    fetchCount();
    if (link) window.location.href = link;
  };

  // Poll every 30s
  fetchCount();
  setInterval(fetchCount, 30000);
})();
