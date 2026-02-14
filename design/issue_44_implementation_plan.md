# Issue #44: User Profile - Implementation Plan

## Overview
Implement user profile pages with profile pictures, account information, and user activity history.

## Requirements Summary

### Core Features
1. Profile page showing public user information
2. User statistics (join date, post count, comments)
3. Profile picture upload and display
4. Profile pictures in circular format next to posts/comments
5. Clickable usernames and @mentions linking to profile page

## Implementation Plan

### Phase 1: Database Schema Changes

#### 1.1 Add Profile Picture Fields to User Model
**File**: `app/models.py`

Add fields to User model:
```python
profile_picture_url: Optional[str] = None  # URL/path to profile picture
profile_picture_uploaded_at: Optional[datetime] = None  # Track when uploaded
bio: Optional[str] = None  # Short user bio (optional, max 500 chars)
```

**Migration**: `migrations/versions/011_add_profile_fields.sql`
```sql
ALTER TABLE user ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(500);
ALTER TABLE user ADD COLUMN IF NOT EXISTS profile_picture_uploaded_at TIMESTAMP;
ALTER TABLE user ADD COLUMN IF NOT EXISTS bio VARCHAR(500);
```

#### 1.2 Create Profile Views/Statistics
Consider creating a view for user statistics:
```sql
CREATE OR REPLACE VIEW user_statistics AS
SELECT
    u.id,
    u.username,
    u.created_at,
    COUNT(DISTINCT l.id) as like_count,
    COUNT(DISTINCT c.id) as comment_count
FROM user u
LEFT JOIN like l ON u.id = l.user_id
LEFT JOIN comment c ON u.id = c.user_id AND c.is_removed = false
GROUP BY u.id, u.username, u.created_at;
```

### Phase 2: Backend API Implementation

#### 2.1 Profile Picture Upload Endpoint
**File**: `app/profile.py` (new file)

Create new router for profile-related endpoints:
```python
@router.post("/upload-profile-picture")
async def upload_profile_picture(
    file: UploadFile,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
)
```

**Requirements**:
- Validate file type (png, jpeg, jpg, gif, webp)
- Validate file size (max 5MB)
- Resize/crop image to standard size (e.g., 200x200px)
- Generate unique filename
- Store in `/app/static/profile_pictures/` or cloud storage
- Update user.profile_picture_url in database
- Return URL of uploaded image

**Dependencies needed**:
- `Pillow` (PIL) for image processing
- `python-multipart` for file uploads (likely already installed)

#### 2.2 Get User Profile Endpoint
```python
@router.get("/profile/{username}")
def get_user_profile(username: str, session: Session = Depends(get_session))
```

**Returns**:
```json
{
  "username": "john_doe",
  "profile_picture_url": "/static/profile_pictures/abc123.jpg",
  "created_at": "2025-01-15T10:30:00Z",
  "account_age": "9 months",
  "comment_count": 42,
  "like_count": 156,
  "bio": "Python developer and robotics enthusiast"
}
```

#### 2.3 Update User Profile Endpoint
```python
@router.patch("/profile")
def update_profile(
    profile_update: ProfileUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
)
```

Allow updating:
- Bio
- Profile picture (via separate upload endpoint)

#### 2.4 Get User Comments Endpoint
```python
@router.get("/profile/{username}/comments")
def get_user_comments(
    username: str,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session)
)
```

Returns paginated list of user's comments (excluding removed ones).

### Phase 3: Frontend Implementation

#### 3.1 Profile Picture Display in Comments
**File**: `assets/js/like-comment.js`

Modify comment rendering to include profile picture:
```javascript
<div class="comment-author d-flex align-items-center">
  <img src="${comment.profile_picture_url || '/assets/img/default-avatar.png'}"
       class="rounded-circle me-2"
       width="32"
       height="32"
       alt="${escapeHtml(comment.username)}">
  <strong class="me-2">${escapeHtml(comment.username)}</strong>
  <span class="text-muted small">${timeAgo}</span>
</div>
```

Make username clickable:
```javascript
<a href="/profile/${encodeURIComponent(comment.username)}"
   class="text-decoration-none">
  <strong>${escapeHtml(comment.username)}</strong>
</a>
```

#### 3.2 Profile Page Template
**File**: `web/_includes/profile.html` (Jekyll template)

