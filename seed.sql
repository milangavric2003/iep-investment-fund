INSERT INTO users (forename, surname, email, password_hash, role)
VALUES
    ('Scrooge', 'McDuck', 'onlymoney@gmail.com', 'scrypt:32768:8:1$r6kU1DwACJYEN7JF$edf77b82c1c762feea231fbf22837cf493073a8e8a345569ea6329ffd32dfc3698356e3522c228fc809bca966355edd88682b2b6a4842df821574f47381d7f3b', 'DIRECTOR'),
    ('Alice', 'Johnson', 'alice.johnson@example.com', 'scrypt:32768:8:1$TX6JTQyxXNMWkcG7$dfcb5a54d61241e8a0f8c316fecb9c67945b2d01b2c6f13936964f2af00d93ba8acdacdf56a2ca4e36cd410b8a8cc80c528a879cb16539e571e2cf5795372d87', 'EMPLOYEE'),
    ('Bob', 'Smith', 'bob.smith@example.com', 'scrypt:32768:8:1$1wrbchOwNYIzXa4p$59aecc762ed0dac3545a8c965375b67a8e7921dd34de0d6003387a8a1b0bb059f309c4d5285f00cb4b5afbd10f1dd052629d5e40b25e2934be566a44bee24bd9', 'EMPLOYEE')

-- updating values if already exist in database
ON DUPLICATE KEY UPDATE
    forename = VALUES(forename),
    surname = VALUES(surname),
    password_hash = VALUES(password_hash),
    role = VALUES(role);