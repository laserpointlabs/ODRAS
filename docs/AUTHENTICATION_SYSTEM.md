# ODRAS Authentication System

## Overview

This document describes the enhanced authentication system for ODRAS, which replaces the previous allowlist-based system with proper password authentication and user management.

## Security Features

### ✅ Implemented
- **Password Hashing**: PBKDF2 with 100,000 iterations and random salt
- **Role-Based Access Control**: Admin and regular user roles
- **Account Management**: User activation/deactivation
- **Secure Token Storage**: Database-backed token management
- **Password Requirements**: Minimum 8 characters
- **User Management API**: Full CRUD operations for users

### 🔒 Security Best Practices
- Passwords are never stored in plain text
- Each password has a unique salt
- Tokens expire after 24 hours
- Admin operations require authentication
- User accounts can be deactivated
- Password changes require current password verification

## Database Schema

### Users Table
```sql
CREATE TABLE public.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with username/password
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout (invalidate token)

### User Management (Admin Only)
- `POST /api/users/` - Create new user
- `GET /api/users/` - List all users
- `PUT /api/users/{user_id}` - Update user info
- `DELETE /api/users/{user_id}` - Deactivate user
- `POST /api/users/{user_id}/activate` - Activate user

### Self-Service
- `PUT /api/users/me/password` - Change own password

## Migration from Old System

### 1. Run Database Migration
```bash
psql -U postgres -d odras -f scripts/migrate_auth_system.sql
```

### 2. Setup Initial Users
```bash
python scripts/setup_initial_users.py
```

### 3. Update Environment Variables
Remove or comment out the old `ALLOWED_USERS` environment variable:
```bash
# OLD - Remove this
# export ALLOWED_USERS="admin,jdehart"

# NEW - No environment variable needed
```

## Default Credentials

After running the setup script, you'll have these default accounts:

| Username | Password | Role |
|----------|----------|------|
| admin | admin123! | Admin |
| jdehart | jdehart123! | User |

**⚠️ IMPORTANT**: Change these passwords immediately after first login!

## Usage Examples

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123!"}'
```

### Create New User (Admin)
```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "securepassword123",
    "display_name": "New User",
    "is_admin": false
  }'
```

### Change Password
```bash
curl -X PUT http://localhost:8000/api/users/me/password \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "admin123!",
    "new_password": "newsecurepassword123"
  }'
```

## Frontend Integration

The frontend login form now properly validates passwords:

```javascript
// Login form submission
const login = async (username, password) => {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  
  if (response.ok) {
    const { token } = await response.json();
    localStorage.setItem('odras_token', token);
    // Redirect to main app
  } else {
    // Show error message
  }
};
```

## Security Considerations

### Password Policy
- Minimum 8 characters (configurable)
- No maximum length limit
- No complexity requirements (can be added)
- Passwords are hashed with PBKDF2

### Token Management
- Tokens expire after 24 hours
- Tokens are stored in database with hash
- Inactive users cannot authenticate
- Admin can deactivate any user

### Access Control
- Admin users can manage all users
- Regular users can only change their own password
- Project access is still controlled by project membership
- Admin UI elements are hidden for non-admin users

## Troubleshooting

### Common Issues

1. **"Invalid username or password"**
   - Check username spelling
   - Verify password is correct
   - Ensure user account is active

2. **"User not found"**
   - User may not exist in database
   - Check if user was deactivated

3. **"Admin access required"**
   - User needs admin privileges for the operation
   - Check user's `is_admin` status

### Database Issues

1. **Migration failed**
   - Check PostgreSQL connection
   - Ensure user has CREATE/ALTER permissions
   - Run migration script manually

2. **Password fields missing**
   - Run the migration script: `scripts/migrate_auth_system.sql`
   - Check table schema with `\d users` in psql

## Future Enhancements

### Planned Features
- [ ] Password complexity requirements
- [ ] Account lockout after failed attempts
- [ ] Password expiration
- [ ] Two-factor authentication
- [ ] LDAP/Active Directory integration
- [ ] OAuth2/SSO support
- [ ] Audit logging for user actions

### Configuration Options
- [ ] Configurable password policy
- [ ] Token expiration time
- [ ] Maximum failed login attempts
- [ ] Password history (prevent reuse)

## Support

For issues with the authentication system:
1. Check the logs for error messages
2. Verify database connectivity
3. Ensure all migrations have been run
4. Check user account status in database

Contact the development team for additional support.
