/* ============================================================================
   DATA INTEGRITY PLATFORM - MAIN JAVASCRIPT FILE
   BTech CSE Final Year Project
   
   PURPOSE:
   This file handles all frontend logic including:
   - Data storage (currently localStorage, later API calls)
   - Data retrieval and display
   - Integrity verification (placeholder for now)
   - User interface interactions
   
   NOTE FOR VIVA:
   This is Phase 1 (Frontend only). All backend integration points are marked
   with "TODO: Backend Integration" comments.
   ============================================================================ */

/* ============================================================================
   GLOBAL CONSTANTS & CONFIGURATION
   ============================================================================ */

// API Base URL - Flask Backend
const API_BASE_URL = 'https://secure-data-storage-and-integrity.onrender.com/api/data';

// Status types for data integrity
const STATUS = {
    PENDING: 'pending',
    VALID: 'valid',
    INVALID: 'invalid'
};

/* ============================================================================
   UTILITY FUNCTIONS
   ============================================================================ */

/**
 * Generate a unique ID for each record
 * NOTE: No longer needed - MongoDB generates _id automatically
 */
function generateId() {
    // Not used anymore - MongoDB generates _id
    return Date.now().toString() + Math.random().toString(36).substr(2, 9);
}

/**
 * Format timestamp to readable date string
 * @param {string|number} timestamp - ISO string or Unix timestamp
 * @returns {string} Formatted date string
 */
function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Generate SHA-256 hash
 * NOW HANDLED BY BACKEND: Flask backend computes actual SHA-256 hash
 * 
 * VIVA EXPLANATION:
 * - SHA-256 is a cryptographic hash function
 * - It creates a unique 64-character hexadecimal string
 * - Same input always gives same hash
 * - Even tiny changes in input create completely different hash
 * - This property helps detect data modification
 * - Backend uses Python's hashlib.sha256() for secure hashing
 * 
 * @param {string} data - The data to hash
 * @returns {string} This function is no longer used (backend handles hashing)
 */
function generateHash(data) {
    // No longer used - Backend handles hash generation
    // Keeping function for backward compatibility
    return null;
}

/**
 * Show notification message to user
 * @param {string} message - Message to display
 * @param {string} type - Type of notification (success, error, info)
 */
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

/* ============================================================================
   DATA STORAGE FUNCTIONS (API Integration with Flask Backend)
   ============================================================================ */

/**
 * Save data to database via API
 * Sends POST request to Flask backend
 * Backend will compute SHA-256 hash and store in MongoDB
 * 
 * VIVA EXPLANATION:
 * - Sends HTTP POST request to /api/data endpoint
 * - Backend receives data, computes SHA-256 hash
 * - Stores both data and hash in MongoDB
 * - Returns created record with ID, hash, timestamp
 * 
 * @param {string} data - Data to save
 * @returns {Promise<Object>} Saved record from backend
 */
async function saveToStorage(data) {
    try {
        const response = await fetch(API_BASE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: data })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return result.record;
    } catch (error) {
        console.error('Error saving data:', error);
        throw error;
    }
}

/**
 * Get all records from database via API
 * Sends GET request to Flask backend
 * 
 * @returns {Promise<Array>} Array of all records from MongoDB
 */
async function getAllRecords() {
    try {
        const response = await fetch(API_BASE_URL);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return result.records;
    } catch (error) {
        console.error('Error fetching records:', error);
        throw error;
    }
}

/**
 * Get single record by ID from database
 * @param {string} id - MongoDB _id
 * @returns {Promise<Object|null>} Record object or null
 */
async function getRecordById(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/${id}`);
        
        if (!response.ok) {
            if (response.status === 404) return null;
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return result.record;
    } catch (error) {
        console.error('Error fetching record:', error);
        return null;
    }
}

/**
 * Update record in database (Not used in current version)
 * @param {string} id - Record ID
 * @param {Object} updates - Fields to update
 */
async function updateRecord(id, updates) {
    // Not implemented in current API
    // Can be added later if needed
    console.warn('updateRecord not implemented');
}

/**
 * Delete record from database via API
 * @param {string} id - MongoDB _id to delete
 * @returns {Promise<boolean>} Success status
 */
async function deleteRecord(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return true;
    } catch (error) {
        console.error('Error deleting record:', error);
        throw error;
    }
}

/**
 * Clear all records from database via API
 * @returns {Promise<number>} Number of records deleted
 */
async function clearAllRecords() {
    try {
        const response = await fetch(`${API_BASE_URL}/clear`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return result.count;
    } catch (error) {
        console.error('Error clearing records:', error);
        throw error;
    }
}

/* ============================================================================
   DATA INTEGRITY VERIFICATION
   ============================================================================ */

/**
 * Verify data integrity via API
 * Backend will:
 *   1. Retrieve stored hash from MongoDB
 *   2. Recompute hash of current data
 *   3. Compare both hashes
 *   4. Return validation result
 * 
 * VIVA EXPLANATION:
 * How integrity verification works:
 * 1. When data is saved, we compute hash H1 and store it in MongoDB
 * 2. To verify, backend computes hash H2 of current data
 * 3. If H1 === H2, data is unchanged (Valid)
 * 4. If H1 !== H2, data was modified (Invalid)
 * 5. Backend updates status field in database
 * 
 * @param {string} id - MongoDB _id to verify
 * @returns {Promise<Object>} Verification result from backend
 */
async function verifyIntegrity(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/${id}/verify`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return {
            status: result.status,
            message: result.message
        };
    } catch (error) {
        console.error('Error verifying integrity:', error);
        throw error;
    }
}

