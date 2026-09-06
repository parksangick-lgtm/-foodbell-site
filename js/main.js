/* =========================================================
   푸드벨 (FoodBell) 메인 스크립트
   - 모바일 내비게이션 토글
   - 메뉴 카테고리 탭 전환
   - 맨 위로 버튼 표시/스크롤
   - 문의 폼 보내기 (넷리파이 폼)
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

  /* ---------- 카테고리별 사진 앨범 접기/펼치기 (기본: 펼침) ---------- */
  document.querySelectorAll('.album-toggle').forEach(function (btn) {
    var album = document.getElementById(btn.getAttribute('data-album'));
    if (!album) return;
    var label = btn.querySelector('.album-toggle__label');
    var baseLabel = label ? label.textContent : '';

    var sync = function () {
      var open = !album.hidden;
      btn.setAttribute('aria-expanded', String(open));
      btn.classList.toggle('is-open', open);
      if (label) label.textContent = open ? baseLabel + ' 접기' : baseLabel + ' 펼치기';
    };
    sync();

    btn.addEventListener('click', function () {
      album.hidden = !album.hidden;
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

  /* ---------- 문의 폼 보내기 ----------
     넷리파이(Netlify) 폼 기능을 씁니다. 페이지를 새로 열지 않고 보내기 위해
     fetch 로 넘기고, 결과는 버튼 아래 한 줄로 알려줍니다.
     ※ 내 컴퓨터 미리보기(localhost)에서는 전송이 안 됩니다. 넷리파이에 올라가야 작동합니다. */
  var contactForm = document.getElementById('contactForm');
  var formNote = document.getElementById('formNote');

  if (contactForm && formNote) {
    var isLocal = ['localhost', '127.0.0.1', ''].indexOf(window.location.hostname) !== -1;

    var setNote = function (text, kind) {
      formNote.className = 'contact__form-note' + (kind ? ' is-' + kind : '');
      formNote.textContent = text;
    };

    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();

      var submitBtn = contactForm.querySelector('button[type="submit"]');

      if (isLocal) {
        setNote('미리보기에서는 전송되지 않습니다. 인터넷에 올린 주소에서 시험해보세요.', 'error');
        return;
      }

      submitBtn.disabled = true;
      setNote('보내는 중...');

      fetch('/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(new FormData(contactForm)).toString()
      })
        .then(function (res) {
          if (!res.ok) throw new Error(String(res.status));
          contactForm.reset();
          setNote('문의가 접수되었습니다. 확인하는 대로 연락드리겠습니다.', 'ok');
        })
        .catch(function () {
          setNote('전송에 실패했습니다. 010-5353-3477 로 전화 주시면 바로 도와드리겠습니다.', 'error');
        })
        .then(function () {
          submitBtn.disabled = false;
        });
    });
  }
})();
