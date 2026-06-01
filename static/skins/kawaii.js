// Kawaii Night — ambient rising particle glow
// Respects prefers-reduced-motion: when set, exits immediately (no particles).
if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) (function () {
  'use strict';

  var interval;

  function createParticle() {
    var p = document.createElement('div');
    p.style.cssText =
      'position:fixed;' +
      'width:4px;height:4px;' +
      'background:white;' +
      'border-radius:50%;' +
      'pointer-events:none;' +
      'z-index:40;' +
      'left:' + (Math.random() * window.innerWidth) + 'px;' +
      'top:' + window.innerHeight + 'px;' +
      'opacity:' + (Math.random() * 0.5) + ';' +
      'box-shadow:0 0 8px #ffb0ca;';

    document.body.appendChild(p);

    var duration  = 4000 + Math.random() * 6000;
    var xOffset   = (Math.random() - 0.5) * 100;
    var h         = window.innerHeight;

    var anim = p.animate([
      { transform: 'translateY(0) translateX(0)',                                        opacity: 0 },
      { transform: 'translateY(' + (-h * 0.5) + 'px) translateX(' + xOffset + 'px)',   opacity: 0.6 },
      { transform: 'translateY(' + (-h)        + 'px) translateX(' + (xOffset * 2) + 'px)', opacity: 0 }
    ], { duration: duration, easing: 'linear' });

    anim.onfinish = function () { p.remove(); };
  }

  interval = setInterval(createParticle, 500);

  window.addEventListener('beforeunload', function () {
    clearInterval(interval);
  });
}());
