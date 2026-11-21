/* layoutChecks — in-page layout checks for responsive design
 * Evaluated per page per width. Returns array of {check, selector, width, detail}.
 * Checks: page-overflow, clipped, collision, crushed, ellipsis.
 * Opt-outs: data-layout-scroll-ok (intended scrollers), data-layout-overlay-ok (overlays).
 *
 * Revision (round 3, issue #774): crushed uses getClientRects() fragment count instead of
 * height/lineHeight to avoid false positives on flex-stretched elements; collision skips
 * parent-child containment pairs only (a.contains(b) or b.contains(a)) — the blanket
 * same-parent sibling skip was removed per review #780 (round 10).
 *
 * Revision (round 11, issue #774): collision compares getClientRects() fragment pairs instead
 * of a single getBoundingClientRect() union. A multi-line inline element's bounding-box union
 * spans back to the line start, so it spuriously "overlaps" a preceding sibling that sits only
 * on line 1 (e.g. <strong>Question:</strong> <em>text that wraps to another line</em>) even
 * though no rendered line actually touches — same false-positive class round 3 already fixed
 * for crushed. Fragment comparison catches real same-line/adjacent overlaps unchanged.
 *
 * Revision (round 16, issue #774): crushed filters zero-area getClientRects() fragments before
 * counting them, matching the filter collision already applies (line 71) for the same wrap-
 * boundary artifact — an unfiltered stray fragment was inflating the line count by one.
 *
 * Revision (2026-10-12, live-site read): a flex item is blockified and reports a single client
 * rect however many lines it wraps to, so the freshness pill's date (`.pill .mono`, a flex item)
 * broke as "05.10.202 / 6" at 1280 px on connect.html with 0 findings. Leaf elements now count
 * lines from a Range over their text.
 */
/* circles port (2026-11-21) of oracle-fleet scripts/e2e/layout_checks.js @ 58b87e8 — two local
 * changes, both marked `circles:` below: (1) the overlay opt-out covers an element's whole subtree
 * (`closest`), so one attribute on the sunburst <svg> exempts every cell — annular sectors'
 * boxes overlap by construction, and the chart's own legibility rules live in
 * specs/render/sunburst.md; (2) content inside a CLOSED <details> is not rendered and is skipped
 * (Chromium still lays it out under content-visibility, so its boxes "collide" with the summary).
 */
