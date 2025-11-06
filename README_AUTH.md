# Authentication Setup

## What's Been Added

1. **Cognito User Pool** - Admin-only user creation
2. **API Gateway Authorization** - All endpoints require JWT tokens
3. **User Management Script** - Easy user invitation/management
4. **Authenticated Web App** - Login/logout functionality

## Deployment

Deploy the updated stack:
```bash
sam deploy
```

## User Management

### Invite a User
```bash
python3 scripts/manage_users.py invite --email user@example.com
```

### Invite with Temporary Password
```bash
python3 scripts/manage_users.py invite --email user@example.com --password TempPass123!
```

### List Users
```bash
python3 scripts/manage_users.py list
```

### Delete User
```bash
python3 scripts/manage_users.py delete --email user@example.com
```

## Web Access

After deployment:
1. Use the Amplify URL from stack outputs
2. Login with invited user credentials
3. First-time users will be prompted to set a new password

## API Access

All API endpoints now require Authorization header:
```bash
curl -H "Authorization: <JWT_TOKEN>" https://your-api-gateway/images
```

## Files Changed

- `template.yaml` - Added Cognito resources and API authorization
- `web/auth.html` - New authenticated web interface
- `web/config.js` - Added Cognito configuration
- `scripts/manage_users.py` - User management utility