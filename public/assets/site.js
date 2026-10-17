/* Small progressive enhancements. Works without npm, a backend, or external JS. */
(() => {
  // Academic publication search and category filters.
  const list = document.querySelector('#publication-list');
  if (list) {
    const cards = [...list.querySelectorAll('.paper-card')];
    const chips = [...document.querySelectorAll('[data-filter]')];
    const search = document.querySelector('#paper-search');
    const counter = document.querySelector('#results-counter');
    const empty = document.querySelector('#no-results');
    let category = 'all';

    const update = () => {
      const needle = (search?.value || '').toLocaleLowerCase().trim();
      let found = 0;
      for (const card of cards) {
        const matches = (category === 'all' || card.dataset.category === category) &&
          (!needle || (card.dataset.search || '').includes(needle));
        card.hidden = !matches;
        if (matches) found++;
      }
      counter.textContent = `Showing ${found} of ${cards.length} entries`;
      empty.hidden = found !== 0;
      chips.forEach(chip => {
        const selected = chip.dataset.filter === category;
        chip.classList.toggle('is-selected', selected);
        chip.setAttribute('aria-pressed', String(selected));
      });
    };
    chips.forEach(chip => chip.addEventListener('click', () => {
      category = chip.dataset.filter;
      update();
    }));
    search?.addEventListener('input', update);
    update();
  }

  // Photography gallery: filter by album and open original files in a native dialog.
  // Without JavaScript, each image is still a normal link to its full file.
  const gallery = document.querySelector('#photo-gallery');
  if (!gallery) return;
  const cards = [...gallery.querySelectorAll('.photo-card')];
  const filters = [...document.querySelectorAll('[data-photo-filter]')];
  const counter = document.querySelector('#photo-counter');
  const empty = document.querySelector('#photo-no-results');
  const dialog = document.querySelector('#photo-lightbox');
  const image = document.querySelector('#lightbox-image');
  const title = document.querySelector('#lightbox-title');
  const details = document.querySelector('#lightbox-details');
  const position = document.querySelector('#lightbox-position');
  const closeButton = dialog?.querySelector('.lightbox-close');
  let album = 'all';
  let current = null;
  let lastFocused = null;

  const visibleLinks = () => cards
    .filter(card => !card.hidden)
    .map(card => card.querySelector('.photo-card__link'));

  const updateGallery = () => {
    let visible = 0;
    cards.forEach(card => {
      card.hidden = album !== 'all' && card.dataset.photoAlbum !== album;
      if (!card.hidden) visible++;
    });
    counter.textContent = `${visible} photograph${visible === 1 ? '' : 's'}`;
    empty.hidden = visible !== 0;
    filters.forEach(filter => {
      const selected = filter.dataset.photoFilter === album;
      filter.classList.toggle('is-selected', selected);
      filter.setAttribute('aria-pressed', String(selected));
    });
  };

  filters.forEach(filter => filter.addEventListener('click', () => {
    album = filter.dataset.photoFilter;
    updateGallery();
  }));
  updateGallery();

  if (!dialog || typeof dialog.showModal !== 'function') return;

  const updateLightbox = link => {
    const visible = visibleLinks();
    current = link;
    image.src = link.href;
    image.alt = link.dataset.photoAlt || link.dataset.photoTitle || 'Photograph';
    title.textContent = link.dataset.photoTitle || '';
    details.textContent = [link.dataset.photoLocation, link.dataset.photoDate].filter(Boolean).join(' · ');
    position.textContent = `${visible.indexOf(link) + 1} / ${visible.length}`;
  };
  const move = step => {
    const visible = visibleLinks();
    if (!visible.length) return;
    const index = visible.indexOf(current);
    updateLightbox(visible[(index + step + visible.length) % visible.length]);
  };

  gallery.addEventListener('click', event => {
    const link = event.target.closest('.photo-card__link');
    if (!link || !gallery.contains(link)) return;
    event.preventDefault();
    lastFocused = link;
    updateLightbox(link);
    dialog.showModal();
    closeButton?.focus();
  });
  closeButton?.addEventListener('click', () => dialog.close());
  dialog.querySelector('.lightbox-prev')?.addEventListener('click', () => move(-1));
  dialog.querySelector('.lightbox-next')?.addEventListener('click', () => move(1));
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => {
    image.removeAttribute('src');
    lastFocused?.focus();
  });
  document.addEventListener('keydown', event => {
    if (!dialog.open) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); move(-1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); move(1); }
  });
})();
