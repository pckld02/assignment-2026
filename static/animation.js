const video = document.getElementById("scrollVideo");

video?.addEventListener("loadedmetadata", () => {
  const duration = video.duration;

  window.addEventListener("scroll", () => {
    const scrollTop = window.scrollY;
    const maxScroll = document.body.scrollHeight - window.innerHeight;
    const scrollFraction = scrollTop / maxScroll;

    video.currentTime = duration * scrollFraction;
  });
});

// High Contrast Mode - Site-wide
document.addEventListener("DOMContentLoaded", function() {
  // Load saved state on page load
  const isHighContrast = localStorage.getItem("highContrast") === "enabled";
  if (isHighContrast) {
    document.body.classList.add("high-contrast");
  }

  // Handle button click
  const highcontrastBtn = document.getElementById("highcontrast-btn");
  if (highcontrastBtn) {
    highcontrastBtn.addEventListener("click", function() {
      document.body.classList.toggle("high-contrast");
      
      // Save state to localStorage
      if (document.body.classList.contains("high-contrast")) {
        localStorage.setItem("highContrast", "enabled");
      } else {
        localStorage.setItem("highContrast", "disabled");
      }
    });
  }
});
