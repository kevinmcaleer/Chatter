-- Migration: Create User Projects (Issue #15)
-- Description: Create tables for user-generated project content with all mandatory and optional fields

-- Create project table
CREATE TABLE IF NOT EXISTS project (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    author_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    background TEXT,  -- Markdown content
    code_link VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    primary_image_id INTEGER,  -- Will be set after project_image is created
    view_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0
);

-- Create indexes for project table
CREATE INDEX idx_project_author ON project(author_id);
CREATE INDEX idx_project_status ON project(status);
CREATE INDEX idx_project_created ON project(created_at DESC);

-- Create project_tag table
CREATE TABLE IF NOT EXISTS project_tag (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    tag_name VARCHAR(100) NOT NULL,
    UNIQUE(project_id, tag_name)
);

CREATE INDEX idx_project_tag_name ON project_tag(tag_name);
CREATE INDEX idx_project_tag_project ON project_tag(project_id);

-- Create project_step table
CREATE TABLE IF NOT EXISTS project_step (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,  -- Markdown
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, step_number)
);

CREATE INDEX idx_project_step_project ON project_step(project_id, step_number);

-- Create bill_of_material table
CREATE TABLE IF NOT EXISTS bill_of_material (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    quantity INTEGER NOT NULL DEFAULT 1,
    price_cents INTEGER,  -- Price in cents, nullable
    item_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_bom_project ON bill_of_material(project_id, item_order);

-- Create component table (reusable electronic components)
CREATE TABLE IF NOT EXISTS component (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    datasheet_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_component_name ON component(name);

-- Create project_component table (many-to-many with quantities)
CREATE TABLE IF NOT EXISTS project_component (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES component(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    UNIQUE(project_id, component_id)
);

CREATE INDEX idx_project_component_project ON project_component(project_id);
CREATE INDEX idx_project_component_component ON project_component(component_id);

-- Create project_file table (downloadable files with 25MB limit enforced in application)
CREATE TABLE IF NOT EXISTS project_file (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,  -- Stored filename
    original_filename VARCHAR(255) NOT NULL,  -- User's original filename
    file_size INTEGER NOT NULL,  -- Size in bytes
    file_type VARCHAR(100),  -- MIME type
    description TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_project_file_project ON project_file(project_id);

-- Create project_image table (with drag-drop ordering)
CREATE TABLE IF NOT EXISTS project_image (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,  -- Stored filename
    original_filename VARCHAR(255) NOT NULL,  -- User's original filename
    display_order INTEGER NOT NULL DEFAULT 0,
    caption TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_project_image_project ON project_image(project_id, display_order);

-- Add foreign key constraint for primary_image_id (after project_image table exists)
ALTER TABLE project
    ADD CONSTRAINT fk_project_primary_image
    FOREIGN KEY (primary_image_id)
    REFERENCES project_image(id)
    ON DELETE SET NULL;

-- Create project_link table (external resources)
CREATE TABLE IF NOT EXISTS project_link (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    title VARCHAR(255) NOT NULL,
    link_type VARCHAR(50) NOT NULL CHECK (link_type IN ('resource', 'video', 'course', 'article', 'related_project')),
    description TEXT
);

CREATE INDEX idx_project_link_project ON project_link(project_id);
CREATE INDEX idx_project_link_type ON project_link(link_type);

-- Create tool_material table
CREATE TABLE IF NOT EXISTS tool_material (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    tool_type VARCHAR(20) NOT NULL CHECK (tool_type IN ('tool', 'material')),
    notes TEXT
);

CREATE INDEX idx_tool_material_project ON tool_material(project_id);

-- Update schema_version
INSERT INTO schema_version (version, description, applied_at)
VALUES (16, 'Create user projects tables (Issue #15)', CURRENT_TIMESTAMP);
