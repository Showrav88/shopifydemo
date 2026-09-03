(function () {
  const track = document.getElementById("slidesTrack");
  const slides = Array.from(document.querySelectorAll(".slide"));
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const currentEl = document.getElementById("currentSlide");
  const totalEl = document.getElementById("totalSlides");
  const progressFill = document.getElementById("progressFill");
  const dotsContainer = document.getElementById("dots");

  let current = 0;
  const total = slides.length;

  totalEl.textContent = total;

  slides.forEach((_, i) => {
    const dot = document.createElement("button");
    dot.className = "dot-btn" + (i === 0 ? " active" : "");
    dot.setAttribute("aria-label", "Go to slide " + (i + 1));
    dot.addEventListener("click", () => goTo(i));
    dotsContainer.appendChild(dot);
  });

  const dots = Array.from(dotsContainer.querySelectorAll(".dot-btn"));

  function goTo(index) {
    if (index < 0 || index >= total) return;
    current = index;

    track.style.transform = "translateX(-" + current * 100 + "%)";

    slides.forEach((slide, i) => {
      slide.classList.toggle("active", i === current);
      slide.setAttribute("aria-hidden", i !== current);
    });

    dots.forEach((dot, i) => {
      dot.classList.toggle("active", i === current);
    });

    currentEl.textContent = current + 1;
    progressFill.style.width = ((current + 1) / total) * 100 + "%";

    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === total - 1;

    history.replaceState(null, "", "#slide-" + (current + 1));
  }

  function next() { goTo(current + 1); }
  function prev() { goTo(current - 1); }

  prevBtn.addEventListener("click", prev);
  nextBtn.addEventListener("click", next);

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === " ") {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      prev();
    } else if (e.key === "Home") {
      e.preventDefault();
      goTo(0);
    } else if (e.key === "End") {
      e.preventDefault();
      goTo(total - 1);
    }
  });

  let touchStartX = 0;
  track.addEventListener("touchstart", (e) => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });

  track.addEventListener("touchend", (e) => {
    const diff = touchStartX - e.changedTouches[0].screenX;
    if (Math.abs(diff) > 50) {
      diff > 0 ? next() : prev();
    }
  }, { passive: true });

  const hash = window.location.hash;
  if (hash.startsWith("#slide-")) {
    const num = parseInt(hash.replace("#slide-", ""), 10);
    if (num >= 1 && num <= total) goTo(num - 1);
    else goTo(0);
  } else {
    goTo(0);
  }
})();
