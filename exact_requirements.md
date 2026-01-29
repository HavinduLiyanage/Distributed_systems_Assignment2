# CSI3344 Assignment 2 - EXACT REQUIREMENTS BREAKDOWN

## SYSTEM FUNCTIONALITIES (What the App MUST Do)

### 1. AUTHENTICATION & SESSION MANAGEMENT (Section A)

#### BC Client Must:
- ✅ Allow user to enter username/password
- ✅ Send login request to BAS server
- ✅ Receive and store authentication token on success
- ✅ Handle login failure (reject and display error)
- ✅ Use token for all subsequent API calls

#### BAS Server Must:
- ✅ Accept login requests
- ✅ Validate credentials (mock validation - hardcoded users)
- ✅ Generate session token / auth token on success
- ✅ Return token to client OR reject with error
- ✅ Log all authentication attempts (success AND failure)
- ✅ Validate token on every subsequent request

#### Design Questions to Answer:
- WHERE is authentication handled? (BAS server)
- HOW is token used in subsequent APIs? (sent with every request)
- HOW is token validated? (check against active sessions)

---

### 2. BALANCE QUERY (Section B)

#### BC Client Must:
- ✅ Send balance query request with user's token
- ✅ Display returned balance to user

#### BAS Server Must:
- ✅ Authenticate the request (validate token)
- ✅ Read current balance from BDB server (Phase 2) or in-memory (Phase 1)
- ✅ Return balance to client

#### Design Questions to Answer:
- WHY is this synchronous? (Explain: immediate response needed, simple query, no processing delay)

---

### 3. SUBMIT TRANSFER REQUEST (Section C) - MOST COMPLEX

#### BC Client Must Allow User to Provide:
- ✅ Recipient account ID (or payee ID)
- ✅ Transfer amount
- ✅ Optional reference message

#### BC Client Must:
- ✅ Validate inputs locally (basic checks)
- ✅ Send transfer request to BAS with token
- ✅ Receive and display outcome to user
  - Either: CONFIRMED completion
  - Or: Trackable request ID
- ✅ Show meaningful outcome (not just "OK")

#### BAS Server Must Enforce:

##### **AUTHENTICATION:**
- ✅ Validate token
- ✅ Identify requesting user
- ✅ Authorize user to perform transfer

##### **VALIDATION:** (Input Checks Required)
- ✅ Recipient account exists
- ✅ Recipient ≠ Sender (no self-transfers)
- ✅ Amount > 0
- ✅ Amount has max 2 decimal places
- ✅ Reference message ≤ 200 characters (if provided)
- ✅ Calculate fee based on amount
- ✅ Check: Sender balance ≥ (amount + fee)
- ✅ Report errors clearly if validation fails

##### **FEE POLICY:** (Fee Calculation Logic)
```
Transfer Amount Range      | Percentage | Per-Transfer Cap
--------------------------+------------+-----------------
$0.00 - $2,000.00         | 0%         | $0 (Free tier)
$2,000.01 - $10,000.00    | 0.25%      | $20.00
$10,000.01 - $20,000.00   | 0.20%      | $25.00
$20,000.01 - $50,000.00   | 0.125%     | $40.00
$50,000.01 - $100,000.00  | 0.08%      | $50.00
$100,000.01 and above     | 0.05%      | $100.00
```

**Fee Calculation Steps:**
1. Identify tier based on transfer amount
2. Calculate: fee = amount × percentage
3. Apply cap: fee = min(calculated_fee, cap)
4. Round to 2 decimal places

**CRITICAL RULES:**
- ✅ All monetary values MUST be rounded to 2 decimal places
- ✅ Cap = MAXIMUM fee for a SINGLE transfer
- ✅ Fee is PER TRANSFER (not cumulative)

##### **CONSISTENCY:** (Must Ensure)
- ✅ Balances remain consistent under failures
- ✅ Balances remain consistent under concurrent requests
- ✅ Transfer records remain consistent
- ✅ No partial updates (atomicity)
- ✅ Handle race conditions

##### **PROCESSING MODE:**
Must decide and justify:
- OPTION A: Synchronous (transfer completes immediately, funds move instantly)
- OPTION B: Asynchronous (transfer queued for settlement, PENDING status initially)

Must explain WHY chosen approach is appropriate.

