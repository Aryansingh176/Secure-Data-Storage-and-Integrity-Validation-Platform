# 🔒 Data Integrity Platform

**BTech CSE Final Year Project**  
*A simple, industry-style web application for data storage and integrity verification*

---

## 📋 Project Overview

### High-Level Goal
The Data Integrity Platform allows users to store data and later verify whether the stored data has been modified using a hash-based integrity verification approach.

### Key Features
- ✅ Store text data securely
- ✅ Generate cryptographic hash for each data entry
- ✅ Verify data integrity at any time
- ✅ View all stored records with status tracking
- ✅ Clean, professional, and responsive UI

---

## 🎯 What This Project IS

- ✓ Simple software-only web application
- ✓ Industry-style project suitable for BTech demonstration
- ✓ Hash-based data integrity verification system
- ✓ Clean, well-documented code for viva explanation

## 🚫 What This Project IS NOT

- ✗ NOT a research project
- ✗ NOT a blockchain project
- ✗ NOT an IoT hardware project
- ✗ NO complex cryptography beyond SHA-256 hashing

---

## 🛠️ Technology Stack

### Frontend (Current Phase)
- **HTML5** - Structure and content
- **CSS3** - Styling and responsive design
- **Vanilla JavaScript** - Logic and interactions
- **LocalStorage** - Temporary data storage (demo only)

### Backend (Future Phase)
- **Node.js/Python** - Server-side logic
- **Express/Flask** - Web framework
- **MySQL/MongoDB** - Database
- **Crypto Library** - SHA-256 hash generation

---

## 📁 Project Structure

```
data-integrity-platform/
│
├── index.html              # Home page with data entry form
├── records.html            # Records page with data table
│
├── css/
│   └── style.css          # All styling (organized, responsive)
│
├── js/
│   └── script.js          # All JavaScript logic (well-commented)
│
└── README.md              # This file
```

---

## 🚀 How to Run

### Prerequisites
- Any modern web browser (Chrome, Firefox, Edge, Safari)
- No installation required
- No server needed for Phase 1

### Steps
1. **Download/Clone** the project folder
2. **Open** `index.html` in your web browser
3. **That's it!** The application is ready to use

### Alternative: Using Live Server (Optional)
If you want to run on a local server:
```bash
# If you have Python installed:
python -m http.server 8000

# Then open: http://localhost:8000
```

---

## 📖 How to Use

### 1. Store Data
1. Open `index.html`
2. Enter any text data in the textarea
3. Click "Save Data" button
4. Data is saved with a generated hash

### 2. View Records
1. Navigate to "View Records" from the navbar
2. See all stored data in a table format
3. View ID, Data, Hash, Timestamp, and Status

### 3. Verify Integrity
1. On the records page, click "Verify" button
2. System checks if data has been modified
3. Status updates to "Valid" or "Invalid"

### 4. Manage Records
- **Delete**: Remove individual records
- **Refresh**: Reload the records table
- **Clear All**: Remove all records at once

---

## 🎨 Features

### User Interface
- **Clean Design**: Modern, professional appearance
- **Responsive**: Works on desktop, tablet, and mobile
- **Color-Coded Status**: 
  - 🟡 Yellow = Pending (not verified)
  - 🟢 Green = Valid (integrity confirmed)
  - 🔴 Red = Invalid (data modified)
- **Notifications**: Success/error messages with auto-hide

### Functionality
- Form validation
- Data persistence (localStorage for demo)
- Real-time status updates
- Interactive data table
- Statistics dashboard

---

## 💡 Key Concepts (For Viva)

### 1. Data Integrity
**Definition**: Ensuring data remains unchanged from its original state.

**Why Important**:
- Detect unauthorized modifications
- Ensure data authenticity
- Maintain data trustworthiness

### 2. Cryptographic Hashing (SHA-256)
**What is SHA-256**:
- Secure Hash Algorithm, 256-bit
- Creates unique 64-character hexadecimal string
- One-way function (cannot reverse)

