const video = document.getElementById("scrollVideo");

video.addEventListener("loadedmetadata", () => {
  const duration = video.duration;

  window.addEventListener("scroll", () => {
    const scrollTop = window.scrollY;
    const maxScroll = document.body.scrollHeight - window.innerHeight;
    const scrollFraction = scrollTop / maxScroll;

    video.currentTime = duration * scrollFraction;
  });
});
