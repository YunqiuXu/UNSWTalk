#!/usr/bin/env python3
# encoding: utf-8

# Build database from dataset
# How to run: ./build_db.py

import os
import re
import sys
import sqlite3
from collections import defaultdict
import shutil


dataset = "dataset-medium"


# Function: get_key_value
# Split a line as key - value
def get_key_value(line):
    line = line.split(':', maxsplit = 1)
    key = line[0]
    value = line[1]
    value = value.strip()
    # value maybe a list, e.g. friends, courses
    if re.match(r"^\(.+\)$", value):
        value = re.sub(r'(^\(|\)$)', '', value)
        if value != "":
            values = value.split(',') 
            values = [value.strip() for value in values]
        else:
            values = []
        return key, values
    return key, value


# Function: get_item_dict
# Read a file and transform all lines as key-value pairs
def get_item_dict(file_path):
    # return null if key does not exist
    item_dict = defaultdict(lambda: 'null')
    with open(file_path, 'r') as f:
        for line in f.readlines():
            line = line.rstrip('\n')
            key, value = get_key_value(line)
            item_dict[key] = value
    return item_dict


# Function: check_dir
# check whether a dir is exist, otherwise create it
def check_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)


# Function: get_student_dict
# Transform a student's profile as dict
def get_student_dict(dataset, zid):
    # Get student's profile dict
    file_path = "db/{}/{}/student.txt".format(dataset, zid)
    student_dict = get_item_dict(file_path)
    
    # Build dir to store images
    check_dir("static/student_img")
    check_dir("static/student_img/{}/".format(dataset))
    check_dir("static/student_img/{}/{}/".format(dataset, zid))

    # Copy images
    img_path = "db/{}/{}/img.jpg".format(dataset, zid)
    if os.path.exists(img_path):
        dest_path = "static/student_img/{}/{}/img.jpg".format(dataset, zid)
        student_dict["profile_img"] = "student_img/{}/{}/img.jpg".format(dataset, zid)
        shutil.copyfile(img_path, dest_path)
    else:
        # default_img
        student_dict["profile_img"] = "img/default.png"

    # Default profile_text
    student_dict["profile_text"] = ""

    return student_dict


# Function: get all posts in folder "zid"
def get_posts(dataset, zid):
    posts = []
    file_path = "db/{}/{}".format(dataset, zid)
    for curr_file in os.listdir(file_path):
        if re.match(r'[0-9]+\.txt', curr_file):
            posts.append(curr_file)
    return posts


# Function: get all comments in folder "zid"
def get_comments(dataset, zid, post):
    post_id = post[:-4]
    comments = []
    file_path = "db/{}/{}".format(dataset, zid)
    for curr_file in os.listdir(file_path):
        pattern = re.compile(post_id + "-[0-9]+\.txt")
        if re.match(pattern, curr_file):
            comments.append(curr_file)
    return comments


# Function: get all replies in folder "zid"
def get_replies(dataset, zid, comment):
    comment_id = comment[:-4]
    replies = []
    file_path = "db/{}/{}".format(dataset, zid)
    for curr_file in os.listdir(file_path):
        pattern = re.compile(comment_id + "-[0-9]+\.txt")
        if re.match(pattern, curr_file):
            replies.append(curr_file)
    return replies


# Main : generate database
if __name__ == "__main__":

    # Build tables
    dataset_path = "db/" + dataset
    db_filename = dataset + ".db"
    db_path = "db/" + db_filename
    os.system("sqlite3 db/{} < db/db_schema.sql".format(db_filename))
    
    # Get all students' profile
    student_zids = [f for f in os.listdir(dataset_path)]
    student_dicts = []
    for student_zid in student_zids:
        student_dicts.append(get_student_dict(dataset, student_zid))

    # Insert profiles into table STUDENT
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        to_be_insert = []
        for student_dict in student_dicts:
            to_be_insert.append((student_dict['zid'], student_dict['email'], student_dict['password'],
                                student_dict['full_name'], student_dict['birthday'], student_dict['profile_img'],
                                student_dict['program'], student_dict['home_suburb'], student_dict['home_longitude'], 
                                student_dict['home_latitude'], student_dict['profile_text']))
        insert_sql = "INSERT INTO STUDENT VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        result = cur.executemany(insert_sql, to_be_insert)

    # Insert friends into FRIENDS
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        for student_dict in student_dicts:
            for friend in student_dict['friends']:
                # remove same pairs
                cur.execute('DELETE FROM FRIENDS WHERE zid=? and friend_zid=?',[friend, student_dict['zid']])
                cur.execute('DELETE FROM FRIENDS WHERE zid=? and friend_zid=?',[student_dict['zid'], friend])
                # friendship between each other
                insert_friend_sql = "INSERT INTO FRIENDS(zid, friend_zid) VALUES (?, ?)"
                cur.executemany(insert_friend_sql, [(student_dict['zid'], friend)])
                insert_friend_sql = "INSERT INTO FRIENDS(zid, friend_zid) VALUES (?, ?)"
                cur.executemany(insert_friend_sql, [(friend, student_dict['zid'])])

    # Insert courses into COURSES
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        for student_dict in student_dicts:
            for course in student_dict['courses']:
                insert_course_sql = "INSERT INTO COURSES(zid, course) VALUES (?, ?)"
                cur.executemany(insert_course_sql, [(student_dict['zid'], course)])

    # Insert POST / COMMENT / REPLY  
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        post_id, comment_id, reply_id = 0, 0, 0
        for student_zid in student_zids:
            # Posts
            for post in get_posts(dataset, student_zid):
                post_dir = "db/{}/{}/{}".format(dataset, student_zid, post)
                post_dict = get_item_dict(post_dir)
                insert_post_sql = "INSERT INTO POST(id, zid, time, longitude, latitude, message) VALUES (?, ?, ?, ?, ?, ?)"
                post_id += 1
                cur.execute(insert_post_sql, [post_id, post_dict["from"], post_dict["time"], post_dict["longitude"], post_dict["latitude"], post_dict["message"]])
                # Comments
                for comment in get_comments(dataset, student_zid, post):
                    comment_dir = "db/{}/{}/{}".format(dataset, student_zid, comment)
                    comment_dict = get_item_dict(comment_dir)
                    insert_comment_sql = "INSERT INTO COMMENT(id, post_id, zid, time, message) VALUES (?, ?, ?, ?, ?)"
                    comment_id += 1
                    cur.execute(insert_comment_sql, [comment_id, post_id, comment_dict['from'], comment_dict['time'], comment_dict['message']])
                    # Replies
                    for reply in get_replies(dataset, student_zid, comment):
                        reply_dir = "db/{}/{}/{}".format(dataset, student_zid, reply)
                        reply_dict = get_item_dict(reply_dir)
                        insert_reply_sql = "INSERT INTO REPLY(id, comment_id, zid, time, message) VALUES (?, ?, ?, ?, ?)"
                        reply_id += 1
                        cur.execute(insert_reply_sql, [reply_id, comment_id, reply_dict['from'], reply_dict['time'], reply_dict['message']])

    print("Finished!")