**Properties**:
- **Deterministic**: Same input → Same hash
- **Fixed Size**: Always 256 bits (64 hex chars)
- **Avalanche Effect**: Tiny input change → Completely different hash
- **Collision-Resistant**: Practically impossible to find two inputs with same hash

**Example**:
```
Input: "Hello World"
Hash:  "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"

Input: "Hello World!" (added !)
Hash:  "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
```

### 3. How Integrity Verification Works

**Step 1: Data Storage**
```
1. User enters data: "Important Document"
2. System computes hash: H1 = SHA256("Important Document")
3. Store both data and H1 in database
```

**Step 2: Verification**
```
1. Retrieve data from database
2. Compute new hash: H2 = SHA256(current data)
3. Compare: H1 === H2?
   - YES → Data is Valid (unchanged)
   - NO → Data is Invalid (modified)
```

---

## 🔧 Current Implementation (Phase 1)

### What's Implemented NOW:
✅ Complete frontend UI  
✅ Data entry form  
✅ Records display table  
✅ LocalStorage for temporary storage  
✅ Fake hash generation (demo)  
✅ Placeholder verification (always returns "Valid")  
✅ Responsive design  
✅ Status badges and notifications  

### What's Coming LATER (Phase 2):
⏳ Backend API server  
⏳ Database integration  
⏳ Real SHA-256 hash generation  
⏳ Actual integrity verification  
⏳ User authentication  
⏳ File upload support  
⏳ Export/Import functionality  

---

## 🔌 Backend Integration Plan

### API Endpoints (To Be Implemented)

#### 1. Save Data
```javascript
POST /api/data
Body: { data: "text to save" }
Response: { id, data, hash, timestamp, status }
```

#### 2. Get All Records
```javascript
GET /api/data
Response: [ { id, data, hash, timestamp, status }, ... ]
```

#### 3. Get Single Record
```javascript
GET /api/data/:id
Response: { id, data, hash, timestamp, status }
```

#### 4. Verify Integrity
```javascript
POST /api/verify/:id
Response: { status: "valid" | "invalid", message: "..." }
```

#### 5. Delete Record
```javascript
DELETE /api/data/:id
Response: { success: true, message: "..." }
```

### Database Schema

