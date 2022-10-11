-- Migration SQL script to transform the old Telegram-only database format to the new core schema.
-- Do not use it directly, but rather use it as a template and replace the placeholder variables,
-- e.g. the database names ('original' is the source, 'core' is the core, 'telegram' is the bot). 
-- It's expected that all databases and tables already exist and that a community user has been added.
-- Furthermore, exactly one application has to exist, which will be used as the new Telegram reference.
-- Other than that, the tables should be empty (if they aren't this leads to undefined behavior).

BEGIN;

UPDATE users AS new_users
    JOIN original.users AS old_users
        ON old_users.tid IS NULL
SET new_users.created=old_users.created
WHERE special = 1;

INSERT INTO users (balance,active,external,permission,name,created)
SELECT balance,TRUE,FALSE,TRUE,username,created FROM original.users
WHERE tid IS NOT NULL;

INSERT INTO aliases (user_id,application_id,username,confirmed)
SELECT new_users.id,1,old_users.tid,TRUE
FROM original.users AS old_users
    JOIN users AS new_users
        ON new_users.name = old_users.username
WHERE old_users.tid IS NOT NULL;

INSERT INTO transactions (sender_id,receiver_id,amount,reason,timestamp)
SELECT new_users_sender.id,new_users_receiver.id,old_transactions.amount,old_transactions.reason,old_transactions.registered
FROM original.transactions AS old_transactions
    JOIN original.users AS old_users_sender
        ON old_transactions.sender = old_users_sender.id
    JOIN original.users AS old_users_receiver
        ON old_transactions.receiver = old_users_receiver.id
    JOIN users AS new_users_sender
        ON new_users_sender.name = old_users_sender.username
    JOIN users AS new_users_receiver
        ON new_users_receiver.name = old_users_receiver.username;

UPDATE users AS new_users
    JOIN original.users AS old_users
        ON new_users.name = old_users.username
SET new_users.permission=old_users.permission
WHERE old_users.username = new_users.name;

UPDATE users AS new_users
    JOIN original.users AS old_users
        ON new_users.name = old_users.username
    JOIN original.externals AS old_externals
        ON old_users.id = old_externals.external
    LEFT JOIN original.users AS old_users_voucher
        ON old_externals.internal = old_users_voucher.id
    LEFT JOIN users as new_users_voucher
        ON new_users_voucher.name = old_users_voucher.username
SET new_users.external=(old_externals.external IS NOT NULL),new_users.voucher_id=new_users_voucher.id
WHERE old_users.username = new_users.name
    AND new_users.special IS NULL;

-- The base amount field will be misused to identify the old collective table temporarily
INSERT INTO multi_transactions (base_amount,registered)
SELECT old_collectives.id,old_collectives.created
FROM original.collectives AS old_collectives
WHERE old_collectives.communistic = 1;

INSERT INTO communisms (active,amount,description,created,creator_id,multi_transaction_id)
SELECT old_collectives.active,old_collectives.amount,old_collectives.description,old_collectives.created,new_users.id,mt.id
FROM original.collectives AS old_collectives
    JOIN original.users AS old_users
        ON old_users.id = old_collectives.creator
    JOIN users AS new_users
        ON new_users.name = old_users.username
    JOIN multi_transactions AS mt
        ON mt.base_amount = old_collectives.id;

INSERT INTO communisms_users (communism_id,user_id,quantity)
SELECT new_comm.id,new_users.id,1
FROM original.collectives_users AS old_coll_users
    JOIN original.collectives AS old_colls
        ON old_colls.id = old_coll_users.collectives_id AND old_colls.communistic = 1
    JOIN original.users AS old_users
        ON old_users.id = old_coll_users.users_id
    JOIN users AS new_users
        ON new_users.name = old_users.username
    JOIN multi_transactions AS mt
        ON mt.base_amount = old_colls.id
    JOIN communisms AS new_comm
        ON new_comm.multi_transaction_id = mt.id;

UPDATE multi_transactions
SET base_amount=1;

INSERT INTO ballots (id,modified)
SELECT old_colls.id,old_colls.created
FROM original.collectives AS old_colls
WHERE old_colls.communistic = 0;

INSERT INTO refunds (amount,description,active,created,creator_id,ballot_id,transaction_id)
SELECT old_colls.amount,old_colls.description,old_colls.active,old_colls.created,new_users.id,new_ballots.id,NULL
FROM original.collectives AS old_colls
    JOIN original.users AS old_users
        ON old_users.id = old_colls.creator
    JOIN users AS new_users
        ON new_users.name = old_users.username
    JOIN ballots AS new_ballots
        ON new_ballots.id = old_colls.id
WHERE old_colls.communistic = 0;

INSERT INTO votes (vote,ballot_id,user_id,modified)
SELECT old_colls_users.vote,new_ballots.id,new_users.id,old_colls.created
FROM original.collectives AS old_colls
    JOIN original.collectives_users AS old_colls_users
        ON old_colls.id = old_colls_users.collectives_id
    JOIN original.users AS old_users
        ON old_users.id = old_colls_users.users_id
    JOIN ballots AS new_ballots
        ON new_ballots.id = old_colls.id
    JOIN users AS new_users
        ON new_users.name = old_users.username
WHERE old_colls.communistic = 0;

COMMIT;
