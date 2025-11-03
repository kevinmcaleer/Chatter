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

---

# User Projects - GitHub Issue #15

## Feature Overview
**As a** registered user
**I want to** create and share maker projects
**So that** I can showcase my work and help others replicate my builds

## Core Functionality

### Project Management
Users can create, edit, publish, and delete projects with:
- **Mandatory fields:** title, description, tags (at least 1)
- **Optional fields:** background story, code repository link
- **Draft mode:** Projects start as drafts visible only to the author
- **Publishing:** Authors can publish/unpublish projects at any time
- **Deletion:** Only authors can delete their own projects

### Project Components

#### Steps
Ordered step-by-step instructions for building the project:
- Step number (manual ordering)
- Title (brief step name)
- Content (detailed instructions in markdown)
- Reordering capability to rearrange steps

#### Bill of Materials (BOM)
List of items needed with pricing:
- Item name
- Description
- Quantity
- Price in cents (supports currency conversion)
- Custom ordering

#### Electronic Components
Reusable component library with autocomplete:
- Component master list (name, description, datasheet URL)
- Project-specific quantity and notes
- Search/autocomplete with minimum 2 characters
- Prevents duplicate components per project

#### Tools & Materials
Required tools and raw materials:
- Tool/material name
- Type (tool, material, or other)
- Notes field for specifications

#### External Links
Curated links to related resources:
- URL, title, description
- Link type: video, course, article, blog, documentation, other
- Helps users find additional learning resources

#### Files
Downloadable project files (max 25MB each):
- Allowed types: .pdf, .zip, .stl, .step, .ino, .py, .cpp, .h, .json, .xml, .txt, .md
- Stored with UUID filenames to prevent conflicts
- Original filename preserved for display
- File size tracked in database
- Author can add title and description

#### Images
Project photo gallery (max 10MB each):
- Allowed types: .jpg, .jpeg, .png, .gif, .webp
- Multiple images per project
- Optional captions
- Primary image selection for project thumbnail
- Automatic image URL generation

### Discovery & Browsing

#### Project Gallery
Paginated grid view with filtering:
- Filter by status (published only for public)
- Filter by tag
- Filter by author
- Sort options: recent, popular, most liked, most viewed
- Page-based pagination (default 20 per page)
- Each card shows: title, author, tags, primary image, stats

#### Project Detail View
Complete project page with all information:
- Project metadata (title, description, background, code link)
- Author information
- Statistics (views, likes, comments, downloads)
- Tags
- All child resources (steps, BOM, components, links, tools, files, images)
- Organized tabs or sections for easy navigation

### Permissions & Security

#### Authorization Model
- **Public access:** View published projects, browse gallery
- **Authenticated users:** Create projects, like/comment on projects
- **Project authors:** Full CRUD on their own projects and all child resources
- **Draft protection:** Drafts only visible to author, not in public gallery

#### File Upload Security
- File size limits enforced (25MB files, 10MB images)
- Extension whitelist validation
- UUID-based filenames prevent overwrites and path traversal
- Physical file deletion when database record deleted
- Automatic directory creation on startup

## API Architecture

### REST Endpoints (37 total)

All project endpoints use `/api` prefix.

#### Core Project Operations (9 endpoints)
- POST `/projects` - Create project (auth required)
- GET `/projects/{id}` - Get project details
- PUT `/projects/{id}` - Update project (author only)
- DELETE `/projects/{id}` - Delete project (author only)
- POST `/projects/{id}/publish` - Publish project (author only)
- POST `/projects/{id}/unpublish` - Unpublish project (author only)
- GET `/projects` - Gallery with filters (public)
- GET `/projects/{id}/download` - Download complete project as ZIP with auto-generated README
- OPTIONS `/projects` - CORS preflight

#### Steps Management (5 endpoints)
- POST `/projects/{id}/steps` - Add step
- GET `/projects/{id}/steps` - List steps
- PUT `/projects/{id}/steps/{step_id}` - Update step
- DELETE `/projects/{id}/steps/{step_id}` - Delete step
- PUT `/projects/{id}/steps/reorder` - Reorder steps (provide array of step IDs)

