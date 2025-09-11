# User Management UI - Admin Interface

## Overview

The User Management interface has been added to the ODRAS admin page, providing a comprehensive web-based interface for managing users following security best practices.

## Features Implemented

### ✅ Core User Management
- **User List Display**: Shows all users with status indicators, admin badges, and creation dates
- **Create New Users**: Modal form with username, password, display name, and admin privilege options
- **User Status Toggle**: Activate/deactivate user accounts
- **Password Management**: Change password functionality for current user
- **Real-time Updates**: User list refreshes after operations

### ✅ Security Features
- **Admin-Only Access**: User management section only visible to admin users
- **Password Validation**: Minimum 8 character requirement enforced
- **Secure API Calls**: All operations use authenticated API endpoints
- **Input Validation**: Client-side validation for all form inputs

### ✅ User Experience
- **Responsive Design**: Works on different screen sizes
- **Visual Status Indicators**: Color-coded active/inactive status
- **Admin Badges**: Clear indication of admin users
- **Confirmation Dialogs**: Prevents accidental user deactivation
- **Error Handling**: Clear error messages for failed operations

## UI Components

### User Management Section
Located in the Admin workbench, the User Management section includes:

```
┌─ User Management ──────────────────────────────┐
│ [Refresh Users] [Create User] [Change Password] │
│ ☐ Show inactive users                          │
├─────────────────────────────────────────────────┤
│ ┌─ User List ─────────────────────────────────┐ │
│ │ username [ADMIN] ● Active                   │ │
│ │ Display Name: John Doe                      │ │
│ │ Created: 12/15/2023              [Edit][Deactivate] │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Create User Modal
```
┌─ Create New User ──────────────────────────────┐
│ Username *        [________________]           │
│ Password *        [________________]           │
│ Display Name      [________________]           │
│ ☐ Admin privileges                            │
│                                                │
│                    [Cancel] [Create User]      │
└────────────────────────────────────────────────┘
```

### Change Password Modal
```
┌─ Change Password ──────────────────────────────┐
│ Current Password * [________________]          │
│ New Password *     [________________]          │
│ Confirm Password * [________________]          │
│                                                │
│                    [Cancel] [Change Password]  │
└────────────────────────────────────────────────┘
```

## API Integration

### Endpoints Used
- `GET /api/users/` - List all users
- `POST /api/users/` - Create new user
- `PUT /api/users/{id}` - Update user information
- `DELETE /api/users/{id}` - Deactivate user
- `POST /api/users/{id}/activate` - Activate user
- `PUT /api/users/me/password` - Change current user's password

### Authentication
All API calls include the JWT token in the Authorization header:
```javascript
headers: {
  'Authorization': `Bearer ${localStorage.getItem('odras_token')}`
}
```

## User Interface Functions

### Core Functions
- `loadUsers()` - Fetches and displays user list
- `renderUserList(users)` - Renders user list with status indicators
- `showCreateUserModal()` - Opens create user form
- `createUser()` - Handles user creation
- `editUser(userId)` - Opens user edit interface
- `updateUser(userId, updates)` - Updates user information
- `toggleUserStatus(userId, currentStatus)` - Activates/deactivates user
- `showChangePasswordModal()` - Opens password change form
- `changePassword()` - Handles password change

### User List Features
- **Status Indicators**: Green dot for active, red dot for inactive users
- **Admin Badges**: "ADMIN" badge for users with admin privileges
- **Action Buttons**: Edit and Activate/Deactivate buttons for each user
- **Creation Date**: Shows when the user account was created
- **Display Name**: Shows user's display name or "Not set"

## Security Considerations

### Access Control
- Only admin users can access the User Management section
- Admin UI visibility is controlled by `updateAdminUIVisibility()`
- Non-admin users are automatically redirected away from admin workbench

### Input Validation
- Username and password are required for new users
- Password minimum length of 8 characters enforced
- Display name is optional
- All inputs are trimmed to remove whitespace

### Error Handling
- Network errors are caught and displayed to user
- API error responses are parsed and shown
- Form validation prevents submission of invalid data

## Usage Instructions

### For Administrators

1. **Access User Management**:
   - Navigate to Admin workbench
   - Expand "User Management" section
   - Click "Refresh Users" to load current user list

2. **Create New User**:
   - Click "Create User" button
   - Fill in username (required, 3-50 characters)
   - Enter password (required, minimum 8 characters)
   - Optionally set display name
   - Check "Admin privileges" if needed
   - Click "Create User"

3. **Manage Existing Users**:
   - View user list with status indicators
   - Click "Edit" to modify user information
   - Click "Activate"/"Deactivate" to change user status
   - Use "Show inactive users" checkbox to view deactivated accounts

4. **Change Your Password**:
   - Click "Change My Password" button
   - Enter current password
   - Enter new password (minimum 8 characters)
   - Confirm new password
   - Click "Change Password"

### User Status Management
- **Active Users**: Can log in and access the system
- **Inactive Users**: Cannot log in, accounts are disabled
- **Admin Users**: Have full system access and can manage other users
- **Regular Users**: Can access projects they're members of

## Best Practices

### User Creation
- Use descriptive usernames (e.g., firstname.lastname)
- Set meaningful display names for better identification
- Only grant admin privileges to trusted users
- Use strong passwords (minimum 8 characters, mix of letters/numbers)

### User Management
- Regularly review user list for inactive accounts
- Deactivate accounts for users who no longer need access
- Keep admin user count minimal
- Monitor user creation and access patterns

### Security
- Change default passwords immediately after setup
- Use strong, unique passwords for all accounts
- Regularly review admin user list
- Deactivate unused accounts promptly

## Future Enhancements

### Planned Features
- [ ] Enhanced user edit modal with all fields
- [ ] User search and filtering
- [ ] Bulk user operations
- [ ] User activity logging
- [ ] Password reset functionality
- [ ] User role management beyond admin/user
- [ ] User import/export capabilities
- [ ] Advanced user permissions

### UI Improvements
- [ ] Pagination for large user lists
- [ ] Advanced search and filtering
- [ ] User activity indicators
- [ ] Bulk selection and operations
- [ ] User profile pictures
- [ ] Last login information

## Troubleshooting

### Common Issues

1. **"Error loading users"**
   - Check if user has admin privileges
   - Verify API endpoints are accessible
   - Check browser console for detailed error messages

2. **"User not found" when editing**
   - User may have been deleted by another admin
   - Refresh user list to get current state

3. **"Admin access required"**
   - Current user doesn't have admin privileges
   - Contact system administrator for access

4. **Password change fails**
   - Verify current password is correct
   - Ensure new password meets requirements
   - Check for network connectivity issues

### Debug Information
- Check browser console for detailed error messages
- Verify API responses in Network tab
- Ensure JWT token is valid and not expired
- Check user permissions in database

## Integration Notes

The User Management UI integrates seamlessly with the existing ODRAS admin interface:

- **Consistent Styling**: Uses same CSS variables and design patterns
- **Modal System**: Reuses existing modal infrastructure
- **API Integration**: Follows established authentication patterns
- **Error Handling**: Consistent with other admin functions
- **Responsive Design**: Works across different screen sizes

The implementation follows ODRAS coding standards and integrates with the existing codebase without conflicts.
