-- Database schema


-- Table : STUDENT
DROP TABLE IF EXISTS STUDENT;
CREATE TABLE STUDENT (
  zid            TEXT PRIMARY KEY NOT NULL,
  email          TEXT,
  password       TEXT             NOT NULL,
  full_name      TEXT,
  birthday       TEXT,
  profile_img    TEXT,
  program        TEXT,
  home_suburb    TEXT,
  home_longitude TEXT,
  home_latitude  TEXT,
  profile_text   TEXT
);


-- Table : TO_BE_CONFIRMED: store profile that has not been activated
DROP TABLE IF EXISTS TO_BE_CONFIRMED;
CREATE TABLE TO_BE_CONFIRMED(
  zid            TEXT PRIMARY KEY NOT NULL,
  email          TEXT             NOT NULL,
  password       TEXT             NOT NULL,
  full_name      TEXT,
  birthday       TEXT,
  profile_img    TEXT,
  program        TEXT,
  home_suburb    TEXT,
  home_longitude TEXT,
  home_latitude  TEXT,
  profile_text   TEXT,
  confirmation_code TEXT          NOT NULL
);


-- Table : TO_BE_SUSPENDED: store profile that is suspended
DROP TABLE IF EXISTS TO_BE_SUSPENDED;
CREATE TABLE TO_BE_SUSPENDED (
  zid            TEXT PRIMARY KEY NOT NULL,
  email          TEXT,
  password       TEXT             NOT NULL,
  full_name      TEXT,
  birthday       TEXT,
  profile_img    TEXT,
  program        TEXT,
  home_suburb    TEXT,
  home_longitude TEXT,
  home_latitude  TEXT,
  profile_text   TEXT
);


-- Table : FRIENDS
DROP TABLE IF EXISTS FRIENDS;
CREATE TABLE FRIENDS (
  id   INTEGER PRIMARY KEY   AUTOINCREMENT,
  zid  TEXT REFERENCES STUDENT (zid), 
  friend_zid  TEXT
);

-- Table : COURSES
DROP TABLE IF EXISTS COURSES;
CREATE TABLE COURSES (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  zid    TEXT REFERENCES STUDENT (zid),
  course TEXT
);

-- Table : POST
DROP TABLE IF EXISTS POST;
CREATE TABLE POST (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  zid       TEXT REFERENCES STUDENT (zid),
  time      TEXT,
  longitude TEXT,
  latitude  TEXT,
  message   TEXT
);

-- Table : COMMENT
DROP TABLE IF EXISTS COMMENT;
CREATE TABLE COMMENT (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER REFERENCES POST (id),
  zid     TEXT REFERENCES STUDENT (zid),
  time    TEXT,
  message TEXT
);

-- Table : REPLY
DROP TABLE IF EXISTS REPLY;
CREATE TABLE REPLY (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  comment_id INTEGER REFERENCES COMMENT (id),
  zid        TEXT REFERENCES STUDENT (zid),
  time       TEXT,
  message    TEXT
);


-----------------------------------------------------------
-- [level 3 Student Account Creation]
-- DROP TABLE IF EXISTS USER_SUSPEND;
-- CREATE TABLE USER_SUSPEND AS
--   SELECT *
--   FROM USER;
-----------------------------------------------------------












