/* =========================================================
   푸드벨 (FoodBell) 메인 스크립트
   - 모바일 내비게이션 토글
   - 메뉴 카테고리 탭 전환
   - 맨 위로 버튼 표시/스크롤
   - 사진 클릭 시 크게 보기 (서비스 카드 · 앨범 · 갤러리 공용 라이트박스)
========================================================= */
(function () {
  'use strict';

  /* ---------- 모바일 내비게이션 ---------- */
  var navToggle = document.getElementById('navToggle');
  var nav = document.getElementById('nav');

  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      var isOpen = nav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', String(isOpen));
    });

    nav.querySelectorAll('.nav__link').forEach(function (link) {
      link.addEventListener('click', function () {
        nav.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------- 메뉴 카테고리 탭 ---------- */
  var tabs = document.querySelectorAll('.menu__tab');
  var panels = document.querySelectorAll('.menu__panel');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var targetId = tab.getAttribute('data-target');

      tabs.forEach(function (t) {
        t.classList.remove('is-active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('is-active');
      tab.setAttribute('aria-selected', 'true');

      panels.forEach(function (panel) {
        var isTarget = panel.id === targetId;
        panel.classList.toggle('is-active', isTarget);
        panel.hidden = !isTarget;
      });
    });
  });

  /* ---------- 맨 위로 버튼 ---------- */
  var toTop = document.getElementById('toTop');
  if (toTop) {
    var toggleToTop = function () {
      toTop.classList.toggle('is-visible', window.scrollY > 480);
    };
    window.addEventListener('scroll', toggleToTop, { passive: true });
    toggleToTop();
  }

  /* ---------- 카테고리별 사진 앨범 — 처음 8장만 보이고 나머지는 "더 보기" ---------- */
  document.querySelectorAll('.album-toggle').forEach(function (btn) {
    var album = document.getElementById(btn.getAttribute('data-album'));
    if (!album) return;
    var label = btn.querySelector('.album-toggle__label');
    var total = album.querySelectorAll('.album__item').length;

    var sync = function () {
      var collapsed = album.classList.contains('is-collapsed');
      btn.setAttribute('aria-expanded', String(!collapsed));
      btn.classList.toggle('is-open', !collapsed);
      if (label) label.textContent = collapsed ? '사진 더 보기 (' + total + '장)' : '사진 접기';
    };
    sync();

    btn.addEventListener('click', function () {
      album.classList.toggle('is-collapsed');
      sync();
    });
  });

  /* ---------- 라이트박스 (갤러리 · 앨범 공용, 이전/다음 이동) ---------- */
  var lightbox = document.getElementById('lightbox');
  var lightboxImg = document.getElementById('lightboxImg');
  var lightboxClose = document.getElementById('lightboxClose');
  var lightboxPrev = document.getElementById('lightboxPrev');
  var lightboxNext = document.getElementById('lightboxNext');
  var lightboxCount = document.getElementById('lightboxCount');

  var group = [];
  var groupIndex = 0;

  function renderLightbox() {
    var item = group[groupIndex];
    if (!item) return;
    lightboxImg.src = item.src;
    lightboxImg.alt = item.alt || '';
    var many = group.length > 1;
    if (lightboxCount) lightboxCount.textContent = many ? (groupIndex + 1) + ' / ' + group.length : '';
    if (lightboxPrev) lightboxPrev.hidden = !many;
    if (lightboxNext) lightboxNext.hidden = !many;
  }

  function openLightbox(items, start) {
    if (!lightbox || !lightboxImg || !items.length) return;
    group = items;
    groupIndex = start || 0;
    renderLightbox();
    lightbox.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.hidden = true;
    lightboxImg.src = '';
    group = [];
    document.body.style.overflow = '';
  }

  function step(delta) {
    if (group.length < 2) return;
    groupIndex = (groupIndex + delta + group.length) % group.length;
    renderLightbox();
  }

  function wireGroup(container, itemSelector, srcAttr) {
    var nodes = Array.prototype.slice.call(container.querySelectorAll(itemSelector));
    var items = nodes.map(function (n) {
      var img = n.querySelector('img');
      return { src: n.getAttribute(srcAttr), alt: img ? img.alt : '' };
    });
    nodes.forEach(function (n, i) {
      n.addEventListener('click', function () { openLightbox(items, i); });
    });
  }

  var galleryGrid = document.querySelector('.gallery__grid');
  if (galleryGrid) wireGroup(galleryGrid, '.gallery__item', 'data-full');
  document.querySelectorAll('.album').forEach(function (album) {
    wireGroup(album, '.album__item', 'data-src');
  });
  document.querySelectorAll('.menu__grid').forEach(function (grid) {
    wireGroup(grid, '.menu-card__thumb', 'data-full');
  });

  if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);
  if (lightboxPrev) lightboxPrev.addEventListener('click', function () { step(-1); });
  if (lightboxNext) lightboxNext.addEventListener('click', function () { step(1); });
  if (lightbox) {
    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox || e.target === lightboxImg.parentNode) closeLightbox();
    });
  }
  document.addEventListener('keydown', function (e) {
    if (!lightbox || lightbox.hidden) return;
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowLeft') step(-1);
    else if (e.key === 'ArrowRight') step(1);
  });

  /* ---------- 컴퓨터에서 "전화로 문의하기" → 번호 복사 ---------- */
  // 컴퓨터(마우스)는 전화를 걸 수 없으니 번호를 복사해 준다. 휴대폰은 그대로 전화가 걸린다.
  var callBtn = document.querySelector('.contact__cta-btn');
  if (callBtn && window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    var toast = document.createElement('div');
    toast.className = 'copy-toast';
    toast.setAttribute('role', 'status');
    document.body.appendChild(toast);
    var toastTimer;

    var showToast = function (msg) {
      toast.textContent = msg;
      toast.classList.add('is-show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(function () { toast.classList.remove('is-show'); }, 2500);
    };

    callBtn.addEventListener('click', function (e) {
      e.preventDefault();
      var number = callBtn.getAttribute('href').replace('tel:', '');
      var done = function () { showToast('전화번호가 복사되었습니다 (' + number + ')'); };
      var fallback = function () {
        var box = document.createElement('textarea');
        box.value = number;
        document.body.appendChild(box);
        box.select();
        document.execCommand('copy');
        document.body.removeChild(box);
        done();
      };
      if (navigator.clipboard) navigator.clipboard.writeText(number).then(done, fallback);
      else fallback();
    });
  }

  /* ---------- 헤더 스크롤 그림자(선택적 시각 효과) ---------- */
  var header = document.getElementById('header');
  if (header) {
    var toggleHeaderShadow = function () {
      header.style.boxShadow = window.scrollY > 8
        ? '0 6px 20px -14px rgba(43,33,24,0.35)'
        : 'none';
    };
    window.addEventListener('scroll', toggleHeaderShadow, { passive: true });
    toggleHeaderShadow();
  }

})();
