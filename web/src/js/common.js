// Shared page behavior: appearance, navigation menu, themed images, lightbox, contents.
(function () {
  const root = document.documentElement;
  const KEY = 'fringescope-theme';
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function save(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode */ } }

  function applyImages(theme) {
    document.querySelectorAll('img[data-light-src][data-dark-src]').forEach(img => {
      const src = theme === 'light' ? img.dataset.lightSrc : img.dataset.darkSrc;
      if (img.getAttribute('src') !== src) img.setAttribute('src', src);
      const link = img.closest('a[data-light-href]');
      if (link) link.href = theme === 'light' ? link.dataset.lightHref : link.dataset.darkHref;
    });
  }
  function setTheme(theme, persist) {
    root.dataset.theme = theme;
    if (persist) save(theme);
    applyImages(theme);
    const button = document.getElementById('theme-button');
    if (button) {
      button.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      button.title = button.getAttribute('aria-label');
      button.innerHTML = theme === 'dark'
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>';
    }
    document.dispatchEvent(new CustomEvent('fringescope-theme', { detail: theme }));
  }
  window.FringeScopeTheme = { get: () => root.dataset.theme || 'dark', set: setTheme };

  document.addEventListener('DOMContentLoaded', () => {
    setTheme(stored() || root.dataset.theme || 'dark', false);
    const themeButton = document.getElementById('theme-button');
    if (themeButton) themeButton.addEventListener('click', () => setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark', true));

    const menu = document.getElementById('menu-button'), nav = document.getElementById('site-nav');
    if (menu && nav) {
      menu.addEventListener('click', () => {
        const open = nav.classList.toggle('open');
        menu.setAttribute('aria-expanded', String(open));
      });
      nav.addEventListener('click', e => { if (e.target.closest('a')) { nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); } });
    }

    // Lightbox: full-resolution figure with native pinch zoom and scrolling.
    const box = document.getElementById('lightbox');
    if (box) {
      const img = box.querySelector('img'), title = box.querySelector('.lb-title'), scroll = box.querySelector('.lb-scroll');
      const fit = box.querySelector('[data-action="fit"]');
      let opener = null;
      function close() { box.hidden = true; document.body.style.overflow = ''; if (opener) opener.focus(); }
      document.addEventListener('click', e => {
        const target = e.target.closest('[data-zoom]');
        if (!target) return;
        e.preventDefault(); opener = target;
        const source = target.tagName === 'IMG' ? target : target.querySelector('img');
        img.src = source.currentSrc || source.src; img.alt = source.alt;
        title.textContent = target.dataset.zoom || source.alt;
        scroll.classList.remove('fit'); fit.textContent = 'Fit to screen';
        box.hidden = false; document.body.style.overflow = 'hidden';
        box.querySelector('[data-action="close"]').focus();
      });
      box.addEventListener('click', e => {
        const action = e.target.closest('[data-action]');
        if (!action) return;
        if (action.dataset.action === 'close') close();
        if (action.dataset.action === 'fit') { const on = scroll.classList.toggle('fit'); fit.textContent = on ? 'Actual size' : 'Fit to screen'; }
      });
      document.addEventListener('keydown', e => { if (e.key === 'Escape' && !box.hidden) close(); });
    }

    // Contents highlighting for article pages.
    const links = [...document.querySelectorAll('.toc a[href^="#"]')];
    if (links.length && 'IntersectionObserver' in window) {
      const map = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
      const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          links.forEach(a => a.classList.remove('active'));
          const a = map.get(entry.target.id); if (a) a.classList.add('active');
        });
      }, { rootMargin: '-80px 0px -70% 0px' });
      map.forEach((a, id) => { const h = document.getElementById(id); if (h) observer.observe(h); });
    }
    document.querySelectorAll('.toc-mobile a').forEach(a => a.addEventListener('click', () => { const d = a.closest('details'); if (d) d.open = false; }));
  });
})();
