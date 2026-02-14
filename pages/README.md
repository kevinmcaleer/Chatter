# Account Management Pages for Jekyll

This directory contains Jekyll-compatible HTML pages with embedded JavaScript for account management functionality. These pages can be integrated into any Jekyll site and connect to the account management API.

## Pages Included

### 1. Login Page (`login.html`)
- **Permalink:** `/login/`
- **Features:**
  - Username and password authentication
  - Form validation
  - JWT token storage in localStorage
  - Auto-redirect if already logged in
  - Links to registration and password reset

### 2. Registration Page (`register.html`)
- **Permalink:** `/register/`
- **Features:**
  - New user account creation
  - Fields: username, firstname, lastname, email, date of birth (optional), password
  - Password confirmation validation
  - Email format validation
  - Auto-redirect if already logged in
  - Link to login page

### 3. Password Reset Page (`password-reset.html`)
- **Permalink:** `/password-reset/`
- **Features:**
  - Change password for logged-in users
  - Current password verification
  - New password confirmation
  - Password strength requirements (min 8 chars)
  - Requires authentication

### 4. Account Details Page (`account-details.html`)
- **Permalink:** `/account-details/`
- **Features:**
  - View account information
  - Edit profile (firstname, lastname, email, date of birth)
  - Change password link
  - Delete account with confirmation
  - Logout functionality
  - Dynamic data loading from API
  - Requires authentication

## JavaScript API Module

### File: `assets/js/account-api.js`

A reusable JavaScript module that handles all API interactions.

**Key Features:**
- Token management (localStorage)
- HTTP request handling
- Error handling
- Clean API interface

**Available Methods:**
```javascript
// Check login status
AccountAPI.isLoggedIn()

// Login
AccountAPI.login(username, password)

// Logout
AccountAPI.logout()

// Register new account
AccountAPI.register({ username, firstname, lastname, email, password, date_of_birth })

// Get current account
AccountAPI.getAccount()

// Update account
AccountAPI.updateAccount({ firstname, lastname, email, date_of_birth })

// Reset password
AccountAPI.resetPassword(oldPassword, newPassword)

// Delete account
AccountAPI.deleteAccount()

// Get token
AccountAPI.getToken()

// Set custom API URL
AccountAPI.setBaseURL(url)
```

## Installation

### 1. Copy Files to Jekyll Site

```bash
# Copy pages
cp pages/*.html /path/to/jekyll-site/

# Copy JavaScript
mkdir -p /path/to/jekyll-site/assets/js
cp pages/assets/js/account-api.js /path/to/jekyll-site/assets/js/
```

### 2. Configure API Endpoint

If your API is on a different domain, update the API base URL in your pages:

```html
<script>
  // Set API base URL before making calls
  AccountAPI.setBaseURL('https://api.example.com');
</script>
```

### 3. Customize Layout

Each page uses the default Jekyll layout. Update the front matter to match your site:

```yaml
---
layout: your-custom-layout
title: Login
permalink: /login/
---
```

## Styling

Each page includes embedded CSS for basic styling. You can:

1. **Use as-is:** The embedded styles provide a clean, functional design
2. **Customize inline:** Edit the `<style>` blocks in each page
3. **Extract to CSS file:** Move styles to your site's main stylesheet
4. **Use with your theme:** Remove embedded styles and let your theme handle it

## Usage in Non-Jekyll Sites

These pages can work in any static site:

1. Remove Jekyll front matter (the `---` sections)
2. Update internal links to match your site structure
3. Ensure `account-api.js` is accessible at `/assets/js/account-api.js`
4. Configure the API base URL if needed

## Embedding in Existing Pages

You can embed the JavaScript functionality in existing pages:

```html
<!-- Include the API module -->
<script src="/assets/js/account-api.js"></script>

<!-- Show user info if logged in -->
<div id="user-info"></div>

<script>
if (AccountAPI.isLoggedIn()) {
  AccountAPI.getAccount()
    .then(user => {
      document.getElementById('user-info').innerHTML =
        `Welcome, ${user.firstname} ${user.lastname}!`;
    })
    .catch(error => {
      console.error('Failed to load user:', error);
      AccountAPI.logout();
    });
} else {
  document.getElementById('user-info').innerHTML =
    '<a href="/login/">Login</a>';
}
</script>
```

## Security Considerations

1. **HTTPS Required:** Always use HTTPS in production
2. **Token Storage:** Tokens are stored in localStorage (consider HttpOnly cookies for enhanced security)
3. **CORS:** Ensure your API has proper CORS headers configured
4. **Password Requirements:** Implement strong password policies on the backend
5. **XSS Protection:** The pages use textContent for user data to prevent XSS

## API Endpoints Expected

The JavaScript expects these API endpoints:

- `POST /auth/login` - Login with username/password
- `POST /accounts/register` - Register new account
- `GET /accounts/me` - Get current user (requires auth)
- `PATCH /accounts/me` - Update account (requires auth)
- `POST /accounts/reset-password` - Reset password (requires auth)
- `DELETE /accounts/me` - Delete account (requires auth)

## Browser Compatibility

- Modern browsers with ES6+ support
- localStorage support required
- Fetch API support required
- For older browsers, include polyfills

## Customization Examples

### Custom Success Messages

```javascript
// In login.html
showMessage('Welcome back!', 'success');
```

### Redirect After Login

```javascript
// Custom redirect
setTimeout(() => {
  window.location.href = '/dashboard/';
}, 1000);
```

### Add Additional Fields

To add custom fields to the registration form:

1. Add input field to `register.html`
2. Include in userData object
3. Update backend API to accept the field
4. Update `account-details.html` to display it

## Troubleshooting

### Login Fails Silently
- Check browser console for errors
- Verify API endpoint URL is correct
- Check CORS headers on API

### Token Not Persisting
- Check if localStorage is enabled
- Verify no browser privacy settings blocking localStorage

### Styles Not Appearing
- Ensure `<style>` blocks are not removed
- Check for CSS conflicts with site theme

## Support

For issues related to:
- **API Backend:** See API documentation
- **Jekyll Integration:** See Jekyll documentation
- **JavaScript Module:** Check browser console for errors

## License

Include your license information here.