#### Bill of Materials (4 endpoints)
- POST `/projects/{id}/bom` - Add BOM item
- GET `/projects/{id}/bom` - List BOM items
- PUT `/projects/{id}/bom/{item_id}` - Update item
- DELETE `/projects/{id}/bom/{item_id}` - Delete item

#### Components (5 endpoints)
- GET `/components/search?q={query}` - Search components (min 2 chars)
- POST `/components` - Create reusable component
- POST `/projects/{id}/components` - Add component to project
- GET `/projects/{id}/components` - List project components
- DELETE `/projects/{id}/components/{pc_id}` - Remove component

#### Links (4 endpoints)
- POST `/projects/{id}/links` - Add link
- GET `/projects/{id}/links` - List links
- PUT `/projects/{id}/links/{link_id}` - Update link
- DELETE `/projects/{id}/links/{link_id}` - Delete link

#### Tools & Materials (4 endpoints)
- POST `/projects/{id}/tools` - Add tool/material
- GET `/projects/{id}/tools` - List tools/materials
- PUT `/projects/{id}/tools/{tool_id}` - Update tool/material
- DELETE `/projects/{id}/tools/{tool_id}` - Delete tool/material

#### Files (3 endpoints)
- POST `/projects/{id}/files` - Upload file (multipart/form-data)
- GET `/projects/{id}/files` - List files
- DELETE `/projects/{id}/files/{file_id}` - Delete file

#### Images (5 endpoints)
- POST `/projects/{id}/images` - Upload image (multipart/form-data)
- GET `/projects/{id}/images` - List images
- PUT `/projects/{id}/images/{image_id}/primary` - Set primary image
- DELETE `/projects/{id}/images/{image_id}` - Delete image

### Request/Response Models

#### Pydantic Schemas
All endpoints use strongly-typed Pydantic schemas for validation:
- `ProjectCreate`, `ProjectUpdate`, `ProjectDetail`, `ProjectSummary`
- `ProjectStepCreate`, `ProjectStepUpdate`, `ProjectStepRead`
- `BillOfMaterialCreate`, `BillOfMaterialUpdate`, `BillOfMaterialRead`
- `ComponentCreate`, `ComponentRead`, `ProjectComponentCreate`, `ProjectComponentRead`
- `ProjectLinkCreate`, `ProjectLinkUpdate`, `ProjectLinkRead`
- `ToolMaterialCreate`, `ToolMaterialUpdate`, `ToolMaterialRead`
- `ProjectFileRead`, `ProjectImageRead`
- `ProjectGallery` (with pagination metadata)

#### Validation Rules
- Tags automatically converted to lowercase
- Required fields enforced at API level
- Optional fields can be null
- Enums for status, link_type, tool_type
- URL format validation
- File extension validation
- File size validation

## Database Schema

### Tables (11 total)

#### `project` (core table)
- `id` - Serial primary key
- `title` - VARCHAR(255), indexed
- `description` - TEXT
- `author_id` - FK to user, indexed
- `status` - VARCHAR(20), default 'draft', indexed
- `background` - TEXT (optional)
- `code_link` - VARCHAR(500) (optional)
- `created_at` - Timestamp, indexed
- `updated_at` - Timestamp
- `primary_image_id` - FK to project_image (optional)
- `view_count` - Integer, default 0
- `download_count` - Integer, default 0
- `like_count` - Integer, default 0
- `comment_count` - Integer, default 0

#### `project_tag`
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `tag_name` - VARCHAR(50), lowercase
- Composite index on (project_id, tag_name)

#### `project_step`
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `step_number` - Integer
- `title` - VARCHAR(255)
- `content` - TEXT
- `created_at` - Timestamp
- Unique constraint on (project_id, step_number)

#### `bill_of_material`
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `item_name` - VARCHAR(255)
- `description` - TEXT (optional)
- `quantity` - Integer
- `price_cents` - Integer (optional)
- `item_order` - Integer

#### `component` (shared component library)
- `id` - Serial primary key
- `name` - VARCHAR(255), unique, indexed
- `description` - TEXT (optional)
- `datasheet_url` - VARCHAR(500) (optional)
- `created_at` - Timestamp

#### `project_component` (junction table)
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `component_id` - FK to component
- `quantity` - Integer
- `notes` - TEXT (optional)
- Unique constraint on (project_id, component_id)

