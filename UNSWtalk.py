#!/usr/bin/env python3
# coding : utf-8

import os
import re
import sys
import sqlite3
from datetime import datetime
from flask import Flask, render_template, session, redirect, url_for, request, g
from werkzeug import secure_filename
import subprocess
import random
import string

# ------------------------------------------------------- #
#                Common Helper Functions                  #
# ------------------------------------------------------- #

# Global vars:
DATABASE_NAME = "dataset-medium"
DATABASE_PATH = "db/{}.db".format(DATABASE_NAME)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


# Function : transform message
# "\n" --> "<br>"
# zid --> full_name with link to homepage
def transform_message(message):
    message = re.sub(r'\\n', '<br>', message)
    zid_pattern = re.compile('z[0-9]{7}')
    zids = set(re.findall(zid_pattern, message))
    for curr_zid in zids:
        curr_profile = get_profile_by_zid(curr_zid)
        # if this zid exists --> replace it with link
        if curr_profile != None:
            link = '<a href="{}">{}</a>'.format(url_for('index', zid=curr_zid), curr_profile['full_name'])
            message = re.sub(curr_zid, link, message)
    return message


# Function : transform time
# 2016-05-13T04:35:53+0000 --> 2016-05-13 04:35:53
def transform_time(time):
    time = str(time)
    time = re.sub(r'\+[0-9]{4}', '', time)
    time = re.sub(r'T', ' ', time)
    return time


# Function: db_query
# Handle general database operations
# Input: 
#       sql: str, SQL script
#       params: list, params for SQL
# Output: 
#       Operation results for SQL, e.g. SELECT, INSERT, DELETE
# DATABASE_PATH = "db/dataset-small.db";
def db_query(sql, params):
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()


# Function : get profile by zid
# Input: zid
# Output: 
#       the profile of this zid (zid, password, email, full_name, birthday, 
#       program, home_suburb, home_longitude, home_latitude, profile_text)
def get_profile_by_zid(zid):
    profile = db_query("SELECT * FROM STUDENT WHERE zid = ?", [zid])
    if len(profile) != 0:
        profile = dict(profile[0])
        return profile
    else:
        return None


# Function : get suspended profile by zid
# Input: zid
# Output: 
#       suspended profile
def get_suspended_profile_by_zid(zid):
    profile = db_query("SELECT * FROM TO_BE_SUSPENDED WHERE zid = ?", [zid])
    if len(profile) != 0:
        profile = dict(profile[0])
        return profile
    else:
        return None


# Function : is_suspended
# Input: zid
# Output: True if this zid is suspended
def is_suspended(zid):
    try:
        profile = db_query("SELECT * FROM TO_BE_SUSPENDED WHERE zid = ?", [zid])
        if len(profile) != 0:
            return True
        else:
            return False
    except:
        return False


# Function : get_friends_by_zid
# Get all friends' zids for an input zid
# Note that suspended will be hidden
def get_friends_by_zid(zid):
    results = []
    friends = db_query("SELECT * FROM FRIENDS WHERE zid = ?", [zid])
    for friend in friends:
        if not is_suspended(friend['friend_zid']):
            results.append(friend['friend_zid'])
    return results


# Function : get_courses_by_zid
# Given a zid, return a list of courses
def get_courses_by_zid(zid):
    results = []
    courses = db_query("SELECT * FROM COURSES WHERE zid = ?", [zid])
    for course in courses:
        results.append(course['course'])
    return results


# Function : check_similarity
# Check similarity of 2 zids, note that they should not be same or friends
# One common courses : +1
# One common friends : +1
def check_similarity(zid1, zid2):
    if is_suspended(zid1) or is_suspended(zid2):
        return -100
    # get friends
    friends1 = set(get_friends_by_zid(zid1))
    friends2 = set(get_friends_by_zid(zid2))
    # get courses
    courses1 = set(get_courses_by_zid(zid1))
    courses2 = set(get_courses_by_zid(zid2))
    # return the sum of intersections
    return len(friends1 & friends2) + len(courses1 & courses2)