##### **PERSISTENCE & AUDIT:**
Must store in BDB for traceability:
- ✅ Transfer ID (unique identifier)
- ✅ Sender account ID
- ✅ Recipient account ID
- ✅ Transfer amount
- ✅ Fee charged
- ✅ Total deducted (amount + fee)
- ✅ Status (PENDING/COMPLETED/FAILED)
- ✅ Reference message (if provided)
- ✅ Timestamp (when created)
- ✅ Completion timestamp (when completed)
- ✅ Allow later queries by transfer ID

---

### 4. TRANSFER STATUS QUERY (Section D)

#### BC Client Must:
- ✅ Accept transfer ID from user
- ✅ Send query request to BAS with token and transfer ID
- ✅ Display transfer status and details

#### BAS Server Must:
- ✅ Authenticate request
- ✅ Query transfer by ID from BDB
- ✅ Return status with details

#### Status Values (MUST Support):
- **PENDING**: Transfer accepted but not settled yet (if async processing)
- **COMPLETED**: Funds moved + fee charged successfully
- **FAILED**: Transfer failed (insufficient funds, invalid recipient, server error)
  - IMPORTANT: If FAILED, no money should be deducted

---

### 5. PERSISTENCE & AUDIT (Section E)

#### Requirements:
- ✅ Every transfer MUST be persisted with necessary information
- ✅ Use mock data (small set of mock users/accounts in BDB)
- ✅ No integration with real banks
- ✅ Focus on:
  - Clear tier separation
  - Authenticated APIs
  - Persistence
  - Correct fee logic

---

## SYSTEM ARCHITECTURE REQUIREMENTS

### Three-Tier Structure (MANDATORY)

#### **Tier 1: BC Client (Banking Client)**
- Used by customers
- Functions: sign in, query balance, submit transfer requests
- **CANNOT** access BDB server directly
- **ONLY** communicates with BAS server

#### **Tier 2: BAS Server (Bank Application Server)**
- Provides authenticated APIs
- Implements business rules (fee calculation, validation, state transitions)
- Coordinates transfer processing
- **ONLY** tier that communicates with BDB server
- Acts as intermediary between client and database

#### **Tier 3: BDB Server (Bank Database Server)**
- Stores persistent data:
  - User accounts
  - Balances
  - Transfer records
  - Audit logs
  - Hashed credentials (or mock secrets)
  - Fee records
- **ONLY** accessible by BAS server (NOT by client)

### Communication Requirements:
- ✅ May be synchronous (e.g., login, view balance)
- ✅ May be asynchronous (e.g., notification)
- ✅ MUST justify design choice per operation

---

## IMPLEMENTATION PHASES

### Phase 1: Two-Tier (REQUIRED FIRST)

#### Scope:
- ✅ BC Client + BAS Server ONLY
- ✅ NO separate database tier (BDB)
- ✅ System state maintained IN-MEMORY on BAS server (arrays/dictionaries)

#### Must Support:
- ✅ Sign-in / authentication
- ✅ Balance query
- ✅ Transfer request submission
- ✅ Transfer fee computation using fee table (with caps)

#### Communication Style (Choose ONE):
**Option (i): Synchronous (RMI/RPC-style)**
- Use request/response pattern
- Allowed libraries: **Pyro5 OR gRPC** (and dependencies)
- ONLY Python standard library beyond these

**Option (ii): Asynchronous or Hybrid**
- Use asynchronous communication
- May use third-party libraries/packages
- MUST clearly define message/event flow
- MUST explain behavior under failures (retry, duplicate requests)

---

### Phase 2: Three-Tier (REQUIRED AFTER PHASE 1)

#### Sub-task 1: Testing (REQUIRED)
- ✅ Extensively test Phase-1 system
- ✅ Test various inputs and edge cases:
  - Boundary values of fee tiers
  - Insufficient funds
  - Invalid recipient
  - Repeated requests

#### Sub-task 2: Add BDB Server (REQUIRED)
- ✅ Create BDB server as database tier
- ✅ Extend Phase-1 system for persistent storage
- ✅ MUST use **SQLite** for database implementation
- ✅ SQLite database managed ONLY by BDB server program
- ✅ BC client and BAS server MUST NOT access database directly

#### Communication Rules:
- ✅ BC client has NO direct access to BDB server
- ✅ BAS server ↔ BDB server may use RMI/RPC (or selected mechanism)
- ✅ MUST justify the choice

