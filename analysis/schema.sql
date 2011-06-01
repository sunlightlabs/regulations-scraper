
CREATE TABLE regulations_comments (
    document_id varchar(32) PRIMARY KEY NOT NULL,
    docket_id varchar(32) NOT NULL,
    agency varchar(8) NOT NULL,
    date date,
    text text NOT NULL
);
