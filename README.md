# THREE-TIER Distributed Banking System

**CSI3344 Assignment 2 - Distributed Systems**  
**Summer School 2026**

---

## Project Overview

A complete **THREE-TIER distributed banking system** implementing:
- **Client Tier**: Banking Client (BC) - Customer interface
- **Application Tier**: Bank Application Server (BAS) - Business logic & fee calculation
- **Data Tier**: Bank Database Server (BDB) - SQLite persistence

**Technology Stack**:
- Python 3.8+
- Pyro5 (RPC/RMI framework)
- SQLite3 (database)

---

## System Architecture

```
┌─────────────────┐
│   BC Client     │  (Banking Client - User Interface)
│ client/bc_client.py│
└────────┬────────┘
         │ Pyro5 RPC
         ▼
┌─────────────────┐
│   BAS Server    │  (Bank Application Server - Business Logic)
│ server/bas_server.py│
└────────┬────────┘
         │ Pyro5 RPC
         ▼
┌─────────────────┐
│   BDB Server    │  (Bank Database Server - Data Persistence)
│ server/bdb_server.py│
└─────────────────┘
```

**Important**: BC Client has NO direct access to BDB Server. All data flows through BAS Server.

---

## Features

### Core Banking Operations
-  User authentication with session tokens
-  Balance queries
-  Money transfers with sophisticated fee calculation
-  Transfer status tracking (PENDING, COMPLETED, FAILED)
-  Audit logging

### Fee Structure (6 Tiers)
| Transfer Amount | Fee Percentage | Per-Transfer Cap |
|----------------|----------------|------------------|
| $0 - $2,000 | 0% | Free |
| $2,000.01 - $10,000 | 0.25% | $20.00 |
| $10,000.01 - $20,000 | 0.20% | $25.00 |
| $20,000.01 - $50,000 | 0.125% | $40.00 |
| $50,000.01 - $100,000 | 0.08% | $50.00 |
| $100,000.01+ | 0.05% | $100.00 |

---

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Installation
```bash
python -c "import Pyro5; print('Pyro5 installed successfully')"
```

---

## Running the System (Simplified)

You can launch the entire system (all servers and the client) with a single command. This will automatically open each component in its own terminal window.

### Windows (Recommended)
Double-click the `start_all.bat` file in the root directory.

### Any Platform
Run the following command from the project root:
```bash
python run_all.py

---

## Mock User Credentials

Use these credentials to test the system:

| Username | Password | Initial Balance |
|----------|----------|----------------|
| john | pass123 | $50,000.00 |
| jane | pass456 | $75,000.00 |

---

## Usage Guide

### 1. Login
```
Select option: 1
Enter username: john
Enter password: pass123
```
**Result**: Login successful with session token

---

### 2. View Balance
```
Select option: 2
```
**Result**: Displays current account balance

---

### 3. Submit Transfer
```
Select option: 3
Enter recipient account ID: 1002
Enter transfer amount: 5000
Enter reference (optional): Test transfer
```
**Result**: Transfer processed with fee calculated and displayed

---

### 4. Query Transfer Status
```
Select option: 4
Enter transfer ID: 1
```
**Result**: Displays transfer status and details

---

## Testing

### Run Automated Tests
```bash
python tests/test_system.py
```
This tests:
- Authentication flows
- Balance queries
- Fee calculations (all 6 tiers)
- Transfer validations
- Error handling
- Database persistence

### Export Database for Verification
```bash
python utils/export_database.py
```
Creates CSV files in the root: `users.csv`, `accounts.csv`, `transfers.csv`, `sessions.csv`, `audit_logs.csv`

---

## Project Structure

```
distributed-banking-system/
├── client/                   # Client-tier source code
│   └── bc_client.py
├── server/                   # Server-tier source code
│   ├── bas_server.py
│   ├── bdb_server.py
│   └── start_nameserver.py
├── data/                     # Persistent storage
│   └── banking_system.db
├── docs/                     # Project documentation
├── tests/                    # Automated test suites
├── utils/                    # Utility scripts
│   └── export_database.py
├── config.py                 # Shared configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## System Behavior

### Synchronous Communication
All operations use **synchronous RPC** (Pyro5) for simplicity and immediate feedback:
- BC Client → BAS Server: Request/Response
- BAS Server → BDB Server: Request/Response

**Justification**: Users expect instant confirmation for banking operations. Synchronous communication ensures immediate consistency and simpler error handling.

### Transfer Processing
Transfers are executed as **atomic database transactions**:
1. Validate sender has sufficient balance (amount + fee)
2. Deduct (amount + fee) from sender
3. Add amount to recipient
4. Create transfer record with COMPLETED status
5. Rollback entire transaction on any failure

---

## Error Handling

The system handles:
-  Invalid credentials
-  Insufficient funds
-  Invalid recipient accounts
-  Negative or zero transfer amounts
-  Database connection errors
-  Network timeouts
-  Concurrent access conflicts

---

## Development Phases

### Phase 1: Two-Tier (BC Client ↔ BAS Server)
- In-memory data storage
- Basic RPC communication
- Core business logic

### Phase 2: Three-Tier (BC Client ↔ BAS Server ↔ BDB Server)
- SQLite database persistence
- Database transactions
- Audit logging
- Transfer status tracking

**Note**: Final submission includes Phase 2 (three-tier) implementation.

---

## Troubleshooting

### "Cannot locate nameserver"
- Ensure `start_nameserver.py` is running
- Check `config.py` has correct host/port

### "Cannot connect to BAS/BDB server"
- Start servers in order: Nameserver → BDB → BAS → BC Client
- Ensure all servers registered successfully

### Database errors
- Delete `banking_system.db` and restart BDB server to reinitialize

---

## Assignment Requirements Met

 Three-tier architecture implemented  
 Pyro5 RPC communication  
 SQLite database managed by BDB server only  
 Authenticated APIs with session tokens  
 6-tier fee calculation with caps  
 Transfer validation and error handling  
 Database transactions for consistency  
 Audit logging  
 Mock data for testing  
 Runnable from command line (no IDE required)  
 Comprehensive test coverage  
 Complete documentation  

---

## Author
Student ID: [Your ID]  
Unit: CSI3344 Distributed Systems  
Assignment: Assignment 2 - Three-Tier Banking System  