#### Testing Requirements:
- ✅ Manually create mock data for AT LEAST 2 users
- ✅ Store mock data in database
- ✅ Export database tables as .xlsx/.csv
- ✅ Submit as supporting documents

#### Design Requirements:
- ✅ Explain how design maintains correctness under failures
  - Partial updates
  - Retries
  - Duplicate requests

---

## TEST CASES (EXPLICITLY MENTIONED IN ASSIGNMENT)

### From Assignment Document:

#### 1. **Boundary Values of Fee Tiers** (CRITICAL)
Must test EXACT boundary amounts:
- ✅ $2,000.00 (should be 0% fee - FREE)
- ✅ $2,000.01 (should be 0.25% fee - ENTRY tier)
- ✅ $10,000.00 (should be 0.25% fee, max $20 cap)
- ✅ $10,000.01 (should be 0.20% fee - MID tier)
- ✅ $20,000.00 (should be 0.20% fee, max $25 cap)
- ✅ $20,000.01 (should be 0.125% fee - UPPER-MID tier)
- ✅ $50,000.00 (should be 0.125% fee, max $40 cap)
- ✅ $50,000.01 (should be 0.08% fee - HIGH tier)
- ✅ $100,000.00 (should be 0.08% fee, max $50 cap)
- ✅ $100,000.01 (should be 0.05% fee - TOP tier)

#### 2. **Insufficient Funds**
- ✅ Transfer amount + fee > account balance
- ✅ Should return FAILED status
- ✅ Should NOT deduct any money

#### 3. **Invalid Recipient**
- ✅ Recipient account ID does not exist
- ✅ Should return FAILED status
- ✅ Should NOT deduct any money

#### 4. **Repeated Requests**
- ✅ Same transfer submitted multiple times
- ✅ Must handle duplicate requests properly
- ✅ Should NOT process same transfer twice

---

## ADDITIONAL TEST CASES (IMPLIED BY REQUIREMENTS)

### Input Validation Tests:

#### 5. **Correct Input**
- ✅ Valid recipient
- ✅ Valid amount
- ✅ Sufficient balance
- ✅ Should complete successfully

#### 6. **Incorrect Input - Negative Amount**
- ✅ Amount = -100
- ✅ Should reject immediately
- ✅ Return validation error

#### 7. **Incorrect Input - Zero Amount**
- ✅ Amount = 0
- ✅ Should reject
- ✅ Return validation error

#### 8. **Incorrect Input - Too Many Decimals**
- ✅ Amount = 100.123 (3 decimal places)
- ✅ Should reject or round
- ✅ Handle appropriately

#### 9. **Self Transfer**
- ✅ Sender account = Recipient account
- ✅ Should reject
- ✅ Return validation error

#### 10. **Invalid Session Token**
- ✅ Expired token
- ✅ Non-existent token
- ✅ Tampered token
- ✅ Should reject with authentication error

#### 11. **Missing Required Fields**
- ✅ No recipient specified
- ✅ No amount specified
- ✅ Should return validation error

#### 12. **Reference Message - Max Length**
- ✅ Reference > 200 characters
- ✅ Should reject or truncate
- ✅ Handle appropriately

#### 13. **Reference Message - Optional**
- ✅ Transfer without reference
- ✅ Should succeed
- ✅ Reference stored as NULL/empty

### Fee Calculation Tests:

#### 14. **Fee Tier - Free (0% tier)**
- ✅ Amount = $500
- ✅ Expected fee = $0.00
- ✅ Total deducted = $500.00

#### 15. **Fee Tier - Entry (0.25%, cap $20)**
- ✅ Amount = $5,000
- ✅ Expected fee = $12.50
- ✅ Total deducted = $5,012.50

#### 16. **Fee Cap Enforcement - Entry Tier**
- ✅ Amount = $10,000
- ✅ Calculated fee = $25.00
- ✅ Cap = $20.00
- ✅ Actual fee = $20.00 (capped)
- ✅ Total deducted = $10,020.00

#### 17. **Fee Tier - Mid (0.20%, cap $25)**
- ✅ Amount = $15,000
- ✅ Expected fee = $25.00 (capped)
- ✅ Total deducted = $15,025.00

