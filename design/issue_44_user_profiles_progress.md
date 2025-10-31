# Issue #44: User Profiles - Implementation Progress

## Status: In Progress (40% Complete)

## Overview
Implementing user profile functionality including profile pictures stored on NAS, location field, bio, and public profile pages.

## Completed Tasks ✅

### 1. Database Schema Design
**File**: `app/models.py`

Added three new fields to the User model:
```python
profile_picture: Optional[str] = None  # Filename of profile picture stored on NAS
location: Optional[str] = None         # Country/location string
bio: Optional[str] = None             # Short biography/about me text
```

### 2. Database Migration
**Files**:
- `migrations/versions/013_add_user_profile_fields.sql`
- `migrations/versions/013_add_user_profile_fields_rollback.sql`

Migration adds three columns to the `user` table:
- `profile_picture` (VARCHAR) - stores filename only, not full path
- `location` (VARCHAR) - country/timezone information
- `bio` (TEXT) - longer biography text

### 3. Configuration Module
**File**: `app/config.py`

Created centralized configuration for:
- NAS storage settings (host, credentials from env vars)
- Image upload constraints (5MB max, allowed extensions)
- Profile picture dimensions (400x400 max)
- Local fallback storage path
- CORS and session settings

**Security**: Credentials loaded from environment variables, never hardcoded.

### 4. Storage Utility Module
**File**: `app/storage.py`

Comprehensive storage layer with:
- **NAS Connection Management**: SMB/CIFS connectivity with connection caching
- **Image Validation**: File type, size, and integrity checks
- **Image Processing**: Automatic resizing and optimization using Pillow
- **Dual Storage**: NAS primary, local fallback if NAS unavailable
- **Filename Generation**: Unique filenames with format `user_{id}_{uuid}.png`
- **Deletion**: Clean up from both NAS and local storage

Key Functions:
- `check_nas_connection()` - Verify NAS availability
- `validate_image()` - Validate uploaded files
- `resize_image()` - Resize while maintaining aspect ratio
- `save_profile_picture()` - Main save function with fallback logic
- `delete_profile_picture()` - Remove old pictures

### 5. Dependencies Added
**File**: `requirements.txt`

Added:
- `Pillow==11.0.0` - Image processing
- `smbprotocol==1.14.0` - SMB/CIFS NAS connectivity

## Pending Tasks 📋

### 6. Create Image Upload API Endpoint
**File**: `app/profile.py` (new)

Need to create:
- `POST /profile/picture` - Upload profile picture
- `PUT /profile` - Update profile fields (location, bio)
- `GET /profile/{username}` - View user profile (public)
- `GET /profile/me` - View own profile
- Static file serving for `/profile_pictures/{filename}`

### 7. Create Profile View API Endpoint
Part of `app/profile.py` above.

### 8. Create Profile Edit API Endpoint
Part of `app/profile.py` above.

### 9. Create Profile Page Template
**File**: `app/templates/profile.html` (new)

Need to create HTML template showing:
- Profile picture (circular)
- Username and join date
- Location (if set)
- Bio (if set)
- User's comments and posts
- "Edit Profile" button (if viewing own profile)

### 10. Create Profile Picture Upload UI
**File**: `app/templates/account.html` (update existing)

Add to existing account page:
- File upload form for profile picture
- Image preview before upload
- Location input field
- Bio textarea
- Save button

### 11. Add Profile Pictures to Comments/Posts
**Files**:
- `app/schemas.py` - Update CommentWithUser schema
- `app/likes_comments.py` - Include profile_picture in responses
- `web/assets/js/like-comment.js` - Display profile pictures

Need to:
- Add profile_picture to API responses
- Update frontend to show circular avatar images
- Fallback to default avatar if no picture

### 12. Add @mention Linking to Profiles
**Files**:
- `app/moderation.py` - Add @mention detection
- `web/assets/js/like-comment.js` - Convert @mentions to links

Need to:
- Detect @username patterns in comments
- Convert to clickable links to `/profile/{username}`
- Preserve existing content sanitization

### 13. Test Profile Functionality
Need to test:
- Image upload (various formats, sizes)
- NAS connectivity
- Fallback to local storage
- Profile viewing (own and others)
- Profile editing
- @mention links
- Profile pictures in comments

### 14. Update Database Documentation
**File**: `design/database.dbml`

Need to add:
- profile_picture field to User table
- location field to User table
- bio field to User table

## Architecture

### Storage Flow
```
User Upload → FastAPI Endpoint
    ↓
Validate Image (type, size)
    ↓
Resize to 400x400 (maintain aspect ratio)
    ↓
Generate Unique Filename (user_{id}_{uuid}.png)
    ↓
Try Save to NAS (192.168.1.79)
    ↓ (if fail)
Fallback to Local (/tmp/chatter_uploads)
    ↓
Store Filename in Database
```

