// Renders the documentation PDFs as category shelves on in-site pages.
// Reads the books.json manifest (categories + books) produced by book_builder.py.

// Books are deployed to <root>/archive/<lang>/, a sibling of the <lang>/ site tree, so
// they survive per-language site syncs. This script is served from
// <lang>/resources/javascript/, so derive the archive root (and language) from its own
// URL — robust under previews too.
const { MANIFEST_URL, ARCHIVE_ROOT } = (() => {
    const src = document.currentScript && document.currentScript.src;
    if (!src) return { MANIFEST_URL: "books.json", ARCHIVE_ROOT: "" };
    const siteLangRoot = src.replace(/resources\/javascript\/books\.js.*$/, "");
    const lang = siteLangRoot.replace(/\/$/, "").split("/").pop();
    const archiveRoot = new URL("../archive/" + lang + "/", siteLangRoot).href;
    return { MANIFEST_URL: archiveRoot + "books.json", ARCHIVE_ROOT: archiveRoot };
})();

// Shown when a book has no thumbnail (e.g. catalogued archive PDFs) or its cover fails
// to load. A neutral document cover, inlined so it needs no network request.
const PLACEHOLDER_COVER =
    "data:image/svg+xml," +
    encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="400" viewBox="0 0 300 400">' +
            '<rect width="300" height="400" fill="#eceff1"/>' +
            '<rect x="1" y="1" width="298" height="398" fill="none" stroke="#cfd8dc" stroke-width="2"/>' +
            '<g fill="#b0bec5"><rect x="60" y="120" width="180" height="14" rx="3"/>' +
            '<rect x="60" y="150" width="180" height="14" rx="3"/>' +
            '<rect x="60" y="180" width="120" height="14" rx="3"/></g>' +
            '<text x="150" y="300" font-family="sans-serif" font-size="40" font-weight="bold" ' +
            'fill="#90a4ae" text-anchor="middle">PDF</text></svg>'
    );

const fmtSize = (mb) => (mb >= 1 ? mb.toFixed(1) + " MB" : Math.round(mb * 1024) + " KB");
const titleCase = (s) => s.charAt(0).toUpperCase() + s.slice(1);

// Newest version first. Compares dotted numeric versions (2.41 > 2.40 > 2.9 handled
// numerically); falls back to reverse string order for anything non-numeric.
function compareVersionsDesc(a, b) {
    const pa = a.split(".").map(Number);
    const pb = b.split(".").map(Number);
    if (pa.concat(pb).some(Number.isNaN)) return b.localeCompare(a);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
        const diff = (pb[i] || 0) - (pa[i] || 0);
        if (diff) return diff;
    }
    return 0;
}

// Build ordered shelves from the configured categories, appending any
// category referenced by a book but missing from the config.
function buildShelves(categories, books) {
    const meta = new Map(categories.map((c) => [c.key, c]));
    const order = categories.map((c) => c.key);
    const shelves = new Map(order.map((key) => [key, []]));

    for (const book of books) {
        if (!shelves.has(book.category)) {
            shelves.set(book.category, []);
            order.push(book.category);
        }
        shelves.get(book.category).push(book);
    }

    return order
        .map((key) => ({
            key,
            label: (meta.get(key) || {}).label || titleCase(key),
            colour: (meta.get(key) || {}).colour || "",
            books: shelves.get(key).sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
        }))
        .filter((shelf) => shelf.books.length);
}

function el(tag, cls, html) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html != null) node.innerHTML = html;
    return node;
}

function coverImg(book) {
    const img = el("img");
    img.src = book.thumbnail ? ARCHIVE_ROOT + book.thumbnail : PLACEHOLDER_COVER;
    img.alt = "Cover of " + book.title;
    img.loading = "lazy";
    img.onerror = () => {
        img.onerror = null;
        img.src = PLACEHOLDER_COVER;
    };
    return img;
}

function renderShelf(shelf) {
    const section = el("section", "shelf-section");
    section.dataset.cat = shelf.key;
    if (shelf.colour) section.style.setProperty("--cat", shelf.colour);
    section.appendChild(
        el(
            "div",
            "shelf-head",
            `<span class="cat-dot"></span><h2>${shelf.label}</h2>` +
                `<span class="cat-count">${shelf.books.length} title${shelf.books.length > 1 ? "s" : ""}</span>`
        )
    );

    const row = el("div", "shelf-row");
    for (const book of shelf.books) {
        const spine = el("a", "spine");
        spine.href = ARCHIVE_ROOT + book.file;
        spine.target = "_blank";
        const cover = el("div", "spine-cover");
        cover.appendChild(coverImg(book));
        spine.appendChild(cover);
        spine.appendChild(el("div", "spine-cap", `<h3>${book.title}</h3><span>${fmtSize(book.size)}</span>`));
        row.appendChild(spine);
    }
    section.appendChild(row);
    return section;
}

function renderShelvesInto(parent, categories, books) {
    for (const shelf of buildShelves(categories, books)) {
        parent.appendChild(renderShelf(shelf));
    }
}

// Complete Manuals: the latest (unversioned) books, as category shelves.
function renderComplete(container, manifest, books) {
    const latest = books.filter((book) => !book.version);
    if (!latest.length) {
        container.textContent = "No manuals available.";
        return;
    }
    renderShelvesInto(container, manifest.categories || [], latest);
}

// Previous Versions: versioned books, one version shown at a time, chosen from a
// selector at the top (defaults to the newest version).
function renderPrevious(container, manifest, books) {
    const versioned = books.filter((book) => book.version);
    if (!versioned.length) {
        container.textContent = "No previous versions available.";
        return;
    }
    const versions = [...new Set(versioned.map((b) => b.version))].sort(compareVersionsDesc);

    const controls = el("div", "version-controls");
    const label = el("label", "version-label", "Version");
    label.setAttribute("for", "version-select");
    const select = el("select", "version-select");
    select.id = "version-select";
    for (const version of versions) {
        const option = el("option");
        option.value = version;
        option.textContent = version;
        select.appendChild(option);
    }
    controls.appendChild(label);
    controls.appendChild(select);
    container.appendChild(controls);

    const body = el("div", "version-body");
    container.appendChild(body);

    const show = (version) => {
        body.innerHTML = "";
        renderShelvesInto(body, manifest.categories || [], versioned.filter((b) => b.version === version));
    };
    select.addEventListener("change", () => show(select.value));
    show(versions[0]);
}

async function init() {
    const completeContainer = document.getElementById("pdf-books-container");
    const previousContainer = document.getElementById("pdf-books-previous-container");
    if (!completeContainer && !previousContainer) return;

    let manifest;
    try {
        const response = await fetch(MANIFEST_URL);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        manifest = await response.json();
    } catch (error) {
        console.error("Could not fetch or parse books data:", error);
        const message = "Could not load book information.";
        if (completeContainer) completeContainer.textContent = message;
        if (previousContainer) previousContainer.textContent = message;
        return;
    }

    const books = Object.entries(manifest.books || {}).map(([file, book]) => ({ ...book, file }));
    if (completeContainer) renderComplete(completeContainer, manifest, books);
    if (previousContainer) renderPrevious(previousContainer, manifest, books);
}

document.addEventListener("DOMContentLoaded", init);
