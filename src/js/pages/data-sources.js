// This file contains JavaScript specific to the data sources page, managing data source interactions.

document.addEventListener('DOMContentLoaded', function() {
    const dataSourceForm = document.getElementById('data-source-form');
    const dataSourceList = document.getElementById('data-source-list');

    // Function to add a new data source
    function addDataSource(event) {
        event.preventDefault();
        const dataSourceName = document.getElementById('data-source-name').value;

        if (dataSourceName) {
            const listItem = document.createElement('li');
            listItem.textContent = dataSourceName;
            dataSourceList.appendChild(listItem);
            dataSourceForm.reset();
        } else {
            alert('Please enter a data source name.');
        }
    }

    // Event listener for form submission
    dataSourceForm.addEventListener('submit', addDataSource);
});