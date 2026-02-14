# Database Schema

Complete database schema documentation for Chatter.

## Database Server

**Production:** PostgreSQL 14+ at `192.168.2.3:5433`
**Database Name:** `kevsrobots_cms`

## Schema Overview

Chatter uses 4 main tables:
- `user` - User accounts and authentication
- `accountlog` - Audit trail of account changes
- `like` - User likes/favorites
- `comment` - User comments

## Tables

### user

Stores user account information and authentication data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique user identifier |
| `username` | VARCHAR | UNIQUE, NOT NULL, INDEXED | Unique username for login |
| `firstname` | VARCHAR | NOT NULL, DEFAULT '' | User's first name |
| `lastname` | VARCHAR | NOT NULL, DEFAULT '' | User's last name |
| `date_of_birth` | DATE | NULLABLE | User's date of birth (optional) |
| `email` | VARCHAR | UNIQUE, NOT NULL, INDEXED | Unique email address |
| `status` | VARCHAR | NOT NULL, DEFAULT 'active' | Account status: 'active' or 'inactive' |
| `hashed_password` | VARCHAR | NOT NULL | Bcrypt hashed password |
| `type` | INTEGER | DEFAULT 0 | User type: 0=regular user, 1=admin |
| `force_password_reset` | BOOLEAN | DEFAULT FALSE | Admin can force password reset on next login |
| `password_reset_code` | VARCHAR | NULLABLE, INDEXED (partial) | One-time 8-character reset code |
| `code_expires_at` | TIMESTAMP | NULLABLE | Expiration time for reset code (24 hours) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last account update timestamp |
| `last_login` | TIMESTAMP | NULLABLE, INDEXED | Last successful login timestamp |

**Indexes:**
- `PRIMARY KEY` on `id`
- `UNIQUE INDEX` on `username`
- `UNIQUE INDEX` on `email`
- `INDEX` on `last_login` (for engagement queries)
- `PARTIAL INDEX` on `password_reset_code` WHERE `password_reset_code IS NOT NULL`

**Constraints:**
- Username must be unique
- Email must be unique
- Status must be 'active' or 'inactive'

**Example Row:**
```sql
INSERT INTO "user" (username, firstname, lastname, email, hashed_password, type)
VALUES ('johndoe', 'John', 'Doe', 'john@example.com', '$2b$12$...', 0);
```

---

### accountlog

Audit trail of account modifications for compliance and security.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique log entry identifier |
| `user_id` | INTEGER | NOT NULL, FOREIGN KEY → user.id | User whose account was modified |
| `action` | VARCHAR | NOT NULL | Action type: 'created', 'updated', 'activated', 'deactivated', 'deleted' |
| `field_changed` | VARCHAR | NULLABLE | Specific field that was changed |
| `old_value` | VARCHAR | NULLABLE | Previous value before change |
| `new_value` | VARCHAR | NULLABLE | New value after change |
| `changed_by` | INTEGER | NULLABLE, FOREIGN KEY → user.id | User who made the change (for admin actions) |
| `changed_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | When the change occurred |
| `ip_address` | VARCHAR | NULLABLE | IP address of the request |
| `user_agent` | VARCHAR | NULLABLE | User agent string of the request |

**Foreign Keys:**
- `user_id` → `user.id` (CASCADE DELETE)
- `changed_by` → `user.id` (SET NULL on delete)

**Example Row:**
```sql
INSERT INTO accountlog (user_id, action, field_changed, old_value, new_value, changed_by, ip_address)
VALUES (1, 'updated', 'email', 'old@example.com', 'new@example.com', 1, '192.168.1.100');
```

---

### like

Stores user likes/favorites for content across the Kev's Robots ecosystem.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique like identifier |
| `url` | VARCHAR | NOT NULL | URL of the liked content |
| `user_id` | INTEGER | NOT NULL, FOREIGN KEY → user.id | User who liked the content |

**Foreign Keys:**
- `user_id` → `user.id` (CASCADE DELETE)

**Example Row:**
```sql
INSERT INTO like (url, user_id)
VALUES ('https://www.kevsrobots.com/blog/post-1', 1);
```

---

### comment

Stores user comments on content across the Kev's Robots ecosystem.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique comment identifier |
| `url` | VARCHAR | NOT NULL | URL of the commented content |
| `content` | VARCHAR | NOT NULL | Comment text |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | When comment was created |
| `user_id` | INTEGER | NOT NULL, FOREIGN KEY → user.id | User who created the comment |

**Foreign Keys:**
- `user_id` → `user.id` (CASCADE DELETE)

**Example Row:**
```sql
INSERT INTO comment (url, content, user_id)
VALUES ('https://www.kevsrobots.com/blog/post-1', 'Great article!', 1);
```

---

## Entity Relationships

```
user (1) ──< (many) accountlog [user_id]
user (1) ──< (many) accountlog [changed_by]
user (1) ──< (many) like
user (1) ──< (many) comment
```

**Cascade Behavior:**
- When a user is deleted:
  - All their `accountlog` entries are deleted
  - All their `like` entries are deleted
  - All their `comment` entries are deleted
  - `accountlog.changed_by` is set to NULL for logs they created

---

## Migrations

Database changes are managed through migration files in `migrations/versions/`:

| Migration | Description |
|-----------|-------------|
| `000_create_initial_schema.sql` | Initial tables (user, accountlog, like, comment) |
| `001_add_account_management_with_logging.sql` | Add account management fields |
| `002_add_last_login_tracking.sql` | Add last_login field and index |
| `003_add_force_password_reset.sql` | Add force_password_reset flag |
| `004_add_password_reset_code.sql` | Add password reset code fields |

**Migration Tracking:**
Migrations are tracked in the `schema_version` table (if it exists).

**Applying Migrations:**
Migrations are automatically applied on Docker container startup via `docker-entrypoint.sh`.

For manual application:
```bash
psql $DATABASE_URL -f migrations/versions/004_add_password_reset_code.sql
```

---

## Queries

### Common Queries

**Get user by username:**
```sql
SELECT * FROM "user" WHERE username = 'johndoe';
```

**Get admin users:**
```sql
SELECT * FROM "user" WHERE type = 1;
```

**Get active users:**
```sql
SELECT * FROM "user" WHERE status = 'active';
```

**Get users who haven't logged in recently:**
```sql
SELECT username, email, last_login
FROM "user"
WHERE last_login < NOW() - INTERVAL '30 days'
   OR last_login IS NULL
