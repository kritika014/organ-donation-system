CREATE DATABASE IF NOT EXISTS organ_donation;
USE organ_donation;

-- -----------------------------
-- 1) LOOKUP TABLES
-- -----------------------------
CREATE TABLE IF NOT EXISTS blood_groups (
    blood_group VARCHAR(5) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS organ_types (
    organ VARCHAR(50) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS cities (
    city VARCHAR(50) PRIMARY KEY
);

-- Donor blood group -> recipient blood group compatibility
CREATE TABLE IF NOT EXISTS blood_compatibility (
    donor_blood_group VARCHAR(5) NOT NULL,
    recipient_blood_group VARCHAR(5) NOT NULL,
    PRIMARY KEY (donor_blood_group, recipient_blood_group),
    FOREIGN KEY (donor_blood_group) REFERENCES blood_groups(blood_group),
    FOREIGN KEY (recipient_blood_group) REFERENCES blood_groups(blood_group)
);

-- -----------------------------
-- 2) MAIN TABLES
-- -----------------------------
CREATE TABLE IF NOT EXISTS donors (
    donor_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    age INT NOT NULL CHECK (age >= 0 AND age <= 120),
    blood_group VARCHAR(5) NOT NULL,
    organ VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    contact VARCHAR(20),
    FOREIGN KEY (blood_group) REFERENCES blood_groups(blood_group),
    FOREIGN KEY (organ) REFERENCES organ_types(organ),
    FOREIGN KEY (city) REFERENCES cities(city)
);

CREATE TABLE IF NOT EXISTS recipients (
    recipient_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    age INT NOT NULL CHECK (age >= 0 AND age <= 120),
    blood_group VARCHAR(5) NOT NULL,
    organ_needed VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    urgency_level INT NOT NULL CHECK (urgency_level >= 1 AND urgency_level <= 5),
    FOREIGN KEY (blood_group) REFERENCES blood_groups(blood_group),
    FOREIGN KEY (organ_needed) REFERENCES organ_types(organ),
    FOREIGN KEY (city) REFERENCES cities(city)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT NOT NULL,
    recipient_id INT NOT NULL,
    score INT NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_donor_recipient (donor_id, recipient_id),
    FOREIGN KEY (donor_id) REFERENCES donors(donor_id),
    FOREIGN KEY (recipient_id) REFERENCES recipients(recipient_id)
);

-- Helpful indexes for faster matching
CREATE INDEX idx_donors_match ON donors (blood_group, organ, city);
CREATE INDEX idx_recipients_match ON recipients (blood_group, organ_needed, city, urgency_level);

-- -----------------------------
-- 3) MASTER DATA
-- -----------------------------
INSERT IGNORE INTO blood_groups (blood_group) VALUES
('O-'), ('O+'), ('A-'), ('A+'), ('B-'), ('B+'), ('AB-'), ('AB+');

INSERT IGNORE INTO organ_types (organ) VALUES
('Kidney'), ('Liver'), ('Heart'), ('Lung'), ('Pancreas');

INSERT IGNORE INTO cities (city) VALUES
('Mumbai'), ('Delhi'), ('Bengaluru'), ('Hyderabad'), ('Chennai'),
('Kolkata'), ('Pune'), ('Ahmedabad'), ('Jaipur'), ('Lucknow');

-- ABO + Rh compatibility (RBC donation style)
INSERT IGNORE INTO blood_compatibility (donor_blood_group, recipient_blood_group) VALUES
('O-','O-'), ('O-','A-'), ('O-','B-'), ('O-','AB-'),
('O+','O+'), ('O+','A+'), ('O+','B+'), ('O+','AB+'),
('A-','A-'), ('A-','AB-'),
('A+','A+'), ('A+','AB+'),
('B-','B-'), ('B-','AB-'),
('B+','B+'), ('B+','AB+'),
('AB-','AB-'),
('AB+','AB+');