# Function : friend suggession
# Provide a list (12) of likely friend suggessions
def get_friend_suggestion(zid):
    # select those have common course with zid but not friend
    common_course_sql = "SELECT DISTINCT zid FROM COURSES WHERE course IN (SELECT course FROM COURSES WHERE zid = ?) AND zid <> ? AND zid NOT IN (SELECT friend_zid FROM FRIENDS WHERE zid = ?);"
    set1 = set([ item['zid'] for item in db_query(common_course_sql, [zid, zid, zid])])

    # select those have common friends with zid but not friend
    common_friend_sql = "SELECT DISTINCT zid FROM FRIENDS WHERE friend_zid IN (SELECT friend_zid FROM FRIENDS WHERE zid = ?) AND zid <> ? AND zid NOT IN (SELECT friend_zid FROM FRIENDS WHERE zid = ?);"
    set2 = set([ item['zid'] for item in db_query(common_friend_sql, [zid, zid, zid])])
    
    # remove repeated 
    all_candidates = set1 | set2

    if len(all_candidates) > 0:
        # calculate similarity
        all_similarities = {}
        for candidate in all_candidates:
            all_similarities[candidate] = check_similarity(zid, candidate)
        # sort and select the first 12 zids
        sorted_candidates = sorted(all_similarities.items(), key = lambda item: item[1], reverse = True)[:12]
        results = [item[0] for item in sorted_candidates]
    else:
        # If no candidate, random select 12 users
        all_sql = "SELECT zid FROM STUDENT WHERE zid <> ? AND zid NOT IN (SELECT friend_zid FROM FRIENDS WHERE zid = ?);"
        set3 = set([ item['zid'] for item in db_query(all_sql, [zid, zid])])
        results = random.sample(set3, min(12, len(set3)))

    return results




# Function : get_posts_by_zids
# Input: a list of zids
# Output: 
#       A list of all posts made by these zids, each post is a dict (id, zid, 
#       full_name, profile_img, transformed time, transformed message)
#       Posts are sorted by time, the latest will be posted first
# Note that suspended will be hidden
def get_posts_by_zids(zids):
    posts = []
    for zid in zids:
        if not is_suspended(zid):
            one_posts = db_query("SELECT id, zid, time, message FROM POST WHERE zid = ?", [zid])
            for one_post in one_posts:
                posts.append(dict(one_post))
    posts = sorted(posts, key = lambda x: x['time'], reverse = True)
    # Transform time and message
    for post in posts:
        post['message'] = transform_message(post['message'])
        post['time'] = transform_time(post['time'])
        poster_profile = get_profile_by_zid(post['zid'])
        post['full_name'] = poster_profile['full_name']
        post['profile_img'] = poster_profile['profile_img']
    return posts


# Function: get_post_by_post_id
# Get one post via its post_id (primary key)
# This post will also be shown as dict (id, zid, full_name, profile_img,
#       transformed time, transformed message)
def get_post_by_post_id(post_id):
    post = dict(db_query("SELECT id, zid, time, message FROM POST WHERE id = ?", [post_id])[0])
    post['message'] = transform_message(post['message'])
    post['time'] = transform_time(post['time'])
    poster_profile = get_profile_by_zid(post['zid'])
    post['full_name'] = poster_profile['full_name']
    post['profile_img'] = poster_profile['profile_img']
    return post


# Function : get_comments_by_post_id
# get all comments from given post_id
# Input: a post id
# Output: 
#       A list of comments, each comment is a dict (id, post_id, zid, 
#       full_name, profile_img, transformed time, transformed message)
#       The comments are sorted by time, the earliest will be post first.
def get_comments_by_post_id(post_id):
    results = []
    comments = db_query("SELECT * FROM COMMENT WHERE post_id = ?", [post_id])
    for comment in comments:
        results.append(dict(comment))
    # comments should not be shown in reverse order
    results = sorted(results, key = lambda x: x['time'])
    for comment in results:
        comment['message'] = transform_message(comment['message'])
        comment['time'] = transform_time(comment['time'])
        commenter_profile = get_profile_by_zid(comment['zid'])
        comment['full_name'] = commenter_profile['full_name']
        comment['profile_img'] = commenter_profile['profile_img']
    return results


