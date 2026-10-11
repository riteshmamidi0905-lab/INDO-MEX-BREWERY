/* NASHA site script. Optional enhancement only: the site works without it. */
(function () {
  "use strict";
  var root = document.documentElement;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  try { var t = localStorage.getItem("nasha-theme"); if (t) root.setAttribute("data-theme", t); } catch (e) {}
  var tb = document.getElementById("theme-toggle");
  if (tb) {
    tb.addEventListener("click", function () {
      var dark = getComputedStyle(root).getPropertyValue("--bg").trim().toLowerCase() === "#141110";
      var next = dark ? "light" : "dark";
      root.setAttribute("data-theme", next);
      tb.setAttribute("aria-pressed", String(next === "dark"));
      try { localStorage.setItem("nasha-theme", next); } catch (e) {}
    });
  }
  document.querySelectorAll("[data-filter-group]").forEach(function (fs) {
    var target = document.getElementById(fs.getAttribute("data-filter-group"));
    var status = document.getElementById(fs.getAttribute("data-status"));
    function apply() {
      var rules = {};
      fs.querySelectorAll("input:checked").forEach(function (c) { (rules[c.name] = rules[c.name] || []).push(c.value); });
      var shown = 0;
      target.querySelectorAll("[data-item]").forEach(function (el) {
        var ok = Object.keys(rules).every(function (k) {
          var v = el.getAttribute("data-" + k) || "";
          return rules[k].some(function (r) { return v.split("|").indexOf(r) > -1; });
        });
        el.hidden = !ok;
        if (ok) shown++;
      });
      if (status) status.textContent = shown + (shown === 1 ? " item shown" : " items shown");
    }
    fs.addEventListener("change", apply);
    var reset = fs.querySelector("[data-reset]");
    if (reset) reset.addEventListener("click", function () {
      fs.querySelectorAll("input").forEach(function (c) { c.checked = false; });
      apply();
    });
  });
  // Reveal on scroll: motion marks arrival, never hides content from reduced-motion users.
  var rev = document.querySelectorAll(".reveal");
  if (rev.length) {
    if (reduce || !("IntersectionObserver" in window)) { rev.forEach(function (e) { e.classList.add("in"); }); }
    else {
      var io = new IntersectionObserver(function (es) { es.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } }); }, { rootMargin: "0px 0px -8% 0px" });
      rev.forEach(function (e) { io.observe(e); });
      var tick = false;
      function sweep() { tick = false; rev.forEach(function (e) { if (!e.classList.contains("in") && e.getBoundingClientRect().top < window.innerHeight * 0.92) e.classList.add("in"); }); }
      window.addEventListener("scroll", function () { if (!tick) { tick = true; requestAnimationFrame(sweep); } }, { passive: true });
      window.addEventListener("resize", sweep); sweep();
      setTimeout(function () { rev.forEach(function (e) { e.classList.add("in"); }); }, 8000);
    }
  }
  // Beer colour preview on the Beer page (illustrative colours).
  var COL = { "hefeweizen": ["#F0C25A", "#FBF6EA"], "mexican-lager": ["#F6D56B", "#FFFDF4"], "vienna-amber": ["#C4691A", "#F2E6D0"] };
  var macro = document.querySelector("[data-macro]");
  if (macro) {
    document.querySelectorAll(".swatch").forEach(function (b) {
      b.addEventListener("click", function () {
        var c = COL[b.getAttribute("data-beer")]; if (!c) return;
        macro.querySelectorAll(".liq").forEach(function (e) { e.setAttribute("fill", c[0]); e.style.fill = c[0]; });
        macro.querySelectorAll(".foam").forEach(function (e) { e.setAttribute("fill", c[1]); e.style.fill = c[1]; });
        document.querySelectorAll(".swatch").forEach(function (s) { s.setAttribute("aria-pressed", String(s === b)); });
      });
    });
  }
  // Two-Pour walkthrough.
  document.querySelectorAll("[data-two-pour]").forEach(function (tp) {
    var st = tp.querySelector("[data-tp-status]");
    var names = ["Beer one", "The dish", "Beer two"];
    function go(n) { n = Math.max(1, Math.min(3, n)); tp.setAttribute("data-active", String(n)); if (st) st.textContent = "Step " + n + " of 3: " + names[n - 1]; }
    tp.querySelectorAll("[data-tp]").forEach(function (b) {
      b.addEventListener("click", function () { var n = +tp.getAttribute("data-active"); go(b.getAttribute("data-tp") === "next" ? (n === 3 ? 1 : n + 1) : n - 1); });
    });
  });
})();
