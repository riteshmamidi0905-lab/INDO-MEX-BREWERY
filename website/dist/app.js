/* NASHA site script. Optional enhancement only: the site works without it. */
(function () {
  "use strict";
  var root = document.documentElement;
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
      var checks = fs.querySelectorAll("input:checked");
      var rules = {};
      checks.forEach(function (c) { (rules[c.name] = rules[c.name] || []).push(c.value); });
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
})();
