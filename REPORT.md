# CSI3344 Assignment 2 Report: Distributed Banking System

**Student Name:** [Your Name]  
**Student ID:** [Your ID]  
**Date:** 29th January 2026  

---

## Executive Summary

This report documents the design and implementation of a three-tier distributed banking system developed for CSI3344 Assignment 2. The system features a distinct Client Tier (Banking Client), Application Tier (BAS Server), and Data Tier (BDB Server), utilizing Pyro5 for Remote Procedure Calls (RPC) and SQLite3 for persistent data storage. Key achievements include a robust implementation of the required 6-tier fee calculation logic, synchronous transaction processing for immediate consistency, and a secure authentication mechanism. The system successfully meets all functional requirements, including valid transfer processing, fee calculation caps, audit logging, and comprehensive error handling.

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Design & Implementation](#design--implementation)
   - [Technology Stack](#technology-stack)
   - [Component Roles](#component-roles)
   - [Communication & Consistency](#communication--consistency)
   - [Fee Calculation Logic](#fee-calculation-logic)
4. [User Manual](#user-manual)
5. [Testing & Verification](#testing--verification)
   - [Test Strategy](#test-strategy)
   - [Test Cases](#test-cases)
6. [Conclusion](#conclusion)

---

## Introduction

Modern banking systems rely on distributed architectures to ensure scalability, reliability, and separation of concerns. This project implements a simplified but architecturally correct banking system that allows users to perform core financial operations—logging in, checking balances, and transferring funds—in a distributed environment.

The scope of this project includes:
- **Phase 1**: Initial development of the Client and Application servers with in-memory storage.
- **Phase 2 (Final)**: Evolution to a full three-tier architecture by introducing a dedicated Database Server (BDB) managing an SQLite database.

---

## System Architecture

The system follows a strict **Three-Tier Architecture**:

1.  **Client Tier (BC Client)**: 
    -   **Role**: Provides the command-line user interface (CLI).
    -   **Responsibility**: Handles user input, displays results, and communicates ONLY with the Application Server. It has no knowledge of the database.
    
2.  **Application Tier (BAS Server)**:
    -   **Role**: The "brain" of the system.
    -   **Responsibility**: hosting business logic, session management, fee calculation, and coordinating data transactions with the Database Server.
    
3.  **Data Tier (BDB Server)**:
    -   **Role**: The "vault".
    -   **Responsibility**: Manages all persistent storage via SQLite. It exposes CRUD operations and atomic transaction methods to the BAS Server.

**Diagram**:
```
[User] <--> [BC Client] <--(Pyro5 RPC)--> [BAS Server] <--(Pyro5 RPC)--> [BDB Server] <--> [SQLite DB]
```

---

## Design & Implementation

### Technology Stack
-   **Language**: Python 3.8+ (Chosen for readability and robust standard library)
-   **Middleware**: Pyro5 (Python Remote Objects) - Chosen for its clean, Pythonic approach to RPC/RMI, making it ideal for educational distributed systems.
-   **Database**: SQLite3 - A lightweight, serverless database engine perfect for embedded persistence without complex setup.

### Communication & Consistency
**Synchronous RPC** was chosen for both BC-BAS and BAS-BDB communications. 
-   **Justification**: Banking operations like "Transfer" are inherently transactional from a user's perspective. When a user sends money, they expect an immediate success or failure confirmation. Asynchronous processing (e.g., message queues) would introduce complexity (eventual consistency) that is unnecessary for this scale and might confuse users regarding their actual account balance.

**Consistency** is maintained via **Atomic Database Transactions**. The `BDB Server` implements `execute_transfer_transaction`, which bundles the debit, credit, and record creation into a single SQL transaction (`BEGIN TRANSACTION` ... `COMMIT/ROLLBACK`). This ensures that money is never lost or created durng a failure.

### Fee Calculation Logic
The system implements the required 6-tier fee structure. The logic is encapsulated in the `BAS Server` to ensure uniform application regardless of client implementation.

**Algorithm**:
1.  Receive transfer amount.
2.  Iterate through `FEE_TIERS` (configured in `config.py`).
3.  Identify the matching range.
4.  Calculate `raw_fee = amount * percentage`.
5.  Apply cap: `final_fee = min(raw_fee, cap)`.
6.  Round to 2 decimal places.

**Example**:
-   Transfer: $8,000 (Tier 2: 0.25%, Cap $20)
-   Calculation: 8000 * 0.0025 = $20.00. Cap is $20.00. Final Fee: $20.00.

---

## User Manual

### Prerequisites
-   Python 3.8 or higher
-   `pip install -r requirements.txt`

### Setup & Running
The system requires three separate terminal windows to simulate the distributed nodes.

1.  **Terminal 1 (Nameserver)**:
    ```bash
    python start_nameserver.py
    ```
    *Wait for "Nameserver started" message.*

2.  **Terminal 2 (Database Server)**:
    ```bash
    python bdb_server.py
    ```
    *Initializing the database and populating mock data.*

3.  **Terminal 3 (Application Server)**:
    ```bash
    python bas_server.py
    ```
    *Connecting to BDB and Nameserver.*

4.  **Terminal 4 (Client)**:
    ```bash
    python bc_client.py
    ```
    *Starts the user interface.*

### Typical Usage Flow
1.  Select **Option 1 (Login)**. Use credentials `john` / `pass123`.
2.  Select **Option 2 (View Balance)** to confirm initial funds ($50,000).
3.  Select **Option 3 (Submit Transfer)**.
    -   Recipient: `1002` (Jane)
    -   Amount: `500`
    -   Confirm "y".
4.  System displays "Transfer Successful" with fee details.
5.  Select **Option 4 (Query Status)** and enter the returned Transfer ID to verify status is `COMPLETED`.

---

## Testing & Verification

Comprehensive testing was conducted using both manual verification and the automated `test_system.py` suite.

### Test Cases Summary

| ID | Test Case | Input | Expected Outcome | Result |
|----|-----------|-------|------------------|--------|
| TC1 | Valid Login | john / pass123 | Success, Token received | PASS |
| TC2 | Invalid Login | john / badpass | Failure message | PASS |
| TC3 | Zero Fee Transfer | $500 (Tier 1) | Fee: $0.00 | PASS |
| TC4 | Capped Fee Transfer | $8,000 (Tier 2) | Fee: $20.00 (Cap applied) | PASS |
| TC5 | Insufficient Funds | Transfer > Balance | Error: "Insufficient balance" | PASS |
| TC6 | Self Transfer | Recipient = Sender | Error: "Own account" | PASS |
| TC7 | Persistence | Restart Servers | Data remains in `banking_system.db` | PASS |

### Evidence
The `export_database.py` utility can be run to dump the current state of `users`, `accounts`, and `transfers` tables to CSV files, providing concrete evidence of successful transactions and persistence.

---

## Conclusion

The Three-Tier Distributed Banking System successfully meets over 100% of the functional requirements. By strictly separating concerns between the Client, Application, and Database tiers, the system achieves modularity and maintainability. The use of Pyro5 allowed for clean, Pythonic RPC implementation, while SQLite ensured reliable data persistence. The solution handles edge cases such as insufficient funds and fee caps gracefully, providing a robust "production-ready" educational prototype.

---
**References**
1. Pyro5 Documentation: https://pyro5.readthedocs.io/
2. Python SQLite3 Documentation: https://docs.python.org/3/library/sqlite3.html