#### `project_file`
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `filename` - VARCHAR(255) (original filename)
- `file_path` - VARCHAR(500) (UUID-based path)
- `file_size` - Integer (bytes)
- `title` - VARCHAR(255)
- `description` - TEXT (optional)
- `uploaded_at` - Timestamp

#### `project_image`
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `filename` - VARCHAR(255) (original filename)
- `image_path` - VARCHAR(500) (UUID-based path)
- `caption` - TEXT (optional)
- `uploaded_at` - Timestamp

#### `project_link`
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `url` - VARCHAR(500)
- `title` - VARCHAR(255)
- `link_type` - VARCHAR(50) (video, course, article, blog, documentation, other)
- `description` - TEXT (optional)

#### `tool_material`
- `id` - Serial primary key
- `project_id` - FK to project, cascade delete
- `name` - VARCHAR(255)
- `tool_type` - VARCHAR(50) (tool, material, other)
- `notes` - TEXT (optional)

### Relationships
- One user has many projects
- One project has many: tags, steps, BOM items, components, links, files, images, tools
- Components are shared across projects (many-to-many via project_component)
- All child resources cascade delete when project deleted

### Indexes
Strategic indexes for performance:
- `project`: author_id, status, created_at, title
- `project_tag`: (project_id, tag_name) composite
- `project_step`: (project_id, step_number) unique composite
- `component`: name unique index

## File Storage

### Storage Strategy - NAS with Local Fallback

Project files use a robust dual-storage system matching the profile picture implementation:

**Primary Storage: NAS (Network Attached Storage)**
```
NAS Share (SMB/CIFS):
├── projects/
│   ├── files/          # Project files (CAD, code, etc.)
│   │   └── {uuid}.ext
│   └── images/         # Project images
│       └── {uuid}.ext
```

**Fallback Storage: Local Filesystem**
```
/tmp/chatter_uploads/projects/
├── files/
│   └── {uuid}.ext
└── images/
    └── {uuid}.ext
```

### Storage Implementation

**Configuration** (`app/config.py`):
- `NAS_HOST` - NAS server address
- `NAS_USERNAME`, `NAS_PASSWORD` - SMB credentials (from environment)
- `NAS_SHARE_NAME` - SMB share name
- `NAS_PROJECT_FILES_PATH` = "projects/files"
- `NAS_PROJECT_IMAGES_PATH` = "projects/images"
- Local paths configured as fallback

**Storage Functions** (`app/storage.py`):
- `check_nas_connection()` - Verify NAS availability
- `save_file_to_nas(content, filename, nas_path)` - Save to NAS
- `read_file_from_nas(filename, nas_path)` - Read from NAS
- `save_file_to_local(content, filename, local_path)` - Local fallback
- `read_file_from_local(filename, local_path)` - Read from local

**Upload Flow**:
1. Generate UUID filename to prevent conflicts
2. Try NAS connection with `check_nas_connection()`
3. Save to NAS with `save_file_to_nas()`
4. If NAS fails, save to local with `save_file_to_local()`
5. Store only UUID filename in database (not full path)
6. Original filename preserved in database for display

**Download Flow** (ZIP generation):
1. Try reading from NAS with `read_file_from_nas()`
2. If NAS unavailable, read from local with `read_file_from_local()`
3. Include file in ZIP with original filename
4. Log warning if file not found in either location

### Storage Management
- UUID filenames prevent conflicts and path traversal attacks
- Original filenames preserved in database
- Database stores unique filename only (e.g., "abc123.stl")
- Automatic NAS connection caching to reduce connection overhead
- Graceful degradation to local storage when NAS unavailable
- Error handling at every storage operation

### File Limits
- Files: 25MB maximum (`MAX_PROJECT_FILE_SIZE`)
- Images: 10MB maximum (`MAX_PROJECT_IMAGE_SIZE`)
- Allowed file extensions: .py, .cpp, .h, .ino, .md, .txt, .pdf, .stl, .obj, .gcode, .json, .xml, .yaml, .yml
- Allowed image types: .png, .jpg, .jpeg, .gif, .webp, .svg
- Extension checking before upload
- Size validation before accepting upload

### ZIP Download & README Generation

Users can download complete projects as a single ZIP file with an auto-generated README.