#### 18. **Fee Tier - Upper-Mid (0.125%, cap $40)**
- ✅ Amount = $35,000
- ✅ Calculated fee = $43.75
- ✅ Cap = $40.00
- ✅ Actual fee = $40.00 (capped)
- ✅ Total deducted = $35,040.00

#### 19. **Fee Tier - High (0.08%, cap $50)**
- ✅ Amount = $75,000
- ✅ Calculated fee = $60.00
- ✅ Cap = $50.00
- ✅ Actual fee = $50.00 (capped)
- ✅ Total deducted = $75,050.00

#### 20. **Fee Tier - Top (0.05%, cap $100)**
- ✅ Amount = $150,000
- ✅ Calculated fee = $75.00
- ✅ Cap = $100.00
- ✅ Actual fee = $75.00
- ✅ Total deducted = $150,075.00

#### 21. **Fee Cap Enforcement - Top Tier**
- ✅ Amount = $250,000
- ✅ Calculated fee = $125.00
- ✅ Cap = $100.00
- ✅ Actual fee = $100.00 (capped)
- ✅ Total deducted = $250,100.00

#### 22. **Fee Rounding**
- ✅ Amount = $3,333.33
- ✅ Calculated fee = 3333.33 × 0.0025 = 8.333325
- ✅ Actual fee = $8.33 (rounded to 2 decimals)
- ✅ Total deducted = $3,341.66

### System Behavior Tests:

#### 23. **Balance After Transfer**
- ✅ Initial balance = $10,000
- ✅ Transfer $2,500 (fee = $1.25)
- ✅ New balance = $7,498.75
- ✅ Verify balance updated correctly

#### 24. **Recipient Balance After Transfer**
- ✅ Recipient initial balance = $5,000
- ✅ Receives $2,500
- ✅ Recipient new balance = $7,500.00
- ✅ Note: Recipient does NOT pay fee

#### 25. **Transfer Record Persistence**
- ✅ Submit transfer
- ✅ Query by transfer ID
- ✅ Verify all details stored correctly

#### 26. **Transfer History Query**
- ✅ Submit multiple transfers
- ✅ Query user's transfer history
- ✅ Verify all transfers listed

#### 27. **Concurrent Transfers - Same User**
- ✅ Two transfers submitted simultaneously
- ✅ Balance = $10,000
- ✅ Transfer 1: $6,000
- ✅ Transfer 2: $5,000
- ✅ One should succeed, one should fail (insufficient funds)
- ✅ No race condition allowing both

#### 28. **Concurrent Transfers - Different Users**
- ✅ User A transfers to User B
- ✅ User B transfers to User A
- ✅ Both submitted simultaneously
- ✅ Both should succeed if balances sufficient
- ✅ No deadlock

### Failure & Recovery Tests:

#### 29. **Partial Update Prevention**
- ✅ If sender deducted but recipient not credited
- ✅ Should rollback entire transaction
- ✅ Sender balance restored

#### 30. **Server Restart**
- ✅ Perform transfers
- ✅ Restart BDB server
- ✅ Verify all data persisted
- ✅ Verify balances correct

#### 31. **Session Expiry**
- ✅ Login and get token
- ✅ Wait for token to expire (or force expiry)
- ✅ Attempt operation with expired token
- ✅ Should reject with authentication error

### Menu & UI Tests:

#### 32. **All Menu Options Function**
- ✅ Login option works
- ✅ Balance query option works
- ✅ Submit transfer option works
- ✅ View transfer status option works
- ✅ View transfer history option works (if implemented)
- ✅ Logout option works

#### 33. **Safe Program Exit**
- ✅ Can exit client safely after login
- ✅ Can exit client safely after transfer
- ✅ Can exit client safely from any menu
- ✅ No hanging processes

#### 34. **Error Message Quality**
- ✅ Clear error messages displayed
- ✅ User understands what went wrong
- ✅ User knows how to fix issue

#### 35. **Formatting Check**
- ✅ Money amounts display with 2 decimals
- ✅ Money amounts display with $ sign
- ✅ Dates formatted properly
- ✅ Menus aligned and readable

---

## REPORT REQUIREMENTS

### User Manual Must Include:

#### Application Setting-Up Steps:
- ✅ Prerequisites (Python version, etc.)
- ✅ Installation instructions
- ✅ How to install on MULTIPLE computers (distributed)
- ✅ How to run each component
- ✅ Startup sequence