(function() {
  var F = [], iw = window.innerWidth, all = document.querySelectorAll('*');
  var lc = null;
  // circles: inside a closed <details>, but not its <summary>
  function unrendered(e) { var d = e.closest('details:not([open])'); return !!d && !e.closest('summary'); }
  function layoutCtx() { return lc || (lc = document.createElement('canvas').getContext('2d')); }
  function sel(e) {
    if (!e || e === document) return 'document';
    var s = e.id ? '#' + e.id : e.tagName.toLowerCase();
    if (e.className && typeof e.className === 'string') {
      var c = e.className.trim().split(/\s+/).filter(function(x){return x});
      if (c.length) s += '.' + c.join('.');
    }
    return s;
  }
  // 1. page-overflow — runs at every width AND the 200 % zoom test (WCAG 1.4.10 reflow)
  {
    var se = document.scrollingElement;
    if (se.scrollWidth > iw + 1) {
      var w = [];
      for (var i = 0; i < all.length; i++) try {
        var r = all[i].getBoundingClientRect();
        if (r.right > iw + 1 && r.width > 0) w.push({s:sel(all[i]), r:Math.round(r.right)});
      } catch(e){}
      w.sort(function(a,b){return b.r-a.r});
      F.push({check:'page-overflow',selector:'document',width:iw,detail:JSON.stringify(w.slice(0,5))});
    }
  }
  // 2. clipped — no tag skips: intended scrollers/clippers carry data-layout-scroll-ok (presence,
  // via hasAttribute — a bare attribute's value is "" and getAttribute() would read it as falsy)
  for (var i = 0; i < all.length; i++) try {
    var el = all[i];
    var cs = window.getComputedStyle(el);
    var ox = cs.overflowX, oy = cs.overflowY, o = cs.overflow;
    if ((ox==='hidden'||ox==='clip'||ox==='auto'||ox==='scroll'||oy==='hidden'||oy==='clip'||oy==='auto'||oy==='scroll'||o==='hidden'||o==='clip'||o==='auto'||o==='scroll') && (el.scrollWidth>el.clientWidth+1||el.scrollHeight>el.clientHeight+1)) {
      if (!el.hasAttribute('data-layout-scroll-ok')) F.push({check:'clipped',selector:sel(el),width:iw,detail:'s='+el.scrollWidth+'x'+el.scrollHeight+' c='+el.clientWidth+'x'+el.clientHeight});
    }
  } catch(e){}
  // 3. collision — skip parent-child containment pairs only (same-parent sibling collision
  // detection is essential for catching real regressions; use data-layout-overlay-ok for
  // intentionally overlapping elements)
  for (var i = 0; i < all.length; i++) for (var j = i+1; j < all.length; j++) try {
    var a = all[i], b = all[j];
    // circles: the opt-out covers the subtree; closed-<details> content is not rendered
    if (a.closest('[data-layout-overlay-ok]')||b.closest('[data-layout-overlay-ok]')) continue;
    if (unrendered(a)||unrendered(b)) continue;
    // Skip if one element contains the other (parent-child overlap is not a layout collision)
    if (a.contains(b) || b.contains(a)) continue;
    // NOTE: blanket same-parent skip removed per review #780 — sibling collision detection
    // is essential for catching real regressions (nav links, badges, etc.). If a specific
    // element pair genuinely overlaps by design, mark the overlay element with
    // data-layout-overlay-ok instead.
    var isIntA = /^(a|button|input)$/i.test(a.tagName)||a.getAttribute('role')==='button';
    var isIntB = /^(a|button|input)$/i.test(b.tagName)||b.getAttribute('role')==='button';
    var isTextA = a.querySelectorAll(':scope > *').length===0 && (a.textContent||'').trim().length>0;
    var isTextB = b.querySelectorAll(':scope > *').length===0 && (b.textContent||'').trim().length>0;
    if (!(isIntA||isTextA)||!(isIntB||isTextB)) continue;
    // Fragment-level overlap: only a real touching pair of rendered line boxes counts.
    var fa = a.getClientRects(), fb = b.getClientRects(), hit = null;
    for (var x = 0; x < fa.length && !hit; x++) for (var y = 0; y < fb.length; y++) {
      var fra = fa[x], frb = fb[y];
      if (!(fra.width>0&&fra.height>0&&frb.width>0&&frb.height>0)) continue;
      var ox2 = Math.max(0,Math.min(fra.right,frb.right)-Math.max(fra.left,frb.left));
      var oy2 = Math.max(0,Math.min(fra.bottom,frb.bottom)-Math.max(fra.top,frb.top));
      if (ox2>1&&oy2>1) { hit = {ox:Math.round(ox2),oy:Math.round(oy2)}; break; }
    }
    if (hit) F.push({check:'collision',selector:sel(a)+' vs '+sel(b),width:iw,detail:'overlap '+hit.ox+'x'+hit.oy+'px'});
  } catch(e){}
  // 4. crushed — an element renders more line fragments (getClientRects(), zero-area dropped) than
  // it has break-opportunity segments (split on whitespace, '/', '-'), i.e. a token broke mid-token.
  // No tag skips (code/pre included): a token wider than its container is exempt by measurement.
  for (var i = 0; i < all.length; i++) try {
    var el = all[i];
    var rawRects = el.getClientRects(), rects = [];
    for (var k = 0; k < rawRects.length; k++) if (rawRects[k].width > 0 && rawRects[k].height > 0) rects.push(rawRects[k]);
    var lines = rects.length;
    // A block-level box (a block, or any flex/grid item — blockified) reports ONE client rect
    // however many lines it wraps to, so a leaf element's lines are counted from its text's own
    // line boxes: the distinct tops of a Range over its contents.
    if (lines === 1 && el.childElementCount === 0) {
      var rg = document.createRange(); rg.selectNodeContents(el);
      var tr = rg.getClientRects(), tops = {};
      for (var k = 0; k < tr.length; k++) if (tr[k].width > 0 && tr[k].height > 0) tops[Math.round(tr[k].top)] = 1;
      lines = Math.max(lines, Object.keys(tops).length);
    }
    if (lines <= 1) continue;
    var segs = (el.textContent||'').trim().split(/[\s\/-]+/).filter(function(w){return w}), words = segs.length;
    if (!(words > 0 && lines > words)) continue;
    // A segment wider than its container's content box MUST break (WCAG reflow), so that break
    // is not a crush. Measured with the element's own font; only such over-wide tokens are exempt.
    var pe = el.parentElement, pcs = window.getComputedStyle(pe);
    var room = pe.clientWidth - parseFloat(pcs.paddingLeft) - parseFloat(pcs.paddingRight);
    var ctx = layoutCtx(), widest = 0;
    var ecs = window.getComputedStyle(el);
    // longhands, not ecs.font: Chromium serialises the shorthand as '' for many elements
    ctx.font = ecs.fontStyle + ' ' + ecs.fontWeight + ' ' + ecs.fontSize + ' ' + ecs.fontFamily;
    // measure what renders: text-transform and letter-spacing (an uppercase, tracked eyebrow is
    // wider than its source text, so a must-break label measured bare read as a crush)
    ctx.letterSpacing = ecs.letterSpacing === 'normal' ? '0px' : ecs.letterSpacing;
    var tt = ecs.textTransform;
    for (var k = 0; k < segs.length; k++) {
      var sg = tt === 'uppercase' ? segs[k].toUpperCase() : tt === 'lowercase' ? segs[k].toLowerCase() : segs[k];
      widest = Math.max(widest, ctx.measureText(sg).width);
    }
    widest += parseFloat(ecs.paddingLeft) + parseFloat(ecs.paddingRight) + parseFloat(ecs.borderLeftWidth) + parseFloat(ecs.borderRightWidth);
    if (widest <= room) F.push({check:'crushed',selector:sel(el),width:iw,detail:lines+' lines for '+words+' words'});
  } catch(e){}
  // 5. ellipsis
  for (var i = 0; i < all.length; i++) try {
    var el = all[i], cs = window.getComputedStyle(el);
    if (cs.textOverflow==='ellipsis' && el.scrollWidth>el.clientWidth && !el.hasAttribute('data-layout-scroll-ok')) {
      F.push({check:'ellipsis',selector:sel(el),width:iw,detail:'sW='+el.scrollWidth+' > cW='+el.clientWidth});
    }
  } catch(e){}
  return F;
})()