```sql
CREATE TABLE records (
    id VARCHAR(255) PRIMARY KEY,
    data TEXT NOT NULL,
    hash VARCHAR(64) NOT NULL,
    timestamp BIGINT NOT NULL,
    status ENUM('pending', 'valid', 'invalid') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📝 Code Documentation

### JavaScript Functions Overview

| Function | Purpose | Current | Later |
|----------|---------|---------|-------|
| `saveToStorage()` | Save data | localStorage | POST /api/data |
| `getAllRecords()` | Get records | localStorage | GET /api/data |
| `generateHash()` | Create hash | Fake random | Real SHA-256 |
| `verifyIntegrity()` | Check data | Always valid | Real comparison |
| `displayRecords()` | Show table | ✅ Complete | ✅ Same |
| `showNotification()` | User feedback | ✅ Complete | ✅ Same |

### Important Code Comments
All JavaScript functions include detailed comments explaining:
- What the function does NOW
- What it will do with backend integration
- Example API calls for future reference
- Viva explanation points

---

## 🎓 Viva Preparation Guide

### Questions You Might Face

#### 1. "Explain your project in 2 minutes"
**Answer Template**:
> "My project is a Data Integrity Platform that allows users to store data and verify if it has been modified. When users save data, the system generates a SHA-256 cryptographic hash. Later, they can verify integrity by recomputing the hash and comparing it with the stored hash. Currently, I've completed the frontend with HTML, CSS, and JavaScript. The backend with actual hash verification will be implemented in Phase 2."

#### 2. "What is SHA-256?"
**Answer**: SHA-256 is a cryptographic hash function that creates a unique 256-bit (64 hex character) fingerprint of data. Same input always produces the same hash, but even tiny changes create a completely different hash, making it perfect for detecting data modifications.

#### 3. "How do you verify integrity?"
**Answer**: 
1. When saving: Compute H1 = SHA256(data) and store it
2. When verifying: Compute H2 = SHA256(current_data)
3. Compare: If H1 === H2, data is unchanged (Valid)
4. If H1 !== H2, data was modified (Invalid)

#### 4. "Why use hashing instead of storing original data?"
**Answer**: Hashing is efficient for integrity verification because:
- Fixed size output regardless of input size
- Cannot reverse-engineer original data from hash
- Fast to compute and compare
- Cryptographically secure

#### 5. "What's the difference between hashing and encryption?"
**Answer**:
- **Hashing**: One-way, cannot decrypt, used for integrity
- **Encryption**: Two-way, can decrypt with key, used for confidentiality

#### 6. "Why localStorage? Why not database?"
**Answer**: This is Phase 1 (frontend only). localStorage is used for demonstration purposes. In Phase 2, I'll implement a proper backend with database (MySQL/MongoDB) and API integration.

#### 7. "What challenges did you face?"
**Answer**: 
- Designing a clean, intuitive UI
- Organizing code for easy backend integration
- Ensuring responsive design across devices
- Adding proper comments for code explanation

#### 8. "What's next for this project?"
**Answer**:
- Implement Node.js/Python backend
- Add database (MySQL/MongoDB)
- Real SHA-256 hash generation
- User authentication
- File upload support
- Export/Import functionality

---

## 🔐 Security Considerations

### Current (Frontend Only)
- No real security (demo only)
- Data stored in browser (not secure)
- No encryption or authentication

### Future (With Backend)
- Secure API endpoints
- Database encryption
- User authentication & authorization
- HTTPS communication
- Input validation and sanitization
- Rate limiting
- CSRF protection

---

## 📊 Project Timeline

| Phase | Tasks | Status |
|-------|-------|--------|
| **Phase 1** | Frontend Development | ✅ Complete |
| | - HTML structure | ✅ Done |
| | - CSS styling | ✅ Done |
| | - JavaScript logic | ✅ Done |
| | - Responsive design | ✅ Done |
| **Phase 2** | Backend Development | ⏳ Planned |
| | - API server setup | 📅 Pending |
| | - Database integration | 📅 Pending |
| | - Hash implementation | 📅 Pending |
| | - Testing | 📅 Pending |
| **Phase 3** | Enhancements | 🎯 Future |
| | - User authentication | 🎯 Future |
| | - File support | 🎯 Future |
| | - Export/Import | 🎯 Future |

---

## 🧪 Testing

### Manual Testing Checklist
- [ ] Open index.html in browser
- [ ] Enter data and click "Save Data"
- [ ] Verify success notification appears
- [ ] Navigate to records.html
- [ ] Check if saved data appears in table
- [ ] Click "Verify" button
- [ ] Check status changes to "Valid"
- [ ] Click "Delete" button
- [ ] Verify record is removed
- [ ] Test on mobile device/responsive mode
- [ ] Test form validation (empty input)
- [ ] Test "Clear All" functionality

---

## 🤝 Contributing

This is an academic project, but suggestions are welcome!

---

## 📄 License

This project is created for educational purposes as part of BTech CSE final year curriculum.

---

## 👨‍💻 Author

**BTech CSE Student**  
Final Year Project - 2026

---

## 📞 Support

For questions during viva preparation:
- Review code comments in `script.js`
- Read this README thoroughly
- Understand the "Key Concepts" section
- Practice explaining the hash verification process

---

## ✅ Success Criteria

This project successfully demonstrates:
- ✅ Clean, professional frontend development
- ✅ Understanding of data integrity concepts
- ✅ Knowledge of cryptographic hashing
- ✅ Ability to structure code for future expansion
- ✅ Responsive web design implementation
- ✅ Clear documentation for academic presentation

---

## 🎯 Remember for Viva

1. **Confidence**: You built this, you understand it
2. **Honesty**: Clearly state what's implemented vs planned
3. **Clarity**: Explain concepts simply with examples
4. **Code**: Be ready to walk through any function
5. **Future**: Show enthusiasm for Phase 2 implementation

---

**Good Luck with Your Project Demonstration! 🚀**