# Function : get_replies_by_comment_id
# get all replies from given comment_id
# Input: a comment id
# Output: 
#       A list of all replies, each reply is a dict (id, comment_id, zid, 
#       full_name, profile_img, transformed time, transformed message)
#       The replies are sorted by time, the earliest will be posted first
def get_replies_by_comment_id(comment_id):
    results = []
    replies = db_query("SELECT * FROM REPLY WHERE comment_id = ?", [comment_id])
    for reply in replies:
        results.append(dict(reply))
    # replies should not be shown in reverse order
    results = sorted(results, key = lambda x: x['time'])
    for reply in results:
        reply['message'] = transform_message(reply['message'])
        reply['time'] = transform_time(reply['time'])
        replier_profile = get_profile_by_zid(reply['zid'])
        reply['full_name'] = replier_profile['full_name']
        reply['profile_img'] = replier_profile['profile_img']
    return results


# Function : get_page_index
# Split all indexes by page: e.g. page 0: 0-10, page 1: 10-20 ...
def get_page_index(num):
    pages = []
    for i in range(int(num / 10)):
        pages.append(list(range(i * 10, i * 10 +10)))
    pages.append(list(range(num - num % 10, num)))
    return pages


# Function : get_search_result
# get search result for a keyword
# note that suspended will be hidden
def get_search_result(keyword):
    pattern = "%{}%".format(keyword)
    # search for students
    students_profile = []
    students_id = db_query('SELECT zid, full_name, profile_img FROM STUDENT WHERE full_name LIKE ? OR zid = ?', [pattern, keyword])
    for item in students_id:
        item = dict(item)
        if not is_suspended(item['zid']):
            students_profile.append(item)
    # search for posts
    all_posts = []
    posts_id = db_query('SELECT id FROM POST WHERE message LIKE ?', [pattern])
    for item in posts_id:
        post = get_post_by_post_id(dict(item)['id'])
        if not is_suspended(post['zid']):
            all_posts.append(post)
    all_posts = sorted(all_posts, key = lambda x: x['time'], reverse = True)
    return students_profile, all_posts


# Function: allowed_file
# Modified from Flask doc: http://docs.jinkan.org/docs/flask/patterns/fileuploads.html
# Check whether file is valid
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# Function: send_email
# E.G. to = "yunqiuxu1991@gmail.com", subject = "activation", message = "a link"
def send_email(to, subject, message):
    mutt = [
            'mutt',
            '-s',
            subject,
            '-e', 'set copy=no',
            '-e', 'set realname=UNSWtalk',
            '--', to
    ]
    subprocess.run(
            mutt,
            input = message.encode('utf8'),
            stderr = subprocess.PIPE,
            stdout = subprocess.PIPE,
    )



# ------------------------------------------------------- #
#    Flask Functions : login and initialization           #
# ------------------------------------------------------- #
app = Flask(__name__)

# Function: before_request
# Init g.user: profile and friends
@app.before_request
def before_request():
    if 'zid' in session:
        if is_suspended(session['zid']):
            g.user = get_suspended_profile_by_zid(session['zid'])
            friends = get_friends_by_zid(session['zid'])
            if g.user != None:
                g.user['friends'] = friends
                g.user["suspended"] = 1
        else:
            g.user = get_profile_by_zid(session['zid'])
            friends = get_friends_by_zid(session['zid'])
            if g.user != None:
                g.user['friends'] = friends
                g.user["suspended"] = 0
    else:
        g.user = None


# Function : login
# Login with zid and password
# Unsuccessful login will lead to login_info
# Successful login will redirect to homepage(index)
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    # reset g.user
    g.user = None
    # get zid and password
    zid = request.form.get('zid', '')
    password = request.form.get('password', '')
    # query profile
    if not is_suspended(zid):
        profile = get_profile_by_zid(zid)
    else:
        profile = get_suspended_profile_by_zid(zid)
    
    login_info = ""
    
    if request.method == 'POST':
        # unsuccessful login
        if (profile == None) or (profile['password'] != password):
            login_info = "Wrong username or password!"
        else:
            # store zid in session cookie
            session['zid'] = zid
            # initialize g.user
            before_request()
            # redirect to homepage 
            return redirect(url_for('index', zid = g.user['zid']))
    return render_template('login.html', login_info = login_info)  