#### Features
- **One-click download**: GET `/api/projects/{id}/download` returns complete project bundle
- **Auto-generated README**: Comprehensive markdown documentation created on-the-fly
- **Organized structure**: Files and images in separate subdirectories
- **Download tracking**: Increments `project.download_count` on each download
- **Efficient**: In-memory ZIP generation with streaming response (no temp files)
- **Safe filenames**: Sanitizes project title for ZIP filename

#### ZIP Structure
```
My_Robot_Project_project.zip
├── README.md
├── files/
│   ├── arduino_code.ino
│   ├── schematic.pdf
│   └── 3d_model.stl
└── images/
    ├── finished_robot.jpg
    ├── assembly_step1.png
    └── wiring_diagram.png
```

#### README Contents
The auto-generated `README.md` includes:
1. **Header**: Title, description, author, dates, tags
2. **Background**: Project backstory (if provided)
3. **Source Code Link**: GitHub/GitLab link (if provided)
4. **Build Instructions**: All steps with numbered sections
5. **Bill of Materials**: Table with items, quantities, prices, descriptions
6. **Electronic Components**: Table with components, quantities, datasheets
7. **Tools & Materials**: Bulleted list of required tools
8. **Additional Resources**: Links to videos, courses, articles, documentation
9. **File Listing**: All included files with titles, descriptions, and sizes
10. **Image Listing**: All included images with captions
11. **Footer**: Attribution, download date, kevsrobots.com link

#### Technical Details
- Uses Python `zipfile` library for ZIP creation
- `StreamingResponse` for efficient large file delivery
- Markdown formatting for GitHub/GitLab compatibility
- Proper table formatting for BOM and components
- UTF-8 encoding for international characters
- MIME type: `application/zip`
- Content-Disposition header for download prompt

## Technical Implementation

### FastAPI Router
- Modular router in `app/projects.py`
- Registered with `/api` prefix in main application
- All endpoints documented with OpenAPI schemas
- Automatic request validation via Pydantic
- Automatic response serialization

### SQLModel Models
- `app/project_models.py` contains all 10 models
- Relationships defined with cascade deletes
- Explicit table names match database schema
- Type hints for all fields

### Authentication Integration
- Uses existing auth system from `app/auth.py`
- `get_current_user` dependency for protected routes
- `get_optional_user` for public routes with optional auth
- JWT tokens in HTTP-only cookies

### Logging
- Structured logging for all operations
- User actions logged with username
- File operations logged with sizes
- Errors logged with full context

## Migration

### Database Migration (016)
- SQL script: `migrations/versions/016_create_user_projects.sql`
- Creates all 11 tables with proper constraints
- Creates all indexes
- Updates schema_version table
- Rollback script: `016_create_user_projects_rollback.sql`

### Deployment Steps
1. Run migration: `docker exec chatter-app python3 migrate.py`
2. Verify tables created
3. Ensure volume mount for `/app/data/projects/`
4. Set permissions on host directory
5. Rebuild and deploy Docker image

## Completed Features

### Phase 1 & 2 - Core Functionality (DONE)
- ✅ Complete project CRUD operations
- ✅ 37 REST API endpoints covering all project aspects
- ✅ File and image upload with size limits and validation
- ✅ Draft/publish workflow
- ✅ Gallery with filtering, sorting, and pagination
- ✅ Comprehensive child resource management (steps, BOM, components, links, tools)

### Phase 3 - Integration (DONE)
- ✅ Extended likes system to support entity-based likes (projects, etc.)
- ✅ Extended comments system to support entity-based comments
- ✅ Project download counts tracking
- ✅ ZIP download with auto-generated README

## Future Enhancements

### Phase 4 - Advanced Features (TODO)
- Project forking/cloning
- Version history
- Collaboration (multiple authors)
- Project templates
- Advanced search with full-text indexing
- Recommended projects based on tags
- User project collections/folders
- User project activity feed

## Testing Requirements
- Unit tests for all 37 endpoints
- Authorization tests (public, authenticated, author-only)
- File upload validation tests
- Database cascade delete tests
- Error handling tests (404, 403, 400)
- Code coverage minimum 80%

## Success Metrics
- Number of projects created
- Number of published projects
- Project view counts
- File download counts
- User engagement (likes, comments on projects)
- Search and filter usage analytics