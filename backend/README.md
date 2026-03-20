# TenderMatch API Backend (Phase 1)

This is the backend API for **TenderMatch**, built with **FastAPI** and **MongoDB**. It handles user authentication, organization management, and Role-Based Access Control (RBAC).

## 🚀 Technologies

*   **FastAPI**: High-performance Python web framework for building APIs.
*   **MongoDB (Motor)**: Asynchronous MongoDB driver for storing documents.
*   **Pydantic**: Data validation and serialization.
*   **JWT (JSON Web Tokens)**: Secure, stateless authentication.
*   **Bcrypt**: Secure password hashing.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
*   **Python 3.9+**
*   **MongoDB** (running locally on port `27017` or a cloud URI).

### 2. Environment Variables
Create a `.env` file in the `backend/` directory based on `.env.example`:

```env
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=tenderwatch
JWT_SECRET=your_super_secret_key_change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 3. Installation
To avoid dependency conflicts, use the provided Python virtual environment:

```powershell
# Navigate to the backend folder
cd backend

# Create a virtual environment (if not already done)
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Running the Server

Start the API development server using `uvicorn`:

```powershell
# Make sure your virtual environment is activated
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

The API will be available at: **http://localhost:8000**
Interactive API Documentation (Swagger UI): **http://localhost:8000/docs**

---

## 📚 API Endpoints Created

Below is the complete list of APIs implemented during Phase 1. All protected endpoints require a valid JWT Bearer Token in the `Authorization` header.

### 🔐 Authentication (`/auth`)

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| **POST** | `/auth/register` | Register a new user. If the role is `ADMIN1`, an Organization is automatically created for them using the `organization_details` payload. | Public |
| **POST** | `/auth/login` | Authenticate using Email and Password. Returns a JWT Access Token. | Public |
| **GET** | `/auth/me` | Fetch the currently authenticated user's profile data. | Any Logged-in User |

### 🏢 Organizations (`/organization`)

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| **POST** | `/organization/create` | Manually create an organization. Fails if the logged-in admin already owns an organization. | `ADMIN1`, `SUPERADMIN` |
| **GET** | `/organization/profile` | Retrieve the profile of the organization the current user belongs to. | Any Logged-in User |
| **PUT** | `/organization/profile` | Update the organization's details (e.g., description, website, location). | `ADMIN1`, `SUPERADMIN` |

### 👥 User Management (`/organization/users`)

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| **GET** | `/organization/users` | List all users belonging to the admin's organization. | `ADMIN1` |
| **POST** | `/organization/users` | Create a new user (invitation) within the admin's organization. | `ADMIN1` |
| **DELETE** | `/organization/users/{user_id}` | Delete a user from the organization. Admins cannot delete themselves. | `ADMIN1` |

---

## 🛡️ Role-Based Access Control (RBAC)

The application enforces security through four core roles:

*   **`USER`**: Standard member of an organization. Can view the organization profile and access shared tenders (Phase 2), but cannot manage other users.
*   **`ADMIN1`**: The owner/creator of an organization. Has full CRUD powers over their organization's profile and its members (`USER`s).
*   **`SUPERADMIN`**: System administrator. Has universal access to manage all systems (future proofing).
*   **`CUSTOMER_SUPPORT`**: Internal support staff facing role (future proofing).

## 🗄️ Database Collections

The MongoDB database currently consists of two main collections:

1.  **`users`**: Stores user credentials, role permissions, and `org_id` references linking individuals to their respective organizations.
    *   *Index: Unique constraint on `email`.*
2.  **`organizations`**: Stores company profiles, tracking the `owner_id` (the `ADMIN1` who created it).
    *   *Index: Fast lookups via `name`.*
