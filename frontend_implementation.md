# Frontend Implementation Instructions

## Base Configuration

- **API Base URL**: `http://localhost:8000/api/v1` (or your production URL)
- **Content-Type**: `application/json`

## Authentication

All protected endpoints require the `Authorization` header with a Bearer token.

```
Authorization: Bearer <access_token>
```

When the token expires (401 Unauthorized), use the refresh token (if implemented) or redirect the user to login.

## Generic API Response Structure

All API responses (except 204 No Content) follow this generic structure:

```typescript
interface APIResponse<T> {
  message: string;
  data: T;
}
```

## Error Handling

Errors return standard HTTP status codes (400, 401, 403, 404, 500) with a JSON body:

```typescript
interface ErrorResponse {
  detail: string; 
}
```

For validation errors (422 Unprocessable Entity), Pydantic returns details about which fields failed.

---

## Data Models (TypeScript Interfaces)

### User

```typescript
interface User {
  id: string; // UUID
  email: string;
  first_name: string;
  last_name: string;
  phone_number?: string | null;
  avatar_url?: string | null;
  role: "user" | "admin";
  is_verified: boolean;
  referral_code: string;
  social_provider?: "google" | "apple" | null;
  social_id?: string | null;
  created_at: string; // ISO Date
}

interface UserUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  password?: string;
  phone_number?: string;
  avatar_url?: string;
}
```

### Wallet & Financials

```typescript
interface Wallet {
  id: string;
  balance: number; // Stored as Decimal in backend, careful with float precision
  currency: string; // Default "NGN"
}

interface BankAccount {
  id: string;
  bank_name: string;
  account_number: string;
  account_name: string;
  bank_code: string;
  is_primary: boolean;
  status: "pending" | "verified";
}

interface Card {
  id: string;
  last4: string;
  brand: string; // e.g. "Visa", "Mastercard"
  expiry_month: number;
  expiry_year: number;
  // auth_token and signature are hidden
}
```

### Circles (Ajo)

```typescript
type CircleFrequency = "weekly" | "monthly";
type CircleStatus = "pending" | "active" | "completed" | "cancelled";
type PayoutPreference = "random" | "fixed";
type CircleRole = "host" | "member";

interface Circle {
  id: string;
  name: string;
  description?: string | null;
  amount: number; // In kobo/cents
  frequency: CircleFrequency;
  cycle_start_date?: string | null;
  target_members?: number | null;
  payout_preference: PayoutPreference;
  status: CircleStatus;
  invite_code: string;
}

interface CircleCreateInput {
  name: string;
  description?: string;
  amount: number;
  frequency: CircleFrequency;
  target_members?: number;
  payout_preference?: PayoutPreference;
}

interface CircleMember {
  circle_id: string;
  user_id: string;
  role: CircleRole;
  payout_order: number;
  // join_date is not always exposed in read schema but exists in DB
}
```

### Chat

```typescript
interface ChatMessage {
  id: string;
  circle_id: string;
  user_id: string;
  content: string;
  timestamp: string; // ISO Date
  message_type: "text" | "image" | "file";
  attachment_url?: string | null;
  sender_name?: string | null;
}
```

### Notifications

```typescript
interface Notification {
  id: string;
  title: string;
  body: string;
  type: "action_required" | "info" | "success";
  is_read: boolean;
  action_url?: string | null;
  priority: "normal" | "high";
  created_at?: string | null;
}
```

### Transactions

```typescript
type TransactionType = "deposit" | "withdrawal" | "transfer" | "contribution" | "payout";
type TransactionStatus = "pending" | "success" | "failed";

interface Transaction {
  id: string;
  wallet_id: string;
  amount: number; // In kobo/cents
  type: TransactionType;
  status: TransactionStatus;
  reference: string;
  provider_reference?: string | null;
  description: string;
  txn_metadata?: Record<string, any>;
  created_at: string; // ISO Date
}
```

---

## Endpoints

### 1. Authentication

| Method | Endpoint | Description | Body | Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/signup` | Register new user | `UserCreate` | `User` |
| `POST` | `/auth/login` | Login with email/pass | `{email, password}` | `Token` |
| `POST` | `/auth/social/google` | Google Login | `{token}` | `Token` |
| `POST` | `/auth/social/apple` | Apple Login | `{token, first_name?, last_name?}` | `Token` |
| `POST` | `/auth/verify-email` | Verify Email | Query: `?token=...` | `{verified: boolean}` |

**Token Structure**:
```typescript
interface Token {
  access_token: string;
  token_type: "bearer";
}
```

### 2. User Profile

| Method | Endpoint | Description | Body | Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/users/me` | Get my profile | - | `User` |
| `PUT` | `/users/me` | Update profile | `UserUpdate` | `User` |

### 3. Wallet & Bank

| Method | Endpoint | Description | Body | Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/wallet` | Get wallet balance | - | `Wallet` |
| `POST` | `/wallet/deposit` | Deposit funds | - | `{user: string}` (Mock) |
| `POST` | `/wallet/withdraw` | Withdraw funds | - | `{user: string}` (Mock) |
| `GET` | `/wallet/banks` | List bank accounts | - | `BankAccount[]` |
| `POST` | `/wallet/banks` | Link bank account | `{bank_name, account_number, ...}` | `BankAccount` |
| `GET` | `/wallet/cards` | List cards | - | `Card[]` |
| `POST` | `/wallet/cards` | Link card | `{last4, brand, ...}` | `Card` |

### 4. Circles

| Method | Endpoint | Description | Body | Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/circles` | Create Circle | `CircleCreateInput` | `Circle` |
| `GET` | `/circles` | List my circles | - | `Circle[]` |
| `GET` | `/circles/{id}` | Get Circle details | - | `Circle` |
| `PATCH` | `/circles/{id}` | Update Circle (Host) | `CircleUpdate` | `Circle` |
| `POST` | `/circles/join` | Join via code | Query: `?invite_code=...` | `{circle_id: string}` |
| `POST` | `/circles/{id}/start` | Start Circle (Host) | - | `Circle` |
| `GET` | `/circles/{id}/members` | List Members | - | `CircleMember[]` |
| `PUT` | `/circles/{id}/members/order`| Reorder Members | `{member_ids: string[]}` | `CircleMember[]` |
| `DELETE`| `/circles/{id}/members/{mid}`| Remove Member | - | `{member_id: string}` |
| `POST` | `/circles/{id}/contribute`| Contribute for cycle | - | `{contribution_id, cycle, ...}` |

### 5. Chat

| Method | Endpoint | Description | Body | Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/chat/{circle_id}` | Get messages | Query: `?before=...` | `ChatMessage[]` |
| `POST` | `/chat/{circle_id}` | Send message | `{content, attachment_url?}` | `ChatMessage` |

### 6. Notifications

| Method | Endpoint | Description | Body | Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/notifications` | List notifications | Query: `?skip=0&limit=50` | `Notification[]` |
| `POST` | `/notifications/{id}/read` | Mark as read | - | `{}` |

### 7. Transactions

| Method | Endpoint | Description | Body | Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/transactions` | List user transactions | Query: `?skip=0&limit=50` | `Transaction[]` |
| `POST` | `/transactions/deposit` |  Initiate Deposit | `{amount: number}` | `{authorization_url, access_code, reference}` |
