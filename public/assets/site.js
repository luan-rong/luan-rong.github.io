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

  // Photography: shuffle the complete gallery whenever a visitor loads the page.
  // Do this client-side (not at build time), so refreshes produce new photo orders.
  // Without JavaScript, photos remain ordinary links to their original files.
  const gallery = document.querySelector('#photo-gallery');
  if (!gallery) return;
  const cards = [...gallery.querySelectorAll('.photo-card')];
  for (let i = cards.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [cards[i], cards[j]] = [cards[j], cards[i]];
  }
  gallery.append(...cards);

  const dialog = document.querySelector('#photo-lightbox');
  const image = document.querySelector('#lightbox-image');
  const title = document.querySelector('#lightbox-title');
  const details = document.querySelector('#lightbox-details');
  const position = document.querySelector('#lightbox-position');
  const closeButton = dialog?.querySelector('.lightbox-close');
  let current = null;
  let lastFocused = null;
  const visibleLinks = () => cards.map(card => card.querySelector('.photo-card__link'));

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
