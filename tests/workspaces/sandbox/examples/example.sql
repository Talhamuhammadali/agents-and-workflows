-- Sample SQL commands

-- Create a table
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL
);

-- Insert some data
INSERT INTO users (id, username, email) VALUES
(1, 'john_doe', 'john.doe@example.com'),
(2, 'jane_doe', 'jane.doe@example.com');

-- Select data
SELECT * FROM users;
