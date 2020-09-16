-- MateBot database table creation

CREATE TABLE users (
    `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    `tid` BIGINT UNIQUE,
    `username` VARCHAR(255),
    `name` VARCHAR(255) NOT NULL,
    `balance` MEDIUMINT NOT NULL DEFAULT 0,
    `permission` BOOLEAN NOT NULL DEFAULT false,
    `active` BOOLEAN NOT NULL DEFAULT true,
    `created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `accessed` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    `sender` INT NOT NULL,
    `receiver` INT NOT NULL,
    `amount` MEDIUMINT NOT NULL,
    `reason` VARCHAR(255),
    `registered` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE collectives (
    `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    `active` BOOLEAN NOT NULL DEFAULT true,
    `amount` MEDIUMINT NOT NULL,
    `externals` SMALLINT,
    `description` VARCHAR(255),
    `communistic` BOOLEAN NOT NULL,
    `creator` INT NOT NULL,
    `created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE collectives_users (
    `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    `collectives_id` INT NOT NULL,
    `users_id` INT NOT NULL,
    `vote` ENUM('-', '+') NOT NULL,
    FOREIGN KEY (collectives_id) REFERENCES collectives(id) ON DELETE CASCADE,
    FOREIGN KEY (users_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE collective_messages (
    `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    `collectives_id` INT NOT NULL,
    `chat_id` BIGINT NOT NULL,
    `msg_id` INT NOT NULL,
    FOREIGN KEY (collectives_id) REFERENCES collectives(id) ON DELETE CASCADE
);

CREATE TABLE externals (
    `id` INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    `internal` INT,
    `external` INT UNIQUE NOT NULL,
    `changed` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (internal) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (external) REFERENCES users(id) ON DELETE CASCADE
);
