// Loads the books.json manifest and renders the PDFs as category shelves.
// Category labels, colours and order come from the manifest's categories block.

const fmtSize = mb => mb >= 1 ? mb.toFixed(1) + ' MB' : Math.round(mb * 1024) + ' KB';
const titleCase = s => s.charAt(0).toUpperCase() + s.slice(1);

// Build ordered shelves from the configured categories, appending any
// category referenced by a book but missing from the config.
function buildShelves(categories, books) {
    const meta = new Map(categories.map(c => [c.key, c]));
    const order = categories.map(c => c.key);
    const shelves = new Map(order.map(key => [key, []]));

    for (const book of books) {
        if (!shelves.has(book.category)) {
            shelves.set(book.category, []);
            order.push(book.category);
        }
        shelves.get(book.category).push(book);
    }

    return order
        .map(key => ({
            key,
            label: (meta.get(key) || {}).label || titleCase(key),
            colour: (meta.get(key) || {}).colour || '',
            books: shelves.get(key).sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
        }))
        .filter(shelf => shelf.books.length);
}

function el(tag, cls, html) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html != null) node.innerHTML = html;
    return node;
}

function renderShelf(shelf) {
    const section = el('section', 'shelf-section');
    section.dataset.cat = shelf.key;
    if (shelf.colour) section.style.setProperty('--cat', shelf.colour);
    section.appendChild(el('div', 'shelf-head',
        `<span class="cat-dot"></span><h2>${shelf.label}</h2>` +
        `<span class="cat-count">${shelf.books.length} title${shelf.books.length > 1 ? 's' : ''}</span>`));

    const row = el('div', 'shelf-row');
    for (const book of shelf.books) {
        const spine = el('a', 'spine');
        spine.href = book.file;
        spine.target = '_blank';
        spine.innerHTML =
            `<div class="spine-cover"><img src="${book.thumbnail}" alt="Cover of ${book.title}" loading="lazy"></div>` +
            `<div class="spine-cap"><h3>${book.title}</h3><span>${fmtSize(book.size)}</span></div>`;
        row.appendChild(spine);
    }
    section.appendChild(row);
    return section;
}

document.addEventListener('DOMContentLoaded', () => {
    fetch('books.json')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('books-container');
            if (!container) return;

            const books = Object.entries(data.books || {}).map(([file, book]) => ({ ...book, file }));
            const shelves = buildShelves(data.categories || [], books);

            const summary = document.getElementById('summary');
            if (summary) {
                const totMb = books.reduce((sum, b) => sum + b.size, 0);
                summary.textContent =
                    `${books.length} books across ${shelves.length} categories · ${fmtSize(totMb)} total`;
            }

            for (const shelf of shelves) {
                container.appendChild(renderShelf(shelf));
            }
        })
        .catch(error => {
            console.error('Error fetching or processing book data:', error);
            const container = document.getElementById('books-container');
            if (container) {
                container.textContent = 'Could not load book information.';
            }
        });
});
