// This file contains JavaScript specific to the settings page, managing user configurations.

document.addEventListener('DOMContentLoaded', function() {
    const saveButton = document.getElementById('save-settings');
    const settingsForm = document.getElementById('settings-form');

    saveButton.addEventListener('click', function(event) {
        event.preventDefault();
        const formData = new FormData(settingsForm);
        const settings = {};

        formData.forEach((value, key) => {
            settings[key] = value;
        });

        // Here you would typically send the settings to the server or save them locally
        console.log('Settings saved:', settings);
        alert('Settings have been saved successfully!');
    });
});