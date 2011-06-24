
CREATE TABLE regulations_comments (
    document_id varchar(32) PRIMARY KEY NOT NULL,
    docket_id varchar(32) NOT NULL,
    agency varchar(8) NOT NULL,
    date date,
    text text NOT NULL
);

DROP TABLE IF EXISTS regulations_comments_full;
CREATE TABLE regulations_comments_full (
    document_id varchar(32) PRIMARY KEY NOT NULL,
    docket_id varchar(32) NOT NULL,
    agency varchar(8) NOT NULL,
    date_posted date,
    date_due date,
    title varchar(512) NOT NULL,
    type varchar(32) NOT NULL,
    org_name varchar(255) NOT NULL,
    on_type varchar(32) NOT NULL,
    on_id varchar(32) NOT NULL,
    on_title varchar(512) NOT NULL,
    text text NOT NULL
);


-- this should replace some fields on the comment
CREATE TABLE regulations_dockets (
    docket_id varchar(32) PRIMARY KEY NOT NULL,
    title varchar(255) NOT NULL,
    agency varchar(8) NOT NULL,
    date date
);

CREATE TABLE regulations_matches (
    document_id varchar(32),
    entity_id uuid
);




