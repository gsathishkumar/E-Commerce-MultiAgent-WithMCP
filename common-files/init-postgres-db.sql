-- Create Extension with SuperUser permission
CREATE EXTENSION IF NOT EXISTS vector;


-- Create User and set password
CREATE USER product_user WITH PASSWORD 'password123';

-- Create Product Schema and authorize 'product_user' as owner
CREATE SCHEMA product_schema AUTHORIZATION product_user;

-- Grant all privileges on Product Schema to 'product_user'
GRANT ALL PRIVILEGES ON SCHEMA product_schema TO product_user;

-- Optional: Set search path for 'product_user' to use product_schema by default
ALTER USER product_user SET search_path TO product_schema, public;



-- Create User and set password
CREATE USER refund_user WITH PASSWORD 'password456';

-- Create Refund Schema and authorize 'refund_user' as owner
CREATE SCHEMA refund_schema AUTHORIZATION refund_user;

-- Grant all privileges on Refund Schema to 'refund_user'
GRANT ALL PRIVILEGES ON SCHEMA refund_schema TO refund_user;

-- Optional: Set search path for 'refund_user' to use refund_schema by default
ALTER USER refund_user SET search_path TO refund_schema, public;
