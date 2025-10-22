document.addEventListener('DOMContentLoaded', () => {
    fetch('books.json')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('books-container');
            if (!container) return;

            // Sort books by title
            const sortedBookKeys = Object.keys(data).sort((a, b) => {
                return data[a].title.localeCompare(data[b].title);
            });

            for (const key of sortedBookKeys) {
                const book = data[key];
                const pdfPath = key;

                const card = document.createElement('a');
                card.href = pdfPath;
                card.className = 'book-card';
                card.target = '_blank'; // Open PDF in new tab

                const thumbnail = document.createElement('img');
                thumbnail.src = book.thumbnail;
                thumbnail.alt = `Thumbnail for ${book.title}`;
                thumbnail.className = 'book-thumbnail';

                const info = document.createElement('div');
                info.className = 'book-info';

                const title = document.createElement('h3');
                title.className = 'book-title';
                title.textContent = book.title;

                const meta = document.createElement('div');
                meta.className = 'book-meta';

                const category = document.createElement('p');
                category.textContent = `Category: ${book.category}`;

                const size = document.createElement('p');
                size.textContent = `Size: ${book.size} MB`;

                const created = document.createElement('p');
                created.textContent = `Updated: ${new Date(book.creation_time).toLocaleDateString()}`;

                meta.appendChild(category);
                meta.appendChild(size);
                meta.appendChild(created);
                info.appendChild(title);
                info.appendChild(meta);
                card.appendChild(thumbnail);
                card.appendChild(info);
                container.appendChild(card);
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
