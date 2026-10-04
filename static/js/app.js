document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-count]").forEach(el => {
    const target = Number(el.dataset.count);
    const duration = 1100;
    const start = performance.now();
    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(target * eased).toLocaleString();
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.classList.add("visible");
    });
  }, {threshold: 0.12});

  document.querySelectorAll(".reveal, .step-card").forEach(el => observer.observe(el));

  document.querySelectorAll(".flash").forEach(el => {
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(-10px)";
      setTimeout(() => el.remove(), 400);
    }, 4500);
  });
});