# Function : index
# The homepage of a user, whose user id is <zid>
# Note that zid may not be g.user['zid'] --> you can view other's homepage
@app.route('/<zid>/index', methods=['GET', 'POST'])
def index(zid):
    # Check whether you are logged in
    if 'zid' not in session:
        return redirect(url_for('login'))
    # Check whether you are in your homepage
    curr_profile = get_profile_by_zid(zid)
    # Welcome info
    welcome_info = g.user['full_name']
    # Get all sorted posts : your frineds' and yours
    posts_zid = get_friends_by_zid(zid)
    posts_zid.append(zid)
    all_posts = get_posts_by_zids(posts_zid)
    # Get splitted post indexes for pagination
    pages = get_page_index(len(all_posts))

    return render_template('index_simple.html', welcome_info = welcome_info, curr_profile = curr_profile, all_posts = all_posts, pages = pages)


# Function : logout
# Log out and redirect to log in page
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Remove session info
    session.pop('zid', None)
    return redirect(url_for('login'))


# Function : to_register_page()
# redirect to register page
@app.route('/to_register_page', methods=['GET', 'POST'])
def to_register_page():
    return render_template('register.html', register_info = "")


# Function : register
# Register to be a new user
# What I can change:
#       zid / email / password should not be empty
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check zid: should be like z5555555
        zid = request.form.get('zid', '')
        if not re.match(r"^z[0-9]{7}$", zid):
            register_info = "zid is wrong"
            return render_template('register.html', register_info = register_info)
        # Check zid : should be unique
        if get_profile_by_zid(zid) != None:
            register_info = "zid should be unique!"
            return render_template('register.html', register_info = register_info)

        
        # Check password: should not be empty
        new_password_1 = request.form.get('new_password_1','')
        new_password_2 = request.form.get('new_password_2','')
        if (len(new_password_1) == 0) or (len(new_password_2) == 0) or (new_password_1 != new_password_2):
            register_info = "Password is wrong"
            return render_template('register.html', register_info = register_info)
        else:
            password = new_password_1
        
        # Check email: a confirmation email will be sent, so this should not be empty!
        email = request.form.get('email','')
        if len(email) == 0:
            register_info = "Email is wrong"
            return render_template('register.html', register_info = register_info)

        # Generate a confirmation code
        confirmation_code = "".join(random.sample(string.printable[:62], 8))
        # Send confirmation code to given email
        send_email(email, "Confirmation code for UNSWTalk", confirmation_code)
        # insert new user to TABLE TO_BE_CONFIRMED
        insert_sql = "INSERT INTO TO_BE_CONFIRMED (zid, email, password, full_name, birthday, profile_img, program, home_suburb, home_longitude, home_latitude, profile_text, confirmation_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
        insert_data = [zid, email, password, "Default user", "", "img/default.png", "", "", "", "", "", confirmation_code]
        temp = db_query(insert_sql, insert_data)    

        return redirect(url_for('confirmation'))

    return render_template('register.html', register_info = register_info)


# Function : confirmation
# Check whether zid is matched with confirmation code
@app.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    confirm_info = ""
    if request.method == 'POST':
        zid = request.form.get("zid","")
        confirmation_code = request.form.get("confirmation_code","")

        # get confirm profile by zid
        confirm_profile = db_query("SELECT * FROM TO_BE_CONFIRMED WHERE zid = ?", [zid])
        if len(confirm_profile) != 0:
            confirm_profile = dict(confirm_profile[0])
        else:
            confirm_profile = None
        
        # case 1: no such zid
        if confirm_profile == None:
            confirm_info = "{} is not a user to be confirmed".format(zid)
        # case 2: zid does not match confirmation_code
        elif confirm_profile['confirmation_code'] != confirmation_code:
            confirm_info = "Unmatched zid and confirmation code"
        # case 3: match 
        else:
            # move confirm_profile from TO_BE_CONFIRMED to STUDENT
            temp_delete = db_query("DELETE FROM TO_BE_CONFIRMED WHERE zid = ?", [zid])
            insert_sql = "INSERT INTO STUDENT (zid, email, password, full_name, birthday, profile_img, program, home_suburb, home_longitude, home_latitude, profile_text) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
            insert_data = [confirm_profile['zid'], confirm_profile['email'], confirm_profile['password'], "Default user", "", "img/default.png", "", "", "", "", ""]
            temp_insert = db_query(insert_sql, insert_data)
            # mkdir to store profile image
            img_dir = "static/student_img/{}/{}".format(DATABASE_NAME, zid)
            if not os.path.exists(img_dir):
                os.mkdir(img_dir)
            return redirect(url_for('login'))
    
    return render_template('confirmation.html', confirm_info = confirm_info)  