/* ============================================================================
   INDEX PAGE (Home) - DATA ENTRY FORM
   ============================================================================ */

/**
 * Initialize index page
 * Sets up event listeners for data entry form
 */
function initIndexPage() {
    const form = document.getElementById('dataForm');
    
    if (!form) return; // Not on index page
    
    form.addEventListener('submit', handleDataSubmit);
}

/**
 * Handle form submission for saving data
 * Sends data to Flask backend via API
 * @param {Event} e - Form submit event
 */
async function handleDataSubmit(e) {
    e.preventDefault(); // Prevent page reload
    
    const dataInput = document.getElementById('dataInput');
    const data = dataInput.value.trim();
    
    // Validate input
    if (!data) {
        showNotification('Please enter some data to save', 'error');
        return;
    }
    
    try {
        // Show loading state
        showNotification('Saving data to MongoDB...', 'info');
        
        // Save to database via API
        // Backend will generate hash and MongoDB _id
        const savedRecord = await saveToStorage(data);
        
        // Show success message
        showNotification('✓ Data secured successfully with SHA-256 hash!', 'success');
        
        // Clear form
        dataInput.value = '';
        
        // Optional: Redirect to records page after 2 seconds
        setTimeout(() => {
            // Uncomment to enable auto-redirect:
            // window.location.href = 'records.html';
        }, 2000);
        
    } catch (error) {
        console.error('Error saving data:', error);
        showNotification('✗ Failed to save data. Check if backend is running!', 'error');
    }
}

/* ============================================================================
   RECORDS PAGE - DISPLAY & VERIFICATION
   ============================================================================ */

/**
 * Initialize records page
 * Loads and displays all records, sets up event listeners
 */
function initRecordsPage() {
    const recordsTable = document.getElementById('recordsTableBody');
    
    if (!recordsTable) return; // Not on records page
    
    // Load and display records
    displayRecords();
    
    // Set up button listeners
    document.getElementById('refreshBtn')?.addEventListener('click', displayRecords);
    document.getElementById('clearAllBtn')?.addEventListener('click', handleClearAll);
}

/**
 * Display all records in the table
 * Fetches records from backend via API
 */