Create profile page layout:
```html
---
layout: default
title: {{ username }}'s Profile
---

<div class="container mt-5">
  <div class="row">
    <div class="col-md-3">
      <!-- Profile Picture -->
      <img id="profile-picture"
           src="/assets/img/default-avatar.png"
           class="rounded-circle img-fluid mb-3"
           alt="Profile Picture">

      <!-- Upload button (if viewing own profile) -->
      <div id="upload-section" style="display: none;">
        <input type="file" id="picture-upload" accept="image/*" class="form-control mb-2">
        <button id="upload-btn" class="btn btn-primary btn-sm">Upload Picture</button>
      </div>
    </div>

    <div class="col-md-9">
      <h2 id="username"></h2>
      <p class="text-muted" id="account-age"></p>

      <!-- Bio -->
      <div class="card mb-3">
        <div class="card-body">
          <h5 class="card-title">About</h5>
          <p id="user-bio" class="card-text"></p>
          <button id="edit-bio-btn" class="btn btn-sm btn-secondary" style="display: none;">Edit Bio</button>
        </div>
      </div>

      <!-- Statistics -->
      <div class="row mb-3">
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <h3 id="comment-count">0</h3>
              <p class="text-muted">Comments</p>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <h3 id="like-count">0</h3>
              <p class="text-muted">Likes Given</p>
            </div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="card text-center">
            <div class="card-body">
              <h3 id="member-since"></h3>
              <p class="text-muted">Member Since</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Comments -->
      <div class="card">
        <div class="card-header">
          <h5>Recent Comments</h5>
        </div>
        <div class="card-body" id="recent-comments">
          <!-- Populated by JavaScript -->
        </div>
      </div>
    </div>
  </div>
</div>

<script src="/assets/js/profile.js"></script>
```

#### 3.3 Profile Page JavaScript
**File**: `assets/js/profile.js` (new file)

Handle:
- Loading profile data from API
- Uploading profile pictures
- Editing bio
- Displaying recent comments
- Calculating account age (hours/days/months/years)

#### 3.4 @Mention Linking
**File**: `assets/js/like-comment.js`

Add function to parse and linkify @mentions in comments:
```javascript
function linkifyMentions(text) {
  return text.replace(/@(\w+)/g, '<a href="/profile/$1" class="mention">@$1</a>');
}
```

Apply to comment content before rendering.

### Phase 4: Static Assets

#### 4.1 Default Avatar Image
Create/add default avatar image:
- `web/assets/img/default-avatar.png`
- Circular placeholder (e.g., generic user icon)

#### 4.2 Profile Pictures Storage
Create directory structure:
```
app/static/
  profile_pictures/
    .gitkeep  # Keep directory in git
```

Add to `.gitignore`:
```
app/static/profile_pictures/*.jpg
app/static/profile_pictures/*.png
app/static/profile_pictures/*.gif
app/static/profile_pictures/*.webp
```

### Phase 5: Documentation Updates

#### 5.1 Database Schema Documentation
**File**: `design/database.dbml`

Update User table:
```dbml
Table user {
  // ... existing fields ...
  profile_picture_url varchar(500) [null, note: 'URL to profile picture']
  profile_picture_uploaded_at timestamp [null]
  bio varchar(500) [null, note: 'User bio (max 500 chars)']
}
```

#### 5.2 Epic Documentation
**File**: `design/epic.md`

Add section for User Profiles explaining:
- How profile pictures are uploaded and stored
- Profile page URL structure (`/profile/{username}`)
- Security considerations
- Image processing pipeline

#### 5.3 Deployment Tasks
**File**: `design/deployment_tasks.md`

Add:
```markdown
## Profile Pictures
- [ ] Create `/app/static/profile_pictures/` directory on production
- [ ] Set proper permissions (nginx/app user needs write access)
- [ ] Add nginx location block for serving static profile pictures
- [ ] Install Pillow package: `pip install Pillow`
- [ ] Run migration 011 to add profile fields
```

### Phase 6: Security & Validation