#### Usage Steps:
- ✅ How to start servers
- ✅ How to start client
- ✅ How to login
- ✅ How to perform each operation
- ✅ Screenshots of usage

#### Test Instructions:
- ✅ How tutor can test the code
- ✅ Where to find test data
- ✅ Expected outputs for test cases

### Test Cases Documentation:

Must answer:
- ✅ How does code react to correct input?
- ✅ How does code react to incorrect input?
- ✅ Can you exit program safely after testing?
- ✅ Do test cases cover all primary functions?
- ✅ Do all menu options function properly?
- ✅ Is it formatted well enough?

---

## BASIC REQUIREMENTS (MUST MEET)

### Application/System:
- ✅ Must include ALL required components (BC, BAS, BDB)
- ✅ Observable behaviors consistent with requirements
- ✅ Necessary error handling mechanisms
- ✅ MUST be implemented using **Python**
- ✅ MUST be runnable off-the-shelf (from OS shell with Python installed)
- ✅ NO IDE required to run

### Report:
- ✅ Well structured
- ✅ Informative
- ✅ Does NOT contain code (code in separate files)
- ✅ All code files included separately in .zip
- ✅ Max 4,000 words (excluding references)
- ✅ Max 12 pages
- ✅ Font: Times New Roman, 12pt minimum
- ✅ Must declare AI tool usage

---

## MARKING BREAKDOWN

- **Phase 1**: 16 marks
- **Phase 2**: 16 marks
- **Report**: 18 marks
- **Total**: 50 marks (50% of unit grade)

### Report Sections (18 marks):
- ✅ Executive summary: abstraction & vital information
- ✅ Thought/idea organization: conjunctions & cohesion
- ✅ Clarity: discussion flow and integrity
- ✅ Citations to References
- ✅ User manual
- ✅ Test cases
- ✅ Conclusions achieved
- ✅ References
- ✅ Quality of report: Format requirements met
- ✅ Report length: Not too long, not too short

---

## EDGE CASES SUMMARY

### Critical Edge Cases (MUST Handle):

1. **Fee Tier Boundaries** (Most Critical)
   - Exactly at tier change amounts
   - Just above tier change amounts
   - Just below tier change amounts

2. **Insufficient Funds**
   - Balance exactly equals amount (but fee makes it insufficient)
   - Balance slightly less than amount + fee

3. **Concurrent Operations**
   - Multiple transfers from same account simultaneously
   - Race conditions on balance updates

4. **Invalid/Missing Data**
   - NULL values
   - Empty strings
   - Special characters in reference
   - Very long reference messages

5. **Authentication**
   - Expired tokens
   - Reused tokens after logout
   - Invalid token formats

6. **Database Operations**
   - Connection failures
   - Transaction rollbacks
   - Duplicate keys

7. **Large Amounts**
   - Maximum representable amounts
   - Precision issues with very large numbers

8. **Repeated Operations**
   - Duplicate transfer submissions
   - Idempotency testing

---

## DESIGN DECISIONS THAT MUST BE JUSTIFIED

1. **Why is authentication handled in BAS server?**
2. **Why are sessions stored where they are stored?**
3. **Why is balance query synchronous?**
4. **Why is transfer processing synchronous/asynchronous?**
5. **How does fee calculation handle edge cases?**
6. **How does system ensure consistency under failures?**
7. **How does system handle concurrent requests?**
8. **What is stored in database and why?**
9. **Why was Pyro5/gRPC chosen?**
10. **Why was three-tier architecture beneficial?**

---

## CRITICAL SUCCESS FACTORS

### To Get Maximum Marks:

1. ✅ **ALL functionalities working perfectly**
2. ✅ **Fee calculation PERFECT** (all boundary tests pass)
3. ✅ **Comprehensive error handling**
4. ✅ **Clear tier separation** (no direct DB access from client/BAS)
5. ✅ **Extensive testing documented**
6. ✅ **Professional user manual** (tutor can install and run easily)
7. ✅ **All test cases documented with results**
8. ✅ **Database exports provided**
9. ✅ **Design justifications clear and convincing**
10. ✅ **Code runs off-the-shelf** (no IDE needed)
11. ✅ **Report well-structured** and within limits

---

END OF EXACT REQUIREMENTS BREAKDOWN