async function displayRecords() {
    const recordsTableBody = document.getElementById('recordsTableBody');
    
    try {
        // Fetch records from API
        const records = await getAllRecords();
        
        // Clear existing rows
        recordsTableBody.innerHTML = '';
        
        // Update statistics
        updateStatistics(records);
        
        // If no records, show empty state
        if (records.length === 0) {
            recordsTableBody.innerHTML = `
                <tr class="no-records">
                    <td colspan="6" class="text-center">
                        <div class="empty-state">
                            <div class="empty-icon">📭</div>
                            <h3>No Records Found</h3>
                            <p>Start by adding some data from the <a href="index.html">Home page</a></p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        // Display each record
        records.forEach(record => {
            const row = createRecordRow(record);
            recordsTableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error displaying records:', error);
        recordsTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">
                    <div class="empty-state">
                        <div class="empty-icon">⚠️</div>
                        <h3>Error Loading Records</h3>
                        <p>Could not connect to backend. Make sure Flask server is running on port 5000.</p>
                    </div>
                </td>
            </tr>
        `;
    }
}

/**
 * Create table row for a record
 * @param {Object} record - Record object from MongoDB
 * @returns {HTMLTableRowElement} Table row element
 */
function createRecordRow(record) {
    const row = document.createElement('tr');
    
    // Determine status badge class and icon
    let badgeClass = 'badge-pending';
    let statusIcon = '';
    if (record.status === STATUS.VALID) {
        badgeClass = 'badge-valid';
        statusIcon = '✓ ';
    }
    if (record.status === STATUS.INVALID) {
        badgeClass = 'badge-invalid';
        statusIcon = '✗ ';
    }
    
    // MongoDB uses _id field
    const recordId = record._id;
    const displayId = recordId.substr(recordId.length - 8); // Last 8 chars of MongoDB ObjectId
    
    // Create row HTML
    row.innerHTML = `
        <td>${displayId}</td>
        <td>
            <div class="data-preview" title="${record.data}">
                ${record.data}
            </div>
        </td>
        <td>
            <div class="hash-preview" title="${record.hash}">
                ${record.hash.substr(0, 16)}...
            </div>
        </td>
        <td class="timestamp">${formatDate(record.timestamp)}</td>
        <td>
            <span class="badge ${badgeClass}">
                ${statusIcon}${record.status}
            </span>
        </td>
        <td>
            <button 
                class="btn btn-success btn-sm" 
                onclick="handleVerify('${recordId}')"
                ${record.status === STATUS.VALID ? 'disabled' : ''}
            >
                ${record.status === STATUS.VALID ? '✓ Verified' : '🔍 Verify'}
            </button>
            <button 
                class="btn btn-danger btn-sm" 
                onclick="handleDelete('${recordId}')"
            >
                🗑️ Delete
            </button>
        </td>
    `;
    
    return row;
}

/**
 * Handle verify button click
 * @param {string} id - Record ID to verify
 */
async function handleVerify(id) {
    try {
        // Show loading notification
        showNotification('� Verifying data integrity with SHA-256...', 'info');
        
        // Call verification API - backend will update status in MongoDB
        const result = await verifyIntegrity(id);
        
        // Refresh display to show updated status
        await displayRecords();
        
        // Show result
        if (result.status === STATUS.VALID) {
            showNotification('✓ Integrity Verified: Data is authentic and unmodified', 'success');
        } else {
            showNotification('⚠️ Alert: Unauthorized data modification detected!', 'error');
        }
        
    } catch (error) {
        console.error('Verification error:', error);
        showNotification('✗ Verification failed. Please try again.', 'error');
    }
}

/**
 * Handle delete button click
 * @param {string} id - MongoDB _id to delete
 */
async function handleDelete(id) {
    if (confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
        try {
            await deleteRecord(id);
            await displayRecords();
            showNotification('✓ Record deleted successfully', 'success');
        } catch (error) {
            console.error('Delete error:', error);
            showNotification('✗ Failed to delete record', 'error');
        }
    }
}

/**
 * Handle clear all button click
 */
async function handleClearAll() {
    if (confirm('⚠️ WARNING: This will permanently delete ALL records. This action cannot be undone. Continue?')) {
        try {
            await clearAllRecords();
            await displayRecords();
            showNotification('✓ All records have been cleared from the system', 'success');
        } catch (error) {
            console.error('Clear all error:', error);
            showNotification('✗ Failed to clear records', 'error');
        }
    }
}

/**
 * Update statistics display
 * @param {Array} records - Array of all records
 */
function updateStatistics(records) {
    const totalRecords = records.length;
    const verifiedRecords = records.filter(r => r.status === STATUS.VALID).length;
    const pendingRecords = records.filter(r => r.status === STATUS.PENDING).length;
    
    // Update DOM elements if they exist
    const totalEl = document.getElementById('totalRecords');
    const verifiedEl = document.getElementById('verifiedRecords');
    const pendingEl = document.getElementById('pendingRecords');
    
    if (totalEl) totalEl.textContent = totalRecords;
    if (verifiedEl) verifiedEl.textContent = verifiedRecords;
    if (pendingEl) pendingEl.textContent = pendingRecords;
}

/* ============================================================================
   INITIALIZATION
   ============================================================================ */

/**
 * Initialize the application when DOM is ready
 * Determines which page we're on and runs appropriate initialization
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize based on current page
    initIndexPage();
    initRecordsPage();
});

/* ============================================================================
   NOTES FOR VIVA PREPARATION
   ============================================================================ 
   
   KEY POINTS TO EXPLAIN:
   
   1. CURRENT IMPLEMENTATION:
      - Using localStorage (browser storage) for demo
      - Generating fake hashes for demonstration
      - All verification marks data as "Valid" (placeholder)
   
   2. BACKEND INTEGRATION (Later):
      - Replace localStorage with REST API calls
      - Backend will use Node.js/Python with Express/Flask
      - Database: MySQL or MongoDB
      - API Endpoints:
        * POST /api/data - Save data and compute hash
        * GET /api/data - Get all records
        * GET /api/data/:id - Get single record
        * PUT /api/data/:id - Update record
        * DELETE /api/data/:id - Delete record
        * POST /api/verify/:id - Verify integrity
   
   3. HASH VERIFICATION LOGIC (Backend):
      - When saving: Compute SHA-256(data) and store it
      - When verifying: 
        a. Get stored hash from database
        b. Compute new hash of current data
        c. Compare both hashes
        d. If same → Valid, If different → Invalid
   
   4. SECURITY CONSIDERATIONS:
      - Hashing is one-way (cannot reverse)
      - Same input always gives same hash
      - Tiny change in input creates completely different hash
      - SHA-256 is cryptographically secure
   
   5. PROJECT SCOPE:
      - Simple web application (not blockchain, not IoT)
      - Demonstrates data integrity verification concept
      - Industry-ready code structure
      - Suitable for BTech final year project
   
   ============================================================================ */
