// Kawaii Night — floating hearts & sparkles
// Respects prefers-reduced-motion: when set, exits immediately (no particles).
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { /* no-op */ }
else (function () {
  'use strict';

  var MAX     = 35;
  var SYMBOLS = ['♥', '✦', '✿', '★', '◆', '✸', '❋', '✾'];
  var COLORS  = ['#f472b6', '#c084fc', '#67e8f9', '#fcd34d', '#fb7185', '#a78bfa', '#f9a8d4'];
  var active  = [];
  var timer;

  /* Inject keyframe once */
  var style = document.createElement('style');
  style.textContent =
    '@keyframes _kw{' +
      '0%  {transform:translateY(0) rotate(0deg)  scale(0.8);opacity:0}' +
      '8%  {opacity:0.55}' +
      '88% {opacity:0.30}' +
      '100%{transform:translateY(-110vh) rotate(420deg) scale(0.6);opacity:0}' +
    '}';
  document.head.appendChild(style);

  /* Particle layer — sits below page content */
  var layer = document.createElement('div');
  layer.style.cssText =
    'position:fixed;inset:0;pointer-events:none;z-index:-1;' +
    'overflow:hidden;contain:strict;';
  document.body.appendChild(layer);

  function spawn() {
    if (active.length >= MAX) return;
    var el   = document.createElement('span');
    var sym  = SYMBOLS[Math.random() * SYMBOLS.length | 0];
    var col  = COLORS [Math.random() * COLORS.length  | 0];
    var size = 10 + Math.random() * 14;          /* 10–24 px */
    var left = 3  + Math.random() * 94;          /* 3–97 % */
    var dur  = 7  + Math.random() * 9;           /* 7–16 s */
    var del  = Math.random() * 1.5;              /* stagger up to 1.5 s */

    el.textContent = sym;
    el.style.cssText =
      'position:absolute;bottom:-28px;left:' + left + '%;' +
      'font-size:' + size + 'px;color:' + col + ';' +
      'opacity:0;will-change:transform,opacity;' +
      'animation:_kw ' + dur + 's ' + del.toFixed(2) + 's ease-in forwards;';

    el.addEventListener('animationend', function () {
      el.remove();
      var i = active.indexOf(el);
      if (i !== -1) active.splice(i, 1);
    }, { once: true });

    layer.appendChild(el);
    active.push(el);
  }

  /* Spawn one right away then every ~1.8 s */
  spawn();
  timer = setInterval(spawn, 1800);

  /* Clean up on navigation (SPA / back-button) */
  window.addEventListener('beforeunload', function () {
    clearInterval(timer);
    active.length = 0;
  });
}());
