CREATE DATABASE organ_donation;
USE organ_donation;

-- Donors Table
CREATE TABLE donors (
    donor_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    age INT,
    blood_group VARCHAR(5),
    organ VARCHAR(50),
    city VARCHAR(50),
    contact VARCHAR(15)
);

-- Recipients Table
CREATE TABLE recipients (
    recipient_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    age INT,
    blood_group VARCHAR(5),
    organ_needed VARCHAR(50),
    city VARCHAR(50),
    urgency_level INT
);