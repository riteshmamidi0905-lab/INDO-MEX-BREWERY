(function(){
  var d=document,b=d.body;b.classList.add("js");d.documentElement.classList.add("js");
  var hd=d.querySelector(".hd"),btn=d.querySelector(".menu"),nav=d.querySelector(".nav");
  function onScroll(){if(hd)hd.classList.toggle("solid",window.scrollY>40)}
  onScroll();window.addEventListener("scroll",onScroll,{passive:true});
  if(btn&&nav){btn.setAttribute("aria-expanded","false");
    btn.addEventListener("click",function(){var o=nav.classList.toggle("open");btn.setAttribute("aria-expanded",o?"true":"false");btn.textContent=o?"Close":"Menu"});
    nav.addEventListener("click",function(e){if(e.target.tagName==="A"){nav.classList.remove("open");btn.setAttribute("aria-expanded","false");btn.textContent="Menu"}});
    d.addEventListener("keydown",function(e){if(e.key==="Escape"&&nav.classList.contains("open")){nav.classList.remove("open");btn.setAttribute("aria-expanded","false");btn.textContent="Menu";btn.focus()}})}
  var els=[].slice.call(d.querySelectorAll(".rv"));
  if(!("IntersectionObserver" in window)||window.matchMedia("(prefers-reduced-motion: reduce)").matches){els.forEach(function(e){e.classList.add("in")});return}
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target)}})},{rootMargin:"0px 0px -8% 0px"});
  els.forEach(function(e){io.observe(e)});
})();
