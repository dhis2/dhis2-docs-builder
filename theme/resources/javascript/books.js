// Document categories data
async function fetchBooksData() {
    try {
        const response = await fetch("books.json");
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Could not fetch or parse books data:", error);
        return {}; // Return empty object on error
    }
}

function transformDataToCategories(booksData) {
  const categoryMap = {
    implement: "Implementation Guides",
    manage: "System Management",
    develop: "Developer Resources",
  }

  const categories = {}

  Object.entries(booksData).forEach(([filename, book]) => {
    const categoryKey = book.category
    const categoryName = categoryMap[categoryKey] || categoryKey

    if (!categories[categoryKey]) {
      categories[categoryKey] = {
        id: categoryKey,
        name: categoryName,
        books: [],
      }
    }

    // Format date from ISO string
    const date = new Date(book.creation_time).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })

    categories[categoryKey].books.push({
      id: filename.replace(".pdf", ""),
      title: book.title,
      thumbnail: book.thumbnail,
      size: `${book.size} MB`,
      date: date,
      filename: filename,
    })
  })

  return Object.values(categories)
}

// Create download icon SVG
function createDownloadIcon() {
  return `<svg class="pdf-download-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
  </svg>`
}

// Create open icon SVG
function createOpenIcon() {
    return `<svg class="pdf-open-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line>
    </svg>`
}

// Create book card HTML
function createBookCard(book) {
  return `
    <div class="pdf-book-card">
      <div class="pdf-card-header">
        <div class="pdf-thumbnail-container">
          <img src="${book.thumbnail || "/placeholder.svg"}" alt="${book.title} thumbnail" class="pdf-thumbnail">
        </div>
        <div class="pdf-title-row">
          <h3 class="pdf-book-title">${book.title}</h3>
        </div>
      </div>
      <div class="pdf-card-content">
        <div class="pdf-metadata-row">
          <span>${book.size}</span>
          <span>${book.date}</span>
        </div>
        <div class="pdf-button-group">
            <button class="pdf-download-btn" onclick="downloadBook('${book.id}')">
              ${createDownloadIcon()}
              Download
            </button>
            <a href="${book.filename.trim()}" target="_blank" class="pdf-open-btn">
                ${createOpenIcon()}
                Open
            </a>
        </div>
      </div>
    </div>
  `
}

// Create category section HTML
function createCategorySection(category) {
  const booksHTML = category.books.map((book) => createBookCard(book)).join("")

  return `
    <section class="pdf-category-section">
      <h2 class="pdf-category-title">${category.name}</h2>
      <div class="pdf-books-grid">
        ${booksHTML}
      </div>
    </section>
  `
}

// Download book function
function downloadBook(bookId, booksData) {
  const filename = bookId + ".pdf"
  const book = booksData[filename]

  if (book) {
    const link = document.createElement('a');
    link.href = filename.trim();
    link.download = filename.trim();
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

// Initialize the page
async function init() {
  const booksData = await fetchBooksData();
  if (Object.keys(booksData).length === 0) {
      console.log("No book data available to display.");
      return;
  }

  const documentCategories = transformDataToCategories(booksData)
  const container = document.getElementById("categories-container")
  
  const categoriesHTML = documentCategories.map((category) => {
      const booksHTML = category.books.map((book) => createBookCard(book)).join("");
      return `
        <section class="pdf-category-section">
          <h2 class="pdf-category-title">${category.name}</h2>
          <div class="pdf-books-grid">
            ${booksHTML}
          </div>
        </section>
      `;
  }).join("");

  container.innerHTML = categoriesHTML;

  // Re-bind download events if necessary, or pass data down.
  // A simple way is to make booksData available globally or pass it.
  // Let's re-bind.
  container.querySelectorAll('.pdf-download-btn').forEach(btn => {
      const bookId = btn.getAttribute('onclick').match(/'([^']+)'/)[1];
      btn.onclick = () => downloadBook(bookId, booksData);
  });
}

// Run when DOM is loaded
document.addEventListener("DOMContentLoaded", init)