-- -----------------------------
-- 4) BULK DATA (5000+ records total)
-- -----------------------------
-- 3000 donors
INSERT INTO donors (name, age, blood_group, organ, city, contact)
WITH RECURSIVE seq AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 3000
)
SELECT
    CONCAT('Donor_', n) AS name,
    18 + (n MOD 43) AS age,
    ELT((n MOD 8) + 1, 'O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+') AS blood_group,
    ELT((n MOD 5) + 1, 'Kidney', 'Liver', 'Heart', 'Lung', 'Pancreas') AS organ,
    ELT((n MOD 10) + 1, 'Mumbai', 'Delhi', 'Bengaluru', 'Hyderabad', 'Chennai',
                       'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow') AS city,
    CONCAT('+91', LPAD(FLOOR(RAND(n) * 1000000000), 10, '0')) AS contact
FROM seq;

-- 3000 recipients
INSERT INTO recipients (name, age, blood_group, organ_needed, city, urgency_level)
WITH RECURSIVE seq2 AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n + 1 FROM seq2 WHERE n < 3000
)
SELECT
    CONCAT('Recipient_', n) AS name,
    1 + (n MOD 80) AS age,
    ELT((n MOD 8) + 1, 'O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+') AS blood_group,
    ELT((n MOD 5) + 1, 'Kidney', 'Liver', 'Heart', 'Lung', 'Pancreas') AS organ_needed,
    ELT((n MOD 10) + 1, 'Mumbai', 'Delhi', 'Bengaluru', 'Hyderabad', 'Chennai',
                       'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow') AS city,
    1 + (n MOD 5) AS urgency_level
FROM seq2;

-- -----------------------------
-- 5) STEP-3 MATCHING QUERIES
-- -----------------------------
-- BASIC matching:
-- conditions = compatible blood group + same organ + same city
SELECT
    r.recipient_id,
    r.name AS recipient_name,
    r.blood_group AS recipient_blood,
    r.organ_needed,
    r.city,
    d.donor_id,
    d.name AS donor_name,
    d.blood_group AS donor_blood
FROM recipients r
JOIN donors d
    ON d.organ = r.organ_needed
   AND d.city = r.city
JOIN blood_compatibility bc
    ON bc.donor_blood_group = d.blood_group
   AND bc.recipient_blood_group = r.blood_group
ORDER BY r.recipient_id, d.donor_id;

-- ADVANCED scoring-based matching:
-- +50: blood compatible
-- +30: organ match (already in WHERE/JOIN)
-- +20: same city (already in WHERE/JOIN)
-- +urgency_level*10: urgency weight
SELECT
    r.recipient_id,
    r.name AS recipient_name,
    r.urgency_level,
    d.donor_id,
    d.name AS donor_name,
    (
        50 + 30 + 20 + (r.urgency_level * 10)
    ) AS match_score
FROM recipients r
JOIN donors d
    ON d.organ = r.organ_needed
   AND d.city = r.city
JOIN blood_compatibility bc
    ON bc.donor_blood_group = d.blood_group
   AND bc.recipient_blood_group = r.blood_group
ORDER BY r.urgency_level DESC, match_score DESC, r.recipient_id, d.donor_id;

-- Save top match candidates (top 1 donor per recipient) in matches table
INSERT INTO matches (donor_id, recipient_id, score)
SELECT donor_id, recipient_id, score
FROM (
    SELECT
        d.donor_id,
        r.recipient_id,
        (50 + 30 + 20 + (r.urgency_level * 10)) AS score,
        ROW_NUMBER() OVER (
            PARTITION BY r.recipient_id
            ORDER BY r.urgency_level DESC, d.donor_id
        ) AS rn
    FROM recipients r
    JOIN donors d
        ON d.organ = r.organ_needed
       AND d.city = r.city
    JOIN blood_compatibility bc
        ON bc.donor_blood_group = d.blood_group
       AND bc.recipient_blood_group = r.blood_group
) ranked
WHERE rn = 1
ON DUPLICATE KEY UPDATE score = VALUES(score), matched_at = CURRENT_TIMESTAMP;

-- Counts to verify data volume
SELECT COUNT(*) AS donor_count FROM donors;
SELECT COUNT(*) AS recipient_count FROM recipients;