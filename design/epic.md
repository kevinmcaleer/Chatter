# User Account Management - GitHub Issue #27

## User Stories

### Registration
**As a** new user
**I want to** register for an account
**So that** I can participate in comments and track my activity

**Acceptance Criteria:**
- User can access registration page at `/register`
- Form collects: first name, last name, username, email, date of birth (optional), password
- Username and email must be unique
- Password must be at least 8 characters
- Form errors are displayed inline within the form (not as JSON)
- Successful registration redirects to login page
- All validation errors are shown in user-friendly format

### Login
**As a** registered user
**I want to** log in to my account
**So that** I can access my profile and manage my activity

**Acceptance Criteria:**
- User can access login page at `/login`
- Form collects: username and password
- Invalid credentials show error message in the form (not JSON)
- Successful login redirects to account page at `/account`
- Login session persists via secure HTTP-only cookie
- Rate limiting prevents brute force attempts (5 attempts per minute)

### Account Management
**As a** logged-in user
**I want to** manage my account details
**So that** I can keep my information up to date

**Acceptance Criteria:**
- User can access account page at `/account`
- User can view their username (read-only, cannot be changed)
- User can update their email address
- User can change their password
- User can view activity statistics (likes, comments)
- User can view their comment history
- User can delete their account
- All form errors display inline (not as JSON)
- Email validation shows user-friendly errors
- Password change requires current password verification

### Logout
**As a** logged-in user
**I want to** log out of my account
**So that** I can secure my session

**Acceptance Criteria:**
- User can logout via `/logout` endpoint
- Logout clears the authentication cookie
- Logout redirects to login page

### Admin Panel
**As an** administrator
**I want to** manage user accounts
**So that** I can maintain security and help users with account issues

**Acceptance Criteria:**
- Admin can access admin panel at `/admin` (admin-only access)
- Admin panel displays list of all users with:
  - Username
  - Full name (first and last)
  - Email address
  - User type (Admin or User badge)
  - Account status (Active or Inactive)
  - Last login timestamp
  - Account creation date
  - Password reset indicator (badge when reset is required)
- Admin can force password reset for any user (except themselves)
- Forced password reset triggers warning badge on user row
- Admin actions show success/error messages
- Admin panel includes back button to account page
- Admin button is visible on account page for admin users only

### Forced Password Reset
**As a** user whose password reset was forced by admin
**I want to** be prompted to change my password on next login
**So that** I can secure my account with a new password

**Acceptance Criteria:**
- User is redirected to password reset page after successful login
- Password reset page explains admin has required password change
- Form collects new password and confirmation
- Password must be at least 8 characters
- Passwords must match
- Form errors display inline (not as JSON)
- After successful reset, user is redirected to account page
- Reset flag is cleared from user account
- User can proceed normally after password is changed

## Non-Functional Requirements

### Error Handling
**All errors must be handled gracefully in the UI:**
- Form validation errors must be displayed inline within the form that triggered them
- Errors must NOT be returned as JSON responses to form submissions
- Error messages must be user-friendly and actionable
- Each form should display errors in context (e.g., "Email already registered" appears near email field)
- Server errors should show generic "Something went wrong" message to users
- Technical error details should only be logged server-side

### Security
- Passwords must be hashed using bcrypt
- Authentication uses JWT tokens stored in HTTP-only cookies
- Cookies must use `secure` flag in production (HTTPS only)
- Cookies must use `samesite=lax` to prevent CSRF
- Rate limiting on login endpoint (5 requests per minute)
- Session tokens expire after 30 minutes

### User Experience
- All pages must use consistent Kev's Robots branding
- Forms must have clear labels and placeholders
- Success messages must be shown for completed actions
- Page titles must be descriptive
- Navigation must be intuitive with clear links
- Mobile-responsive design using Bootstrap 5.3.3

### Performance
- Forms must validate on both client and server side
- Database queries must use proper indexing
- Pages must load in under 2 seconds

## Technical Implementation

