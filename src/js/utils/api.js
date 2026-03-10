// This file contains utility functions for making API calls, if applicable.

const apiBaseUrl = 'https://api.example.com'; // Replace with your actual API base URL

async function fetchData(endpoint) {
    try {
        const response = await fetch(`${apiBaseUrl}/${endpoint}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return await response.json();
    } catch (error) {
        console.error('There has been a problem with your fetch operation:', error);
        throw error;
    }
}

async function postData(endpoint, data) {
    try {
        const response = await fetch(`${apiBaseUrl}/${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return await response.json();
    } catch (error) {
        console.error('There has been a problem with your post operation:', error);
        throw error;
    }
}

export { fetchData, postData };