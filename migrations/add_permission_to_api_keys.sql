-- Add permission column with default value
ALTER TABLE api_keys 
ADD COLUMN permission VARCHAR(20) NOT NULL DEFAULT 'read';

-- Update existing keys to have read permission
UPDATE api_keys SET permission = 'read' WHERE permission IS NULL;