### Routes
- `GET /register` - Show registration form
- `POST /register` - Process registration (form data)
- `GET /login` - Show login form
- `POST /login` - Process login (form data)
- `GET /logout` - Logout and redirect
- `GET /account` - Show account management page
- `POST /account/update` - Update email
- `POST /account/change-password` - Change password
- `POST /account/delete` - Delete account
- `GET /admin` - Show admin panel (admin-only)
- `POST /admin/force-password-reset/{user_id}` - Force password reset (admin-only)
- `GET /force-password-reset` - Show forced password reset form
- `POST /force-password-reset` - Process forced password reset

### API Routes (for backward compatibility)
- `POST /api/register` - JSON API endpoint (deprecated)
- `POST /api/login` - JSON API endpoint (OAuth2)

### Templates
- `base.html` - Base template with navigation and footer
- `register.html` - Registration form
- `login.html` - Login form
- `account.html` - Account management page
- `admin.html` - Admin panel with user management
- `force_password_reset.html` - Forced password reset form

## Testing Requirements
- All endpoints must have unit tests
- Form validation must be tested
- Error handling must be verified for all edge cases
- Security measures must be tested (password hashing, rate limiting)
- Code coverage must be at least 80%

---

# Likes, Comments and Page Views - GitHub Issues #13, #37, #42, #52

## Features Overview

### Likes Feature (#37)
**As a** user
**I want to** like content I enjoy
**So that** I can show appreciation and bookmark content

**Acceptance Criteria:**
- All users can see like counts on content pages
- Only authenticated users can like/unlike content
- Like button shows outline heart when not liked, filled red heart when liked
- Likes are stored per URL and per user (one like per user per URL)
- Like counts update immediately after like/unlike action
- Like data is retrieved from materialized view for performance

**API Endpoints:**
- `POST /interact/like` - Toggle like for authenticated user
- `GET /interact/likes/{url:path}` - Get like count for any URL
- `GET /interact/user-like-status/{url:path}` - Check if current user has liked
- `GET /interact/most-liked` - Get most liked content from materialized view
- `POST /interact/refresh-most-liked` - Refresh materialized view

### Comments Feature (#42, #35)
**As a** user
**I want to** comment on content
**So that** I can share my thoughts and engage with others

**Acceptance Criteria:**
- All users can read non-hidden comments
- Only authenticated users can post comments
- Comments show username and relative time (e.g., "2h", "3d")
- Comments cannot contain URLs or links (validated client and server-side)
- Comments are checked against profanity/banned word list
- Content is sanitized to prevent XSS attacks
- Users can report comments as spam/abusive via hamburger menu
- Admins can hide reported comments
- Hidden comments don't appear in comment count or listings
- Comments are sorted newest first

**Moderation Features:**
- Users can report comments with reason (spam, abusive, inappropriate, other)
- Flagged comments track flag count and reasons (JSON)
- Admins can view all flagged comments
- Admins can hide/unhide comments
- Admins can clear flags after review
- All moderation actions track reviewer ID and timestamp

**API Endpoints:**
- `POST /interact/comment` - Post new comment (authenticated)
- `GET /interact/comments/{url:path}` - Get comments for URL
- `POST /interact/comments/{comment_id}/report` - Report comment (authenticated)
- `GET /interact/comments/flagged` - Get flagged comments (admin-only)
- `POST /interact/comments/{comment_id}/hide` - Hide comment (admin-only)
- `POST /interact/comments/{comment_id}/unhide` - Unhide comment (admin-only)
- `POST /interact/comments/{comment_id}/clear-flags` - Clear flags (admin-only)

### Page View Tracking (#52)
**As a** site owner
**I want to** track page views
**So that** I can understand content popularity and engagement

**Acceptance Criteria:**
- Every page load logs a view to the database
- Page views track: URL, IP address, timestamp, user agent
- View counts are aggregated in materialized view for performance
- View counts display with formatted numbers:
  - Under 1,000: exact number (e.g., "234")
  - 1,000-9,999: one decimal (e.g., "1.2k")
  - 10,000-999,999: whole number (e.g., "12k")
  - 1,000,000+: millions format (e.g., "1.5M")
- View counts show in summary widgets with chart icon
- View tracking does not require authentication
- View data includes unique visitor counts

**API Endpoints:**
- `POST /analytics/page-view` - Log a page view (no auth required)
- `GET /analytics/page-views/{url:path}` - Get view statistics for URL
- `POST /analytics/refresh-page-view-counts` - Refresh materialized view
- `GET /analytics/most-viewed` - Get most viewed pages