### NAS Configuration
- **Protocol**: SMB/CIFS
- **Host**: 192.168.1.79
- **Username**: kevsrobots (from env var)
- **Password**: (from env var, never in code)
- **Share**: chatter
- **Path**: profile_pictures/

### Environment Variables Required
```bash
# For production deployment
export NAS_USERNAME="kevsrobots"
export NAS_PASSWORD="<password>"
export NAS_HOST="192.168.1.79"
export NAS_SHARE_NAME="chatter"
```

## API Endpoints (Planned)

### Profile Management
- `GET /profile/{username}` - View public profile
- `GET /profile/me` - View own profile
- `PUT /profile` - Update profile (location, bio)
- `POST /profile/picture` - Upload profile picture
- `DELETE /profile/picture` - Remove profile picture

### Static Files
- `GET /profile_pictures/{filename}` - Serve profile picture

## Security Considerations

### ✅ Implemented
- Image validation (type, size, integrity)
- Unique filename generation (prevents overwriting)
- User authentication required for uploads
- Users can only edit their own profiles
- Credentials in environment variables

### 🔒 To Implement
- Rate limiting on image uploads
- Virus scanning (future enhancement)
- Image content moderation (future enhancement)
- HTTPS-only for profile picture URLs

## Database Schema

```sql
ALTER TABLE "user" ADD COLUMN profile_picture VARCHAR;
ALTER TABLE "user" ADD COLUMN location VARCHAR;
ALTER TABLE "user" ADD COLUMN bio TEXT;
```

## Files Modified/Created

### New Files
- ✅ `app/config.py` - Configuration module
- ✅ `app/storage.py` - Storage utilities
- ✅ `migrations/versions/013_add_user_profile_fields.sql`
- ✅ `migrations/versions/013_add_user_profile_fields_rollback.sql`
- ⏳ `app/profile.py` - Profile API endpoints
- ⏳ `app/templates/profile.html` - Profile page template

### Modified Files
- ✅ `app/models.py` - Added profile fields to User model
- ✅ `requirements.txt` - Added Pillow and smbprotocol
- ⏳ `app/main.py` - Mount profile router
- ⏳ `app/schemas.py` - Update response schemas
- ⏳ `app/templates/account.html` - Add profile editing UI
- ⏳ `web/assets/js/like-comment.js` - Display profile pictures
- ⏳ `design/database.dbml` - Document schema changes

## Testing Plan

### Unit Tests
- Image validation functions
- Image resizing logic
- Filename generation
- NAS connection handling
- Fallback storage logic

### Integration Tests
- Upload profile picture (authenticated user)
- View profile page (public)
- Edit profile fields
- Delete profile picture
- @mention linking

### Manual Tests
- Upload various image formats (PNG, JPEG, GIF, WebP)
- Upload oversized images (>5MB)
- Upload invalid files (non-images)
- Test with NAS available
- Test with NAS unavailable (fallback)
- Test profile pictures in comments
- Test @mention links

## Deployment Steps

1. **Install Dependencies**
   ```bash
   pip install Pillow==11.0.0 smbprotocol==1.14.0
   ```

2. **Set Environment Variables**
   ```bash
   export NAS_USERNAME="kevsrobots"
   export NAS_PASSWORD="<password>"
   export NAS_HOST="192.168.1.79"
   export NAS_SHARE_NAME="chatter"
   ```

3. **Run Migration**
   ```bash
   psql -U chatter_user -d chatter -f migrations/versions/013_add_user_profile_fields.sql
   ```

4. **Test NAS Connectivity**
   ```python
   from app.storage import check_nas_connection
   print(check_nas_connection())  # Should return True
   ```

5. **Deploy Application**
   - Build Docker image
   - Push to registry
   - Update docker-compose with environment variables
   - Deploy to production

## Next Steps

1. Complete profile API endpoints
2. Create profile page template
3. Update account page with profile editing
4. Add profile pictures to comment display
5. Implement @mention linking
6. Test thoroughly
7. Update documentation

## Estimated Time Remaining
- API endpoints: 2-3 hours
- Templates/UI: 2-3 hours
- Profile pictures in comments: 1-2 hours
- @mention linking: 1 hour
- Testing: 2 hours
- Documentation: 1 hour
**Total: 9-12 hours**

## Notes
- Profile pictures are stored with UUID in filename to prevent conflicts
- NAS storage is preferred but local fallback ensures reliability
- Images are automatically resized to 400x400 max to save storage
- Circular display on frontend regardless of original image shape
- @mentions will be clickable links to user profiles