# Function : forget_password


# ------------------------------------------------------- #
#           Flask Functions : handle profile              #
# ------------------------------------------------------- #


# Function : view_profile
# View the profile for a user with given zid
# If the zid is g.user['zid'], you can edit the profile
@app.route('/<zid>/view_profile', methods=['GET', 'POST'])
def view_profile(zid):
    # Check whether you are logged in
    if 'zid' not in session:
        return redirect(url_for('login'))
    # Check whether you are in your homepage
    curr_profile = get_profile_by_zid(zid)
    return render_template('view_profile.html', curr_profile = curr_profile)


# Function : to_edit_profile_page()
# redirect to edit_profile page
@app.route('/to_edit_profile_page', methods=['GET', 'POST'])
def to_edit_profile_page():
    if 'zid' not in session:
        return redirect(url_for('login'))
    return render_template('edit_profile.html')


# Function : edit_profile
# Only g.user can edit profile
# What I can change:
#       full_name, password, email, birthday, program
#       home_suburb, profile_img, profile_text
# What I can not change:
#       zid
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    # Check whether you are logged in
    if 'zid' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Check password
        old_password = request.form.get('old_password','')
        new_password_1 = request.form.get('new_password_1','')
        new_password_2 = request.form.get('new_password_2','')
        if (old_password != g.user['password']) or (len(new_password_1) == 0) or (len(new_password_2) == 0) or (new_password_1 != new_password_2):
            password = g.user['password']
        else:
            password = new_password_1
        # Check email
        email = request.form.get('email','')
        if len(email) == 0:
            full_name = g.user['email']
        # Check full_name
        full_name = request.form.get('full_name','')
        if len(full_name) == 0:
            full_name = g.user['full_name']
        # Check birthday
        birthday = request.form.get('birthday','')
        if len(birthday) == 0:
            birthday = g.user['birthday']
        # Check home_suburb
        home_suburb = request.form.get('home_suburb','')
        if len(home_suburb) == 0:
            home_suburb = g.user['home_suburb']
        # Check program
        program = request.form.get('program','')
        if len(program) == 0:
            program = g.user['program']
        # Check profile text
        profile_text = request.form.get('profile_text','')
        profile_text = transform_message(profile_text)
        if len(profile_text) == 0:
            profile_text = g.user['profile_text']
        # Check profile_img
        file = request.files['img_path']
        if file and allowed_file(file.filename):
            # get file name
            filename = secure_filename(file.filename)
            # get absolute path to store
            store_path = "static/student_img/{}/{}".format(DATABASE_NAME, g.user['zid'])
            store_path_abs = os.path.abspath(store_path)
            # store the file
            store_path_abs = store_path_abs + "/" + filename
            file.save(store_path_abs)
            # write into database
            profile_img = "student_img/{}/{}/{}".format(DATABASE_NAME, g.user['zid'], filename)
        else:
            profile_img = g.user['profile_img']
        # Update changes
        update_sql = "UPDATE STUDENT SET email=?, password=?, full_name=?, birthday=?, profile_img=?, program=?, home_suburb=?, profile_text=? WHERE zid=?"
        update_data = [email, password, full_name, birthday, profile_img, program, home_suburb, profile_text, g.user['zid']]
        temp = db_query(update_sql, update_data)    

    return redirect(url_for('view_profile', zid = g.user['zid']))



