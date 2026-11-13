const storyMetadata = [
  { slug: "boston-2026", title: "boston-2026" },
  {
    slug: "isabella-stewart-gardner-2026",
    title: "isabella-stewart-gardner-2026",
  },
  { slug: "state-fair-5k-2026", title: "state-fair-5k-2026" },
  {
    slug: "fbla-san-antonio-2026",
    title: "fbla-san-antonio-2026",
  },
  { slug: "deca-nd-slc-2026", title: "deca-nd-slc-2026" },
  { slug: "mexico-2026", title: "mexico-2026" },
];

let stories = [];
const archiveView = document.querySelector("#archive-view");
const galleryView = document.querySelector("#gallery-view");
const storyList = document.querySelector("#story-list");
const storyNavigation = document.querySelector("#story-navigation");

function renderArchive() {
  const entries = document.createDocumentFragment();
  stories.forEach((story) => {
    const link = document.createElement("a");
    link.className = "archive-entry";
    link.href = `#/${encodeURIComponent(story.slug)}`;

    const title = document.createElement("span");
    title.className = "entry-title";
    title.textContent = story.title;
    link.append(title);
    entries.append(link);
  });
  storyList.replaceChildren(entries);
}

function renderStoryNavigation(activeStory) {
  const currentLink = document.createElement("a");
  currentLink.className = "story-nav-current";
  currentLink.href = `#/${encodeURIComponent(activeStory.slug)}`;
  currentLink.textContent = activeStory.slug;

  const more = document.createElement("details");
  more.className = "story-more";
  const summary = document.createElement("summary");
  summary.textContent = "› more";
  more.append(summary);

  const menu = document.createElement("div");
  menu.className = "story-more-menu";
  stories
    .filter((story) => story.slug !== activeStory.slug)
    .forEach((story) => {
      const link = document.createElement("a");
      link.className = "story-nav-link";
      link.href = `#/${encodeURIComponent(story.slug)}`;
      link.textContent = story.slug;
      menu.append(link);
    });
  more.append(menu);
  storyNavigation.replaceChildren(currentLink, more);
}

function showArchive() {
  document.body.classList.add("archive-page");
  document.body.classList.remove("gallery-page");
  archiveView.hidden = false;
  galleryView.hidden = true;
  document.title = "Photo archive - Studio Franco";
  window.scrollTo(0, 0);
}

