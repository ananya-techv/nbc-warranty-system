// Feature: dashboard search filter - purely client-side, filters rows already on the page
// by matching against a lowercase "bearing_code + mechanic_name" string stored per row
const searchBox = document.getElementById('searchBox');
const rows = document.querySelectorAll('#recordsTableBody tr[data-search]');
const noResults = document.getElementById('noResults');

searchBox.addEventListener('input', () => {
    const query = searchBox.value.trim().toLowerCase();
    let visibleCount = 0;

    rows.forEach(row => {
        const matches = row.dataset.search.includes(query);
        row.style.display = matches ? '' : 'none';
        if (matches) visibleCount++;
    });

    noResults.style.display = (visibleCount === 0) ? 'block' : 'none';
});