### UI Components

#### Like-Comment Component (`like-comment.html`)
Full-featured component for individual content pages:
- Heart icon like button (outline/filled states)
- Like count display
- Comment textarea with "post your comment" placeholder
- Post comment button (disabled until text entered)
- Comment list with username, timestamp, content
- Hamburger menu on each comment for reporting
- Success/error message displays
- Loading spinner for comments

**Usage:**
```liquid
{% include like-comment.html %}
```
Component automatically detects page URL from data attribute.

#### Like-Comment-Summary Component (`like-comment-summary.html`)
Lightweight summary widget for cards and galleries:
- Chart icon with view count (formatted)
- Heart icon with like count
- Comment icon with comment count
- All counts shown even when zero
- Optional background color support for light text

**Usage:**
```liquid
{% assign url_without_slash = page.url | remove_first: "/" %}
{% include like-comment-summary.html url=url_without_slash %}
```

### JavaScript Implementation

#### `like-comment.js`
- Handles full like/comment functionality on content pages
- Logs page view on load
- Checks user authentication via username cookie
- Loads like count and user like status
- Handles like/unlike toggle with visual feedback
- Validates comment content client-side (no URLs, no empty)
- Posts comments and refreshes list
- Formats relative timestamps
- Sanitizes HTML output

#### `like-comment-summary.js`
- Loads data for multiple summary widgets in parallel
- Fetches view count, like count, and comment count
- Updates DOM elements with formatted data
- Gracefully handles errors (shows 0s)

### Database Schema

#### `like` table
- `id` - Primary key
- `url` - Content URL (indexed, no leading slash)
- `user_id` - Foreign key to user (indexed)
- `created_at` - Timestamp
- Unique constraint on (url, user_id)

#### `comment` table
- `id` - Primary key
- `url` - Content URL (indexed, no leading slash)
- `content` - Comment text (sanitized)
- `created_at` - Timestamp
- `user_id` - Foreign key to user (indexed)
- `is_flagged` - Boolean for moderation
- `flag_count` - Number of reports
- `flag_reasons` - JSON array of report details
- `is_hidden` - Boolean, hidden by admin
- `reviewed_at` - Timestamp of review
- `reviewed_by` - Foreign key to admin user

#### `pageview` table
- `id` - Primary key
- `url` - Content URL (indexed, no leading slash)
- `ip_address` - Visitor IP (indexed)
- `viewed_at` - Timestamp (indexed)
- `user_agent` - Browser/device info

#### Materialized Views
- `most_liked_content` - Aggregated like counts by URL
- `page_view_counts` - Aggregated view counts by URL with unique visitors

### URL Normalization
All URLs are normalized before storage:
- Leading slashes are stripped: `/blog/post.html` → `blog/post.html`
- Query parameters are captured using FastAPI `{url:path}` parameter
- Jekyll `page.url` values are filtered: `{{ page.url | remove_first: "/" }}`

### Security & Validation

**Authentication:**
- JWT tokens in HTTP-only cookies for API authentication
- Additional username cookie (non-httponly) for JavaScript auth checks
- Tokens expire after 30 minutes

**Content Validation:**
- Client-side: Check for URLs in comments before posting
- Server-side: Validate comment content, check banned words
- Server-side: Sanitize HTML to prevent XSS attacks
- Server-side: Enforce maximum content length

**Rate Limiting:**
- Implemented via SlowAPI on all endpoints
- Prevents spam and abuse

**IP Address Handling:**
- Real IP extracted from X-Forwarded-For header (nginx proxy)
- Falls back to direct connection IP

### Performance Optimizations
- Materialized views for aggregated counts
- Refresh views via scheduled tasks or manual trigger
- Database indexes on frequently queried columns (url, user_id, ip_address, timestamps)
- Parallel API requests in JavaScript for multiple widgets
- Lazy loading of comments

### Future Enhancements
- Comment replies/threading (#43)
- User ability to edit/delete own comments (#46)
- @mentions in comments (#45)
- Admin comment removal (#47)
- User profiles with activity history (#44)