function showStory(story) {
  if (!story) {
    showArchive();
    return;
  }

  document.body.classList.remove("archive-page");
  document.body.classList.add("gallery-page");
  archiveView.hidden = true;
  galleryView.hidden = false;
  document.title = `${story.title} - Studio Franco`;
  document.querySelector("#topbar-label").textContent =
    `STUDIO FRANCO / ${story.slug.toUpperCase()}`;
  document.querySelector("#topbar-link").innerHTML =
    'BACK TO ARCHIVE <span aria-hidden="true"></span>';
  renderStoryNavigation(story);

  const thumbnailPanel = document.querySelector("#thumbnail-panel");
  const thumbnails = document.createDocumentFragment();
  story.photos.forEach((photo, index) => {
    const button = document.createElement("button");
    button.className = "thumbnail";
    button.type = "button";
    button.setAttribute(
      "aria-label",
      `Show photo ${index + 1}: ${photo.caption}`,
    );
    button.addEventListener("click", () => selectPhoto(story, index));

    const image = document.createElement("img");
    image.src = photo.small;
    image.alt = "";
    image.loading = "lazy";
    image.decoding = "async";
    button.append(image);
    thumbnails.append(button);
  });
  thumbnailPanel.replaceChildren(thumbnails);

  const photoDashes = document.querySelector("#photo-dashes");
  const dashes = document.createDocumentFragment();
  story.photos.forEach((_, index) => {
    const dash = document.createElement("span");
    dash.className = "photo-dash";
    dashes.append(dash);
  });
  photoDashes.replaceChildren(dashes);

  const hasPhotos = story.photos.length > 0;
  photoDashes.setAttribute(
    "aria-valuemax",
    String(Math.max(story.photos.length, 1)),
  );
  photoDashes.setAttribute("aria-disabled", String(!hasPhotos));
  photoDashes.tabIndex = hasPhotos ? 0 : -1;
  photoDashes.onpointerdown = (event) => {
    if (!hasPhotos || (event.pointerType === "mouse" && event.button !== 0)) {
      return;
    }
    photoDashes.setPointerCapture(event.pointerId);
    event.preventDefault();
    selectPhotoFromPointer(story, event);
  };
  photoDashes.onpointermove = (event) => {
    if (hasPhotos && photoDashes.hasPointerCapture(event.pointerId)) {
      selectPhotoFromPointer(story, event);
    }
  };
  photoDashes.onpointerup = (event) => {
    if (photoDashes.hasPointerCapture(event.pointerId)) {
      photoDashes.releasePointerCapture(event.pointerId);
    }
  };
  photoDashes.onpointercancel = photoDashes.onpointerup;
  photoDashes.onkeydown = (event) => {
    if (!hasPhotos) {
      return;
    }
    const currentIndex = Number(photoDashes.dataset.activeIndex || "0");
    let nextIndex = currentIndex;
    switch (event.key) {
      case "ArrowLeft":
      case "ArrowDown":
        nextIndex -= 1;
        break;
      case "ArrowRight":
      case "ArrowUp":
        nextIndex += 1;
        break;
      case "Home":
        nextIndex = 0;
        break;
      case "End":
        nextIndex = story.photos.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    selectPhoto(
      story,
      Math.max(0, Math.min(nextIndex, story.photos.length - 1)),
    );
  };

  const galleryLayout = document.querySelector("#gallery-layout");
  galleryLayout.classList.toggle("is-empty", !hasPhotos);
  document.querySelector("#gallery-empty").hidden = hasPhotos;
  thumbnailPanel.hidden = !hasPhotos;
  document.querySelector(".featured-photo").hidden = !hasPhotos;
  if (hasPhotos) {
    selectPhoto(story, 0);
  }
  window.scrollTo(0, 0);
}

function selectPhotoFromPointer(story, event) {
  const photoDashes = document.querySelector("#photo-dashes");
  const dashes = photoDashes.querySelectorAll(".photo-dash");
  if (dashes.length === 0) {
    return;
  }
  const firstBounds = dashes[0].getBoundingClientRect();
  const lastBounds = dashes[dashes.length - 1].getBoundingClientRect();
  const start = firstBounds.left + firstBounds.width / 2;
  const end = lastBounds.left + lastBounds.width / 2;
  const progress = end === start ? 0 : (event.clientX - start) / (end - start);
  const index = Math.round(
    Math.max(0, Math.min(progress, 1)) * (story.photos.length - 1),
  );
  selectPhoto(story, index);
}

function selectPhoto(story, index) {
  if (index < 0 || index >= story.photos.length) {
    return;
  }
  const photo = story.photos[index];
  const featuredImage = document.querySelector("#featured-image");
  featuredImage.src = photo.small;
  featuredImage.alt = photo.caption;

  document.querySelectorAll(".thumbnail").forEach((button, buttonIndex) => {
    if (buttonIndex === index) {
      button.setAttribute("aria-current", "true");
    } else {
      button.removeAttribute("aria-current");
    }
  });

  document.querySelectorAll(".photo-dash").forEach((button, buttonIndex) => {
    if (buttonIndex === index) {
      button.setAttribute("aria-current", "true");
    } else {
      button.removeAttribute("aria-current");
    }
  });
  const photoDashes = document.querySelector("#photo-dashes");
  photoDashes.dataset.activeIndex = String(index);
  photoDashes.setAttribute("aria-valuenow", String(index + 1));
  photoDashes.setAttribute(
    "aria-valuetext",
    `Photo ${index + 1} of ${story.photos.length}: ${photo.caption}`,
  );
}

async function initializeArchive() {
  const response = await fetch("./photos/manifest.json");
  if (!response.ok) {
    throw new Error(
      `Could not load photos/manifest.json (${response.status}).`,
    );
  }

  const photoManifest = await response.json();
  if (
    !photoManifest ||
    typeof photoManifest !== "object" ||
    Array.isArray(photoManifest)
  ) {
    throw new Error(
      "photos/manifest.json must contain an event-to-photos object.",
    );
  }

  const metadataBySlug = new Map(
    storyMetadata.map((story) => [story.slug, story]),
  );
  const orderedSlugs = [
    ...storyMetadata
      .map((story) => story.slug)
      .filter((slug) => slug in photoManifest),
    ...Object.keys(photoManifest)
      .filter((slug) => !metadataBySlug.has(slug))
      .sort((first, second) => first.localeCompare(second)),
  ];

  stories = orderedSlugs.map((slug) => {
    const files = photoManifest[slug];
    if (!Array.isArray(files)) {
      throw new Error(`Invalid photo list in photos/${slug}.`);
    }

    const photos = files.map((entry) => {
      if (!entry || typeof entry !== "object") {
        throw new Error(`Invalid photo entry in photos/${slug}.`);
      }
      const { filename, caption } = entry;
      if (
        typeof filename !== "string" ||
        filename.includes("/") ||
        filename.includes("\\")
      ) {
        throw new Error(`Invalid photo filename in photos/${slug}.`);
      }

      const encodedFilename = encodeURIComponent(filename);
      return {
        small: `photos/${slug}/small/${encodedFilename}`,
        caption: typeof caption === "string" ? caption : filename,
      };
    });

    const story = metadataBySlug.get(slug) || {
      slug,
      title: slug.replace(/-/g, " "),
    };
    return { ...story, photos };
  });

  renderArchive();
  window.addEventListener("hashchange", renderRoute);
  renderRoute();
}

function showPhotoLoadError(error) {
  console.error("The photo archive could not be initialized.", error);
  document.body.classList.add("archive-page");
  document.body.classList.remove("gallery-page");
  archiveView.hidden = false;
  galleryView.hidden = true;
  const message = document.createElement("p");
  message.className = "archive-error";
  message.setAttribute("role", "alert");
  message.textContent =
    "The photo archive could not load. Check photos/manifest.json.";
  storyList.replaceChildren(message);
}

function renderRoute() {
  const slug = window.location.hash.replace(/^#\/?/, "");
  const story = stories.find((item) => item.slug === slug);
  if (slug && !story) {
    window.location.hash = "#/";
    return;
  }
  story ? showStory(story) : showArchive();
}

initializeArchive().catch(showPhotoLoadError);
