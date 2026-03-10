// This file contains JavaScript for managing the sidebar component, including navigation functionality.

document.addEventListener('DOMContentLoaded', function() {
    const sidebarLinks = document.querySelectorAll('.sidebar-link');

    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const targetPage = this.getAttribute('href');
            loadPage(targetPage);
        });
    });

    function loadPage(page) {
        // Logic to load the specified page content
        // This could involve fetching the page via AJAX or updating the DOM directly
        console.log(`Loading page: ${page}`);
        // Example: window.location.href = page; // Uncomment to navigate to the page
    }
});