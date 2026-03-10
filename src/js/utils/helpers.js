function formatDate(date) {
    const options = { year: 'numeric', month: '2-digit', day: '2-digit' };
    return new Intl.DateTimeFormat('en-US', options).format(date);
}

function generateUniqueId() {
    return 'id-' + Math.random().toString(36).substr(2, 16);
}

function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function isEmpty(obj) {
    return Object.keys(obj).length === 0;
}

export { formatDate, generateUniqueId, deepClone, isEmpty };