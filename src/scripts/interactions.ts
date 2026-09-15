const storyDialog = document.querySelector<HTMLDialogElement>("#story-dialog");
const viewerDialog = document.querySelector<HTMLDialogElement>("#art-viewer");
const viewerImage = document.querySelector<HTMLImageElement>("#viewer-image");
const viewerTitle = document.querySelector<HTMLElement>("#viewer-title");
const viewerCount = document.querySelector<HTMLElement>("#viewer-count");
const viewerNote = document.querySelector<HTMLElement>("#viewer-note");
const revealNote = document.querySelector<HTMLButtonElement>("#reveal-note");
const cards = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-artwork-viewer]"));
let activeIndex = -1;
let lastFocusedElement: HTMLElement | null = null;

function closeStory() {
  if (storyDialog?.open) storyDialog.close();
}

document.querySelectorAll<HTMLElement>("[data-open-story]").forEach((button) => {
  button.addEventListener("click", () => {
    if (!storyDialog || storyDialog.open) return;
    lastFocusedElement = document.activeElement as HTMLElement | null;
    storyDialog.showModal();
  });
});

document.querySelectorAll<HTMLElement>("[data-close-story]").forEach((button) => {
  button.addEventListener("click", closeStory);
});

storyDialog?.addEventListener("click", (event) => {
  if (event.target === storyDialog) closeStory();
});

storyDialog?.addEventListener("close", () => {
  lastFocusedElement?.focus();
});

function updateProgress() {
  const label = document.querySelector<HTMLElement>("[data-progress-label]");
  const bar = document.querySelector<HTMLElement>("[data-progress-bar]");
  if (!label) return;

  let seenCount = 0;
  try {
    const seen = JSON.parse(localStorage.getItem("ganesha108-seen") || "[]");
    seenCount = Array.isArray(seen) ? Math.min(seen.length, 108) : 0;
  } catch {
    seenCount = 0;
  }
  label.textContent = seenCount + " of 108 explored";
  if (bar) bar.style.width = (seenCount / 108) * 100 + "%";
}

function rememberArtwork(id: string) {
  try {
    const current = JSON.parse(localStorage.getItem("ganesha108-seen") || "[]");
    const seen = new Set(Array.isArray(current) ? current : []);
    seen.add(id);
    localStorage.setItem("ganesha108-seen", JSON.stringify(Array.from(seen)));
  } catch {
    // The viewer remains fully usable when local storage is unavailable.
  }
  updateProgress();
}

function setShareableArtwork(id: string | null) {
  const url = new URL(window.location.href);
  if (id) url.searchParams.set("work", id);
  else url.searchParams.delete("work");
  window.history.replaceState(window.history.state, "", url);
}

function renderArtwork(index: number) {
  if (!viewerImage || !viewerTitle || !viewerCount || !revealNote || !viewerNote || cards.length === 0) return;
  activeIndex = (index + cards.length) % cards.length;
  const card = cards[activeIndex];
  const id = card.dataset.artworkId || "";
  const title = card.dataset.artworkTitle || "Ganesha artwork";
  const note = card.dataset.artworkNote || "";

  viewerImage.src = card.dataset.artworkSrc || "";
  viewerImage.alt = card.dataset.artworkAlt || title;
  viewerTitle.textContent = title;
  viewerCount.textContent = String(activeIndex + 1).padStart(2, "0") + " of " + String(cards.length).padStart(2, "0");
  revealNote.hidden = note.length === 0;
  revealNote.textContent = "What to notice";
  viewerNote.hidden = true;
  viewerNote.textContent = note;

  const cssUrl = "url('" + (card.dataset.artworkSrc || "") + "')";
  document.documentElement.style.setProperty("--focus-image", cssUrl);
  rememberArtwork(id);
  setShareableArtwork(id);
}

function openArtwork(index: number) {
  if (!viewerDialog || cards.length === 0) return;
  renderArtwork(index);
  if (!viewerDialog.open) viewerDialog.showModal();
}

function closeViewer() {
  if (viewerDialog?.open) viewerDialog.close();
}

document.querySelectorAll<HTMLButtonElement>("[data-close-viewer]").forEach((button) => {
  button.addEventListener("click", closeViewer);
});

cards.forEach((card, index) => {
  card.addEventListener("click", () => openArtwork(index));
});

document.querySelectorAll<HTMLButtonElement>("[data-surprise]").forEach((button) => {
  button.addEventListener("click", () => {
    if (cards.length === 0) return;
    const nextIndex = activeIndex < 0 || cards.length === 1
      ? Math.floor(Math.random() * cards.length)
      : (activeIndex + 1 + Math.floor(Math.random() * (cards.length - 1))) % cards.length;
    openArtwork(nextIndex);
  });
});

document.querySelectorAll<HTMLButtonElement>("[data-viewer-prev]").forEach((button) => {
  button.addEventListener("click", () => renderArtwork(activeIndex - 1));
});

document.querySelectorAll<HTMLButtonElement>("[data-viewer-next]").forEach((button) => {
  button.addEventListener("click", () => renderArtwork(activeIndex + 1));
});

revealNote?.addEventListener("click", () => {
  if (!viewerNote || !revealNote) return;
  viewerNote.hidden = !viewerNote.hidden;
  revealNote.textContent = viewerNote.hidden ? "What to notice" : "Hide the note";
});

viewerDialog?.addEventListener("click", (event) => {
  if (event.target === viewerDialog) closeViewer();
});

viewerDialog?.addEventListener("close", () => {
  document.documentElement.style.removeProperty("--focus-image");
  setShareableArtwork(null);
  if (activeIndex >= 0) cards[activeIndex]?.focus();
});

viewerDialog?.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    renderArtwork(activeIndex - 1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    renderArtwork(activeIndex + 1);
  }
});

const viewerImageWrap = document.querySelector<HTMLElement>(".viewer-image-wrap");
let touchStartX = 0;
let touchStartY = 0;

viewerImageWrap?.addEventListener("pointerdown", (event) => {
  touchStartX = event.clientX;
  touchStartY = event.clientY;
});

viewerImageWrap?.addEventListener("pointerup", (event) => {
  const deltaX = event.clientX - touchStartX;
  const deltaY = event.clientY - touchStartY;
  if (Math.abs(deltaX) > 65 && Math.abs(deltaX) > Math.abs(deltaY) * 1.25) {
    renderArtwork(activeIndex + (deltaX < 0 ? 1 : -1));
  }
});

updateProgress();

const url = new URL(window.location.href);
const requestedWork = url.searchParams.get("work");
if (requestedWork) {
  const requestedIndex = cards.findIndex((card) => card.dataset.artworkId === requestedWork);
  if (requestedIndex >= 0) openArtwork(requestedIndex);
}
