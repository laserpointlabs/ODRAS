# ODRAS Authentication System<br>
<br>
## Overview<br>
<br>
This document describes the enhanced authentication system for ODRAS, which replaces the previous allowlist-based system with proper password authentication and user management.<br>
<br>
## Security Features<br>
<br>
### ✅ Implemented<br>
- **Password Hashing**: PBKDF2 with 100,000 iterations and random salt<br>
- **Role-Based Access Control**: Admin and regular user roles<br>
- **Account Management**: User activation/deactivation<br>
- **Secure Token Storage**: Database-backed token management<br>
- **Password Requirements**: Minimum 8 characters<br>
- **User Management API**: Full CRUD operations for users<br>
<br>
### 🔒 Security Best Practices<br>
- Passwords are never stored in plain text<br>
- Each password has a unique salt<br>
- Tokens expire after 24 hours<br>
- Admin operations require authentication<br>
- User accounts can be deactivated<br>
- Password changes require current password verification<br>
<br>
## Database Schema<br>
<br>
### Users Table<br>
```sql<br>
CREATE TABLE public.users (<br>
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),<br>
    username VARCHAR(255) UNIQUE NOT NULL,<br>
    display_name VARCHAR(255),<br>
    password_hash VARCHAR(255) NOT NULL,<br>
    salt VARCHAR(255) NOT NULL,<br>
    is_admin BOOLEAN DEFAULT FALSE,<br>
    is_active BOOLEAN DEFAULT TRUE,<br>
    created_at TIMESTAMPTZ DEFAULT NOW(),<br>
    updated_at TIMESTAMPTZ DEFAULT NOW()<br>
);<br>
```<br>
<br>
## API Endpoints<br>
<br>
### Authentication<br>
- `POST /api/auth/login` - Login with username/password<br>
- `GET /api/auth/me` - Get current user info<br>
- `POST /api/auth/logout` - Logout (invalidate token)<br>
<br>
### User Management (Admin Only)<br>
- `POST /api/users/` - Create new user<br>
- `GET /api/users/` - List all users<br>
- `PUT /api/users/{user_id}` - Update user info<br>
- `DELETE /api/users/{user_id}` - Deactivate user<br>
- `POST /api/users/{user_id}/activate` - Activate user<br>
<br>
### Self-Service<br>
- `PUT /api/users/me/password` - Change own password<br>
<br>
## Migration from Old System<br>
<br>
### 1. Run Database Migration<br>
```bash<br>
psql -U postgres -d odras -f scripts/migrate_auth_system.sql<br>
```<br>
<br>
### 2. Setup Initial Users<br>
```bash<br>
python scripts/setup_initial_users.py<br>
```<br>
<br>
### 3. Update Environment Variables<br>
Remove or comment out the old `ALLOWED_USERS` environment variable:<br>
```bash<br>
# OLD - Remove this<br>
# export ALLOWED_USERS="admin,jdehart"<br>
<br>
# NEW - No environment variable needed<br>
```<br>
<br>
## Default Credentials<br>
<br>
After running the setup script, you'll have these default accounts:<br>
<br>
| Username | Password | Role |<br>
|----------|----------|------|<br>
| admin | admin123! | Admin |<br>
| jdehart | jdehart123! | User |<br>
<br>
**⚠️ IMPORTANT**: Change these passwords immediately after first login!<br>
<br>
## Usage Examples<br>
<br>
### Login<br>
```bash<br>
curl -X POST http://localhost:8000/api/auth/login \<br>
  -H "Content-Type: application/json" \<br>
  -d '{"username": "admin", "password": "admin123!"}'<br>
```<br>
<br>
### Create New User (Admin)<br>
```bash<br>
curl -X POST http://localhost:8000/api/users/ \<br>
  -H "Authorization: Bearer YOUR_TOKEN" \<br>
  -H "Content-Type: application/json" \<br>
  -d '{<br>
    "username": "newuser",<br>
    "password": "securepassword123",<br>
    "display_name": "New User",<br>
    "is_admin": false<br>
  }'<br>
```<br>
<br>
### Change Password<br>
```bash<br>
curl -X PUT http://localhost:8000/api/users/me/password \<br>
  -H "Authorization: Bearer YOUR_TOKEN" \<br>
  -H "Content-Type: application/json" \<br>
  -d '{<br>
    "old_password": "admin123!",<br>
    "new_password": "newsecurepassword123"<br>
  }'<br>
```<br>
<br>
## Frontend Integration<br>
<br>
The frontend login form now properly validates passwords:<br>
<br>
```javascript<br>
// Login form submission<br>
const login = async (username, password) => {<br>
  const response = await fetch('/api/auth/login', {<br>
    method: 'POST',<br>
    headers: { 'Content-Type': 'application/json' },<br>
    body: JSON.stringify({ username, password })<br>
  });<br>
<br>
  if (response.ok) {<br>
    const { token } = await response.json();<br>
    localStorage.setItem('odras_token', token);<br>
    // Redirect to main app<br>
  } else {<br>
    // Show error message<br>
  }<br>
};<br>
```<br>
<br>
## Security Considerations<br>
<br>
### Password Policy<br>
- Minimum 8 characters (configurable)<br>
- No maximum length limit<br>
- No complexity requirements (can be added)<br>
- Passwords are hashed with PBKDF2<br>
<br>
### Token Management<br>
- Tokens expire after 24 hours<br>
- Tokens are stored in database with hash<br>
- Inactive users cannot authenticate<br>
- Admin can deactivate any user<br>
<br>
### Access Control<br>
- Admin users can manage all users<br>
- Regular users can only change their own password<br>
- Project access is still controlled by project membership<br>
- Admin UI elements are hidden for non-admin users<br>
<br>
## Troubleshooting<br>
<br>
### Common Issues<br>
<br>
1. **"Invalid username or password"**<br>
   - Check username spelling<br>
   - Verify password is correct<br>
   - Ensure user account is active<br>
<br>
2. **"User not found"**<br>
   - User may not exist in database<br>
   - Check if user was deactivated<br>
<br>
3. **"Admin access required"**<br>
   - User needs admin privileges for the operation<br>
   - Check user's `is_admin` status<br>
<br>
### Database Issues<br>
<br>
1. **Migration failed**<br>
   - Check PostgreSQL connection<br>
   - Ensure user has CREATE/ALTER permissions<br>
   - Run migration script manually<br>
<br>
2. **Password fields missing**<br>
   - Run the migration script: `scripts/migrate_auth_system.sql`<br>
   - Check table schema with `\d users` in psql<br>
<br>
## Future Enhancements<br>
<br>
### Planned Features<br>
- [ ] Password complexity requirements<br>
- [ ] Account lockout after failed attempts<br>
- [ ] Password expiration<br>
- [ ] Two-factor authentication<br>
- [ ] LDAP/Active Directory integration<br>
- [ ] OAuth2/SSO support<br>
- [ ] Audit logging for user actions<br>
<br>
### Configuration Options<br>
- [ ] Configurable password policy<br>
- [ ] Token expiration time<br>
- [ ] Maximum failed login attempts<br>
- [ ] Password history (prevent reuse)<br>
<br>
## Support<br>
<br>
For issues with the authentication system:<br>
1. Check the logs for error messages<br>
2. Verify database connectivity<br>
3. Ensure all migrations have been run<br>
4. Check user account status in database<br>
<br>
Contact the development team for additional support.<br>

