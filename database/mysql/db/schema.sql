CREATE TABLE operation_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    is_success BOOLEAN NOT NULL,
    is_technical_error BOOLEAN NOT NULL,
    timestamp_field TIMESTAMP(6) NOT NULL
);