#### 6.1 File Upload Security
- Validate MIME type (don't trust file extension)
- Scan for malicious content (if possible)
- Limit file size (5MB max)
- Sanitize filename
- Store with unique, non-guessable names
- Validate image dimensions (reject suspicious files)

#### 6.2 Profile Access Control
- Public fields: username, profile_picture, bio, created_at, statistics
- Private fields: email, date_of_birth, password-related fields
- Users can only edit their own profile
- Usernames are public but email addresses are not

#### 6.3 Rate Limiting
Add rate limiting to upload endpoint:
```python
@limiter.limit("5/hour")  # Max 5 uploads per hour
@router.post("/upload-profile-picture")
```

### Phase 7: Testing

#### 7.1 Backend Tests
Create `tests/test_profile.py`:
- Test profile retrieval
- Test profile picture upload (valid formats)
- Test invalid file uploads (wrong type, too large)
- Test profile statistics calculation
- Test bio update

#### 7.2 Frontend Tests
- Test profile page loads correctly
- Test @mention linking
- Test profile picture displays in comments
- Test file upload UI

## Implementation Order

### Sprint 1: Backend Foundation
1. Migration 011 - Add profile fields to database
2. Create `app/profile.py` with basic endpoints
3. Implement profile retrieval endpoint
4. Update User schema with new fields

### Sprint 2: Profile Pictures
1. Install and configure Pillow
2. Implement profile picture upload endpoint
3. Add image validation and processing
4. Create static storage directory
5. Update comments endpoint to include profile_picture_url

### Sprint 3: Frontend - Comments
1. Add default avatar image
2. Update like-comment.js to display profile pictures
3. Make usernames clickable (link to profile)
4. Implement @mention linking

### Sprint 4: Profile Page
1. Create profile.html template
2. Implement profile.js
3. Add profile picture upload UI
4. Add bio editing UI
5. Display user statistics and recent comments

### Sprint 5: Testing & Polish
1. Write backend tests
2. Test file uploads thoroughly
3. Add rate limiting
4. Update documentation
5. Deploy to production

## Dependencies to Add

Add to `requirements.txt`:
```
Pillow>=10.0.0  # Image processing
python-multipart>=0.0.6  # Already likely installed, but ensure it's there
```

## Database Changes Summary

**New Migration**: 011_add_profile_fields.sql
- Add `profile_picture_url` to user table
- Add `profile_picture_uploaded_at` to user table
- Add `bio` to user table
- Optional: Create `user_statistics` view

## API Endpoints Summary

**New endpoints in `/profile` router**:
- `POST /profile/upload-profile-picture` - Upload profile picture
- `GET /profile/{username}` - Get user profile
- `GET /profile/{username}/comments` - Get user's comments
- `PATCH /profile` - Update own profile (bio)

**Modified endpoints**:
- `GET /comments/{url}` - Now includes profile_picture_url in response

## Frontend Files Summary

**New files**:
- `web/_includes/profile.html` - Profile page template
- `web/assets/js/profile.js` - Profile page functionality
- `web/assets/img/default-avatar.png` - Default profile picture

**Modified files**:
- `web/assets/js/like-comment.js` - Add profile pictures and clickable usernames

## Success Criteria

- [ ] Users can upload profile pictures (png, jpeg, gif, webp)
- [ ] Profile pictures display in circular format next to comments
- [ ] Profile page shows username, join date, and statistics
- [ ] Clicking username or @mention navigates to profile page
- [ ] Account age displays in appropriate units (hours/days/months/years)
- [ ] Users can update their bio
- [ ] File uploads are secure and validated
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Feature deployed to production

## Estimated Effort

- Backend: 8-10 hours
- Frontend: 6-8 hours
- Testing: 3-4 hours
- Documentation: 2 hours
- **Total**: 19-24 hours

## Risks & Considerations

1. **Storage**: Profile pictures will consume disk space. Consider:
   - Cloud storage (S3, Cloudflare R2) for scalability
   - Cleanup of old pictures when user uploads new one
   - Storage quotas

2. **Performance**: Image processing is CPU-intensive:
   - Consider async processing for large uploads
   - Cache resized images

3. **Security**: File uploads are a common attack vector:
   - Thorough validation required
   - Consider antivirus scanning for production

4. **Privacy**: Profile pages are public:
   - Ensure no private data is exposed
   - Consider adding privacy settings in future

## Future Enhancements (Out of Scope)

- Multiple profile picture sizes (thumbnail, medium, large)
- Image cropping/editing interface
- Cover photos
- Social media links
- Privacy settings (private profiles)
- Followers/following system
- Activity feed