# Function : suspend_account
# Only g.user can suspend account!
@app.route('/suspend_account', methods=['GET', 'POST'])
def suspend_account():
    # Check login
    if 'zid' not in session:
        return redirect(url_for('login'))
    # get profile to be suspended
    suspend_profile = get_profile_by_zid(g.user['zid'])
    # delete profile from STUDENT
    temp_delete = db_query("DELETE FROM STUDENT WHERE zid = ?", [g.user['zid']])
    # insert profile into TO_BE_SUSPENDED
    insert_sql = "INSERT INTO TO_BE_SUSPENDED (zid, email, password, full_name, birthday, profile_img, program, home_suburb, home_longitude, home_latitude, profile_text) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    insert_data = [suspend_profile['zid'], 
                suspend_profile['email'], 
                suspend_profile['password'], 
                suspend_profile['full_name'],
                suspend_profile['birthday'],
                suspend_profile['profile_img'],
                suspend_profile['program'],
                suspend_profile['home_suburb'],
                suspend_profile['home_longitude'],
                suspend_profile['home_latitude'],
                suspend_profile['profile_text']]
    temp_insert = db_query(insert_sql, insert_data)
    return redirect(url_for('view_profile', zid = g.user['zid']))


# Function : activate_account
# Only g.user can activate account!
@app.route('/activate_account', methods=['GET', 'POST'])
def activate_account():
    # Check login
    if 'zid' not in session:
        return redirect(url_for('login'))
    # get profile to be activated
    suspend_profile = db_query("SELECT * FROM TO_BE_SUSPENDED WHERE zid = ?", [g.user['zid']])
    suspend_profile = dict(suspend_profile[0])
    # delete profile from TO_BE_SUSPENDED
    temp_delete = db_query("DELETE FROM TO_BE_SUSPENDED WHERE zid = ?", [g.user['zid']])
    # insert profile into STUDENT
    insert_sql = "INSERT INTO STUDENT (zid, email, password, full_name, birthday, profile_img, program, home_suburb, home_longitude, home_latitude, profile_text) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    insert_data = [suspend_profile['zid'], 
                suspend_profile['email'], 
                suspend_profile['password'], 
                suspend_profile['full_name'],
                suspend_profile['birthday'],
                suspend_profile['profile_img'],
                suspend_profile['program'],
                suspend_profile['home_suburb'],
                suspend_profile['home_longitude'],
                suspend_profile['home_latitude'],
                suspend_profile['profile_text']]
    temp_insert = db_query(insert_sql, insert_data)
    return redirect(url_for('view_profile', zid = g.user['zid']))


# Function : delete account
# Permanitely delete all information of a student
# Only g.user can delete account
@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    # Check login
    if 'zid' not in session:
        return redirect(url_for('login'))
    # Delete all information of all tables
    temp_delete_1 = db_query("DELETE FROM REPLY WHERE zid = ?", [g.user['zid']])
    temp_delete_2 = db_query("DELETE FROM COMMENT WHERE zid = ?", [g.user['zid']])
    temp_delete_3 = db_query("DELETE FROM POST WHERE zid = ?", [g.user['zid']])
    temp_delete_4 = db_query("DELETE FROM COURSES WHERE zid = ?", [g.user['zid']])
    temp_delete_5 = db_query("DELETE FROM FRIENDS WHERE zid = ? OR friend_zid = ?", [g.user['zid'], g.user['zid']])
    temp_delete_6 = db_query("DELETE FROM STUDENT WHERE zid = ?", [g.user['zid']])
    # Log out
    return redirect(url_for('logout'))


# ------------------------------------------------------- #
#   Flask Functions : handle posts / comments / replies   #
# ------------------------------------------------------- #

# Function: new_post
# Add a new post with zid: g.user['zid']
# Redirect back to index page after adding
@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    # Check login
    if 'zid' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        curr_message = request.form.get('message','')
        if curr_message != None and curr_message != "":
            # Get current time
            curr_time = datetime.now()
            curr_time = curr_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            # Insert into db
            temp = db_query("INSERT INTO POST (zid, time, message) values (?, ?, ?)", [g.user['zid'], curr_time, curr_message])
    return redirect(url_for('index', zid = g.user['zid']))