ORDER BY last_login ASC NULLS FIRST;
```

**Get user with activity counts:**
```sql
SELECT
  u.username,
  u.email,
  COUNT(DISTINCT l.id) as like_count,
  COUNT(DISTINCT c.id) as comment_count
FROM "user" u
LEFT JOIN "like" l ON u.id = l.user_id
LEFT JOIN "comment" c ON u.id = c.user_id
WHERE u.id = 1
GROUP BY u.id, u.username, u.email;
```

**Get users with pending password resets:**
```sql
SELECT username, password_reset_code, code_expires_at
FROM "user"
WHERE password_reset_code IS NOT NULL
  AND code_expires_at > NOW();
```

**Get account audit log for user:**
```sql
SELECT
  al.action,
  al.field_changed,
  al.old_value,
  al.new_value,
  al.changed_at,
  u2.username as changed_by_username
FROM accountlog al
JOIN "user" u ON al.user_id = u.id
LEFT JOIN "user" u2 ON al.changed_by = u2.id
WHERE u.username = 'johndoe'
ORDER BY al.changed_at DESC;
```

---

## Database Backups

**Backup Command:**
```bash
pg_dump -h 192.168.2.3 -p 5433 -U <username> -d kevsrobots_cms > backup_$(date +%Y%m%d).sql
```

**Restore Command:**
```bash
psql -h 192.168.2.3 -p 5433 -U <username> -d kevsrobots_cms < backup_20251023.sql
```

**Backup Schedule:** (Recommended)
- Daily automated backups
- Retain 7 daily backups
- Retain 4 weekly backups
- Retain 12 monthly backups

---

## Performance Considerations

**Indexed Columns:**
- `user.username` - Fast login lookups
- `user.email` - Fast email lookups
- `user.last_login` - Engagement queries
- `user.password_reset_code` - Reset code validation (partial index)

**Connection Pooling:**
SQLModel/SQLAlchemy connection pool settings:
- `pool_size=5` - Number of connections to maintain
- `max_overflow=10` - Additional connections when needed
- `pool_pre_ping=True` - Verify connections before use
- `pool_recycle=3600` - Recycle connections after 1 hour

---

## Database Security

✅ Passwords never stored in plaintext (bcrypt hashed)
✅ SQL injection protection via SQLModel ORM
✅ Database credentials stored in environment variables
✅ Database accessed via internal network only
✅ Regular backups maintained
✅ Audit logging for all account changes

---

## Schema Diagram

Visual representation using DBML (see `design/database.dbml`):

```dbml
Table user {
  id int [pk, increment]
  username varchar [unique, not null]
  firstname varchar [not null]
  lastname varchar [not null]
  date_of_birth datetime
  email varchar [unique, not null]
  status varchar [not null, default: 'active']
  hashed_password varchar [not null]
  type int [default: 0]
  force_password_reset boolean [default: false]
  password_reset_code varchar
  code_expires_at timestamp
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  last_login timestamp
}

Table accountlog {
  id int [pk, increment]
  user_id int [not null, ref: > user.id]
  action varchar [not null]
  field_changed varchar
  old_value varchar
  new_value varchar
  changed_by int [ref: > user.id]
  changed_at timestamp [default: `now()`]
  ip_address varchar
  user_agent varchar
}

Table like {
  id int [pk, increment]
  url varchar [not null]
  user_id int [not null, ref: > user.id]
}

Table comment {
  id int [pk, increment]
  url varchar [not null]
  content varchar [not null]
  created_at timestamp [default: `now()`]
  user_id int [not null, ref: > user.id]
}
```

Generate visual diagram at: https://dbdiagram.io/