# Function: delete_post
# Delete a post with given post id
# Only g.user can delete his post
# Another parameter "zid" is for rediecting back to the page you find this post
@app.route('/<zid>/<post_id>/delete_post', methods=['GET', 'POST'])
def delete_post(zid, post_id):
    if 'zid' not in session:
        return redirect(url_for('login'))
    temp = db_query("DELETE FROM POST WHERE id = ?", [post_id])
    return redirect(url_for('index', zid = zid))


# Function : view_post_detail
# View the details(comments + replies) for a post with post_id
# zid : the one's homepage that you found this post --> you should be able to go back
@app.route('/<zid>/<post_id>/view_post_detail', methods=['GET', 'POST'])
def view_post_detail(zid, post_id):
    # Check login
    if 'zid' not in session:
        return redirect(url_for('login'))
    # Check whether this post is made on your homepage
    curr_profile = get_profile_by_zid(zid)
    # Get this post
    curr_post = get_post_by_post_id(post_id)
    # Get all comments
    all_comments = get_comments_by_post_id(post_id)
    # Get all replies
    for comment in all_comments:
        all_replies = get_replies_by_comment_id(comment['id'])
        comment['replies'] = all_replies
    return render_template('view_post_detail.html', curr_profile = curr_profile, curr_post = curr_post, all_comments = all_comments)


# Function: new_comment
# Add new comment for post with given post_id
# Only g.user can make new comment
# zid : after adding, you should be able to reach the refreshed post_detail page
@app.route('/<zid>/<post_id>/new_comment', methods=['GET', 'POST'])
def new_comment(zid, post_id):
    if 'zid' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        curr_message = request.form.get('comment','')
        if curr_message != None and curr_message != "":
            curr_time = datetime.now()
            curr_time = curr_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            temp = db_query("INSERT INTO COMMENT (post_id, zid, time, message) values (?, ?, ?, ?)", [post_id, g.user['zid'], curr_time, curr_message])
    return redirect(url_for('view_post_detail', zid = zid, post_id = post_id))


# Function: delete_comment
# Delete a comment with given comment_id
# Only g.user can delete his comment
# zid / post_id : after deleting, you should be able to reach the refreshed post_detail page
@app.route('/<zid>/<post_id>/<comment_id>/delete_comment', methods=['GET', 'POST'])
def delete_comment(zid, post_id, comment_id):
    if 'zid' not in session:
        return redirect(url_for('login'))
    temp = db_query("DELETE FROM COMMENT WHERE id = ?", [comment_id])
    return redirect(url_for('view_post_detail', zid = zid, post_id = post_id))


# Function: new_reply
# Add new reply for comment with given comment_id
# Only g.user can make new reply
# zid / post_id : after adding, you should be able to reach the refreshed post_detail page
@app.route('/<zid>/<post_id>/<comment_id>/new_comment', methods=['GET', 'POST'])
def new_reply(zid, post_id, comment_id):
    if 'zid' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        curr_message = request.form.get('reply','')
        if curr_message != None and curr_message != "":
            curr_time = datetime.now()
            curr_time = curr_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            temp = db_query("INSERT INTO REPLY (comment_id, zid, time, message) values (?, ?, ?, ?)", [comment_id, g.user['zid'], curr_time, curr_message])
    return redirect(url_for('view_post_detail', zid = zid, post_id = post_id))


# Function: delete reply
# Delete a reply with given reply_id
# Only g.user can make new reply
# zid / post_id : after adding, you should be able to reach the refreshed post_detail page
@app.route('/<zid>/<post_id>/<reply_id>/delete_reply', methods=['GET', 'POST'])
def delete_reply(zid, post_id, reply_id):
    if 'zid' not in session:
        return redirect(url_for('login'))
    temp = db_query("DELETE FROM REPLY WHERE id = ?", [reply_id])
    return redirect(url_for('view_post_detail', zid = zid, post_id = post_id))


# Function : search
# search for name / post containing keyword
@app.route('/search_results', methods=['GET', 'POST'])
def search():
    # Check login
    if 'zid' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        keyword = request.form.get('keyword','')
        if keyword != None and keyword != "":
            # perform search
            students_profile, all_posts = get_search_result(keyword)
            # pagination
            pages = get_page_index(len(all_posts))
            return render_template('search_results.html', students_profile = students_profile, all_posts = all_posts, pages = pages, search_keyword = keyword)
    # no search
    return redirect(url_for('index', zid = g.user['zid']))



# ------------------------------------------------------- #
#           Flask Functions : handle friends              #
# ------------------------------------------------------- #

# Function: view_friends
# View the friend list of user with given zid
# Only g.user has friend suggestion
@app.route('/<zid>/view_friends', methods=['GET', 'POST'])
def view_friends(zid):
    # Check login
    if 'zid' not in session:
        return redirect(url_for('login'))
    # Check whether you are in your homepage
    curr_profile = get_profile_by_zid(zid)
    # Get all friends' zids
    friends_zid = get_friends_by_zid(zid)
    # Collect all friends' profile_img and full_name
    friends_profile = []
    for friend_zid in friends_zid:
       friend_profile = get_profile_by_zid(friend_zid)
       friends_profile.append(friend_profile)

    # Get friend suggestions
    if zid == g.user['zid']:
        friend_suggestion = []
        suggestions_zid = get_friend_suggestion(zid)

        for suggestion_zid in suggestions_zid:
            suggestion_profile = get_profile_by_zid(suggestion_zid)
            friend_suggestion.append(suggestion_profile)
    else:
        friend_suggestion = None

    return render_template('view_friends.html', friends_profile = friends_profile, curr_profile = curr_profile, friend_suggestion = friend_suggestion)


# Flask function: add a friend from index page
# Note that only g.user can add a friend
# Redirect to this homepage after adding
@app.route('/<zid>/add_friend_index', methods=['GET', 'POST'])
def add_friend_index(zid):
    if 'zid' not in session:
        return redirect(url_for('login'))
    temp = db_query("INSERT INTO FRIENDS (zid, friend_zid) VALUES (?, ?)", [g.user['zid'], zid])
    temp = db_query("INSERT INTO FRIENDS (zid, friend_zid) VALUES (?, ?)", [zid, g.user['zid']])
    return redirect(url_for('index', zid = zid))

# Flask function: delete friend from index page
# Note that only g.user can delete a friend
# Redirect to this homepage after deleting
@app.route('/<zid>/delete_friend_index', methods=['GET', 'POST'])
def delete_friend_index(zid):
    if 'zid' not in session:
        return redirect(url_for('login'))
    temp = db_query("DELETE FROM FRIENDS WHERE zid=? and friend_zid=?", [g.user['zid'], zid])
    temp = db_query("DELETE FROM FRIENDS WHERE friend_zid=? and zid=?", [g.user['zid'], zid])
    return redirect(url_for('index', zid = zid))

# Flask function: add a friend from friend list
# Note that only g.user can add a friend
# Redirect to this friend list after adding
@app.route('/<curr_zid>/<zid>/add_friend_list', methods=['GET', 'POST'])
def add_friend_list(curr_zid, zid):
    if 'zid' not in session:
        return redirect(url_for('login'))
    temp = db_query("INSERT INTO FRIENDS (zid, friend_zid) VALUES (?, ?)", [g.user['zid'], zid])
    temp = db_query("INSERT INTO FRIENDS (zid, friend_zid) VALUES (?, ?)", [zid, g.user['zid']])
    return redirect(url_for('view_friends', zid = curr_zid))

# Flask function: delete a friend from friend list
# Note that only g.user can delete a friend
# Redirect to this friend list after deleting
@app.route('/<curr_zid>/<zid>/delete_friend_list', methods=['GET', 'POST'])
def delete_friend_list(curr_zid, zid):
    if 'zid' not in session:
        return redirect(url_for('login'))
    temp = db_query("DELETE FROM FRIENDS WHERE zid=? and friend_zid=?", [g.user['zid'], zid])
    temp = db_query("DELETE FROM FRIENDS WHERE friend_zid=? and zid=?", [g.user['zid'], zid])
    return redirect(url_for('view_friends', zid = curr_zid))


# ------------------------------------------------------- #
#           Flask Functions : main                        #
# ------------------------------------------------------- #

if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(debug=True)

