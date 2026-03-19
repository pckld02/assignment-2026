import random
from flask import Flask, render_template, request, redirect, session

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

#database functions
def get_db_connection(database='minidisc.db'):
    if database == 'minidisc.db':
        conn = sqlite3.connect('minidisc.db')
        conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    elif database == 'users.db':
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn
def getuserdetails(uid=None):
    if not uid:
        uid = session['user_id']
    conn = get_db_connection(database='users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (uid,))
    user_details = cursor.fetchone()
    conn.close()
    return user_details
def getuserprofilepicture(userid=None):
    if not userid:
        userid=session['user_id']
    conn = get_db_connection(database='users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT profile_picture FROM users WHERE id = ?', (userid,))
    user = cursor.fetchone()
    conn.close()
    return user['profile_picture'] if user['profile_picture'] else "default.jpg"
def get_user_discs(user_id):
    conn = get_db_connection(database='users.db')
    cur = conn.cursor()
    cur.execute("SELECT disc_id FROM favorite_discs WHERE user_id = ?", (user_id,))
    discs = cur.fetchall()

    conn = get_db_connection(database='minidisc.db')
    cur = conn.cursor()

    userdiscs = []
    for disc in discs:
        cur.execute("""
            SELECT id, brand, name, color, capacity, notes
            FROM discs
            WHERE id = ?
        """, (disc['disc_id'],))

        disc_info = cur.fetchone()
        userdiscs.append(disc_info)


    imageindex = {}
    for row in userdiscs:
        cur.execute(
            "SELECT file_path FROM images WHERE disc_id=?",
            (row['id'],)
        )
        img = cur.fetchone()

        if img:
            imageindex[row['id']] = "../static/" + img['file_path']
        else:
            imageindex[row['id']] = f"static/images/discs/{row['id']}.jpg"


    conn.close()
    return userdiscs, imageindex
def get_user_collections(user_id):
    conn = get_db_connection(database='users.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.name, c.discs, u.username
        FROM collections c
        LEFT JOIN users u ON u.id = c.user_id
        WHERE c.user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    discs_conn = get_db_connection(database='minidisc.db')
    discs_cur = discs_conn.cursor()

    items = []
    for row in rows:
        disc_ids = []
        discs_text = (row['discs'] or '').strip()
        if discs_text:
            for value in discs_text.split(','):
                value = value.strip()
                if value.isdigit():
                    disc_ids.append(int(value))

        image_paths = []
        for disc_id in disc_ids[:4]:
            discs_cur.execute(
                "SELECT file_path FROM images WHERE disc_id = ? LIMIT 1",
                (disc_id,)
            )
            image = discs_cur.fetchone()
            if image and image['file_path']:
                image_paths.append("../static/" + image['file_path'])

        items.append({
            'id': row['id'],
            'name': row['name'],
            'username': row['username'] or 'Unknown',
            'images': image_paths
        })
    return items
def get_collection_details(cid):
    conn = get_db_connection(database='users.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.user_id, c.name, c.discs, u.username
        FROM collections c
        LEFT JOIN users u ON u.id = c.user_id
        WHERE c.id = ?
    """, (cid,))
    collection = cursor.fetchone()
    conn.close()

    if not collection:
        return {
        'id': 'null',
        'user_id': 'null',
        'name': 'null',
        'username': 'Unknown',
        'discs': 'null'
    }

    return {
        'id': collection['id'],
        'user_id': collection['user_id'],
        'name': collection['name'],
        'username': collection['username'] or 'Unknown',
        'discs': get_collection_discs(cid)
    }
def get_collection_discs(cid):
    conn = get_db_connection(database='users.db')
    cur = conn.cursor()

    cur.execute("SELECT discs FROM collections WHERE id = ?", (cid,))
    discs = cur.fetchone()
    conn.close()

    if not discs:
        return []

    conn = get_db_connection(database='minidisc.db')
    cur = conn.cursor()

    disc_ids = []
    discs_text = (discs['discs'] or '').strip()
    if discs_text:
        for value in discs_text.split(','):
            value = value.strip()
            if value.isdigit():
                disc_ids.append(int(value))

    userdiscs = []
    for disc_id in disc_ids:
        cur.execute("""SELECT * FROM discs WHERE id = ? """, (disc_id,))

        disc_info = cur.fetchone()
        if disc_info:
            userdiscs.append(disc_info)

    imageindex = {}
    for row in userdiscs:
        cur.execute(
            "SELECT file_path FROM images WHERE disc_id=?",
            (row['id'],)
        )
        img = cur.fetchone()

        if img:
            imageindex[row['id']] = "../static/" + img['file_path']
        else:
            imageindex[row['id']] = f"static/images/discs/{row['id']}.jpg"


    conn.close()
    return userdiscs, imageindex
def check_collection_publicity(cid):
    conn = get_db_connection(database='users.db')
    cur = conn.cursor()

    cur.execute("SELECT ispublic FROM collections WHERE id = ?", (cid,))
    result = cur.fetchone()
    conn.close()

    if result:
        return result['ispublic'] == 1
    return False
def update_collection_title(cid, new_title):
    conn = get_db_connection(database='users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE collections SET name = ? WHERE id = ?", (new_title, cid))
    conn.commit()
    conn.close()

@app.route('/api/filter-options')
def api_filter_options():
    field = request.args.get('field', '').strip()
    column_map = {'Brand': 'brand', 'Colour': 'color', 'Size': 'capacity'}
    column = column_map.get(field)
    if not column:
        return '', 400
    conn = get_db_connection('minidisc.db')
    cur = conn.cursor()
    cur.execute(
        f"SELECT DISTINCT {column} FROM discs WHERE {column} IS NOT NULL AND TRIM({column}) != '' ORDER BY {column}"
    )
    values = [row[column] for row in cur.fetchall()]
    conn.close()
    from flask import jsonify
    return jsonify(values)
@app.route('/api/search-database')
def api_search_database():
    q = request.args.get('q', '').strip()
    filter_field = request.args.get('filter_field', '').strip()   # Brand/Colour/Size
    filter_value = request.args.get('filter_value', '').strip()

    q = q.replace(" ", "_")

    usercollections = []
    if 'user_id' in session:
        users_conn = get_db_connection('users.db')
        users_cur = users_conn.cursor()
        users_cur.execute(
            "SELECT id, name FROM collections WHERE user_id = ? ORDER BY created_at DESC",
            (session['user_id'],)
        )
        usercollections = users_cur.fetchall()
        users_conn.close()

    if not q and not filter_value:
        return render_template('_search_results.html', items=[], usercollections=usercollections)

    conn = get_db_connection('minidisc.db')
    cur = conn.cursor()

    where_clauses = []
    params = []

    if q:
        pattern = f"%{q}%"
        where_clauses.append("(brand LIKE ? OR name LIKE ? OR color LIKE ?)")
        params.extend([pattern, pattern, pattern])

    if filter_value and filter_field:
        column_map = {'Brand': 'brand', 'Colour': 'color', 'Size': 'capacity'}
        column = column_map.get(filter_field)
        if column:
            where_clauses.append(f"{column} = ?")
            params.append(filter_value)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cur.execute(
        f"SELECT id, brand, name, color, capacity, notes FROM discs{where_sql} LIMIT 200",
        params
    )

    rows = cur.fetchall()

    imageindex = {}
    for row in rows:
        cur.execute(
            "SELECT file_path FROM images WHERE disc_id=?",
            (row['id'],)
        )
        img = cur.fetchone()

        if img:
            imageindex[row['id']] = "../static/" + img['file_path']
        else:
            imageindex[row['id']] = f"static/images/discs/{row['id']}.jpg"

    conn.close()

    return render_template(
        '_search_results.html',
        items=rows,
        images=imageindex,
        usercollections=usercollections
    )

@app.route('/add-to-collection/<int:disc_id>', methods=['POST'])
def add_to_collection(disc_id):
    if 'user_id' not in session:
        return redirect('/login')

    collection_id = request.form.get('collection_id', '').strip()
    if not collection_id.isdigit():
        return redirect(request.referrer or '/database')

    conn = get_db_connection('users.db')
    cur = conn.cursor()
    cur.execute(
        "SELECT discs FROM collections WHERE id = ? AND user_id = ?",
        (int(collection_id), session['user_id'])
    )
    collection = cur.fetchone()

    if not collection:
        conn.close()
        return redirect(request.referrer or '/database')

    existing_discs = []
    discs_text = (collection['discs'] or '').strip()
    if discs_text:
        existing_discs = [int(x.strip()) for x in discs_text.split(',') if x.strip().isdigit()]

    if disc_id not in existing_discs:
        existing_discs.append(disc_id)
        updated_discs = ','.join(str(x) for x in existing_discs)
        cur.execute(
            "UPDATE collections SET discs = ? WHERE id = ? AND user_id = ?",
            (updated_discs, int(collection_id), session['user_id'])
        )
        conn.commit()

    conn.close()
    return redirect(request.referrer or '/database')

@app.route('/')
def home():
    return render_template('home.html', username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection(database='users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['profile_picture'] = user['profile_picture']  # Add this line
            print(session)
            return redirect('/user')
        else:
            return render_template('login.html', error='Invalid username or password')
        
    if not 'user_id' in session:
        return render_template('login.html')

    if 'user_id' in session:
        return redirect('/user')
    
#website functions
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/login')

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if not 'user_id' in session:
        return redirect('/login')
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        bio = request.form['bio']
        public = 1 if request.form.get('public') == 'on' else 0

        conn = get_db_connection(database='users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET name = ?, email = ?, bio = ?, public = ? WHERE id = ?', (name, email, bio, public, session['user_id']))
        conn.commit()
        conn.close()

        return redirect('/user')
    
    return render_template('user.html', user=getuserdetails(), message=2, account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if not 'user_id' in session:
        return redirect('/login')

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Get current user
        conn = get_db_connection(database='users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()

        # Validate old password
        if not user or not check_password_hash(user['password_hash'], old_password):
            return render_template('change-password.html', error='Current password is incorrect', user=getuserdetails(), account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())

        # Validate new password
        if not new_password or len(new_password) < 6:
            return render_template('change-password.html', error='New password must be at least 6 characters long', user=getuserdetails(), account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())

        if new_password != confirm_password:
            return render_template('change-password.html', error='New passwords do not match', user=getuserdetails(), account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())

        # Update password
        hashed_password = generate_password_hash(new_password)
        conn = get_db_connection(database='users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_password, session['user_id']))
        conn.commit()
        conn.close()

        return render_template('change-password.html', success='Password changed successfully!', user=getuserdetails(), account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())

    return render_template('change-password.html', user=getuserdetails(), account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())


@app.route('/upload-picture', methods=['GET', 'POST'])
def upload_picture():
    if not 'user_id' in session:
        return redirect('/login')
    
    if request.method == 'POST':
        if 'pictureFile' not in request.files:  # Check FILES not FORM
            return render_template('user.html', username=session['username'], message=1, account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())
        
        file = request.files['pictureFile']  # Get from files, not form
        if file and file.filename != '':
            filename = f"{session['user_id']}_profile.jpg"
            os.makedirs("static/images/profile-pictures", exist_ok=True)  # Create folder if needed
            file.save(f"static/images/profile-pictures/{filename}")
        
        conn = get_db_connection(database='users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET profile_picture = ? WHERE id = ?', (filename, session['user_id']))
        print(f"Updated profile picture for user {session['username']} to {filename}")
        conn.commit()
        conn.close()
        session['profile_picture'] = getuserprofilepicture()  # Add this line

        return redirect('/user')  # Redirect after successful upload

    return render_template('user.html', user=getuserdetails(), message=1, account=1, pfp="../static/images/profile-pictures/"+getuserprofilepicture())

@app.route('/delete-account', methods=['GET', 'POST'])
def delete_account():
    if not 'user_id' in session:
        return redirect('/login')

    uid = session['user_id']
    conn = get_db_connection(database='users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (uid,))
    conn.commit()
    conn.close()
    session.clear()
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']

        conn = get_db_connection(database='users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template('register.html', error='Username already exists')

        hashed_password = generate_password_hash(password)
        join_date = datetime.datetime.now().strftime('%B %Y')  # Format: "Month Year" (e.g., "May 2025")
        cursor.execute('INSERT INTO users (username, name, password_hash, join_date, public) VALUES (?, ?, ?, ?, ?)', (username, name, hashed_password, join_date, 1))
        conn.commit()
        conn.close()

        return redirect('/login')
    
    if not 'user_id' in session:
        return render_template('register.html')
    
    if 'user_id' in session:
        return render_template('home.html')

def get_total_user_collection_likes(user_id):
    conn = get_db_connection(database='users.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(LENGTH(likes) - LENGTH(REPLACE(likes, ',', '')) + 1) AS total_likes
        FROM collections
        WHERE user_id = ? AND likes IS NOT NULL AND TRIM(likes) != ''
    """, (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result['total_likes'] if result and result['total_likes'] else 0

@app.route('/user', methods=['GET', 'POST'])
def user():
    if not 'user_id' in session:
        return render_template('login.html')

    user = request.args.get('uid')

    #check if user exists
    if user and not getuserdetails(user):
        return render_template('private-profile.html', user=getuserdetails(), message=67)
    
    #viewing another users profile
    if user and getuserdetails(user)['public'] == 1:
        userdiscs, images = get_user_discs(user)
        items=get_user_collections(user)
        print(get_user_discs(session['user_id']))
        total_likes = get_total_user_collection_likes(user)
        print(f"User {session['username']} has total collection likes: {total_likes}")


        return render_template('user.html', user=getuserdetails(user), pfp="../static/images/profile-pictures/"+getuserprofilepicture(user), userdiscs=userdiscs, images=images, items=items, total_likes=total_likes)
    
    #viewing another users profile that is private
    elif user and getuserdetails(user)['public'] == 0: return render_template('private-profile.html', user=getuserdetails(), message=0)
    
    #viewing own profile
    else:
        userdiscs, images = get_user_discs(session['user_id'])
        user=getuserdetails()
        total_likes = get_total_user_collection_likes(session['user_id'])
        print(f"User {session['username']} has total collection likes: {total_likes}")

        print(get_user_discs(session['user_id']))

        return render_template('user.html', user=getuserdetails(), pfp="../static/images/profile-pictures/"+getuserprofilepicture(), userdiscs=userdiscs, images=images, account=1 , items=get_user_collections(session['user_id']), total_likes=total_likes)

@app.route('/collections')
def collections():
    if not 'user_id' in session:
        return render_template('login.html')
    
    action = request.args.get('action')
    cid = request.args.get('cid')
    remove_disc = request.args.get('remove_disc')
    print(f"Action: {action}, Collection ID: {cid}, Remove Disc ID: {remove_disc}"+"\n\n\n")

    #handle liking and unliking collections
    # likes colum will contain the uid of all users that have liked the collection, separated by commas. This is not ideal but it works for now and avoids needing to create a whole new table for collection likes
    if action == "like" and cid:
        conn = get_db_connection(database='users.db')
        cur = conn.cursor()
        cur.execute("SELECT likes FROM collections WHERE id = ?", (cid,))
        result = cur.fetchone()
        existing_like = [int(x) for x in result['likes'].split(',') if x] if result and result['likes'] else []
        print(f"Existing likes for collection {cid}: {existing_like}"+"\n\n\n")

        if not session['user_id'] in existing_like:
            existing_like.append(session['user_id'])
            cur.execute("UPDATE collections SET likes = ? WHERE id = ?", (','.join(map(str, existing_like)), cid))
            conn.commit()
        conn.close()
        return redirect(f'/collections?cid={cid}')
    if action == "unlike" and cid:
        conn = get_db_connection(database='users.db')
        cur = conn.cursor()
        cur.execute("SELECT likes FROM collections WHERE id = ?", (cid,))
        result = cur.fetchone()
        existing_like = [int(x) for x in result['likes'].split(',') if x] if result and result['likes'] else []
        print(f"Existing likes for collection {cid}: {existing_like}"+"\n\n\n")

        if session['user_id'] in existing_like:
            existing_like.remove(session['user_id'])
            cur.execute("UPDATE collections SET likes = ? WHERE id = ?", (','.join(map(str, existing_like)), cid))
            conn.commit()
        conn.close()
        return redirect(f'/collections?cid={cid}')

    #private collection
    if cid and check_collection_publicity(cid) == False and get_collection_details(cid)['username'] != session['username']:
        return render_template('private-collection.html', user=getuserdetails(), message=0)

    #public collection or own collection
    if cid:
        userdiscs, imageindex = get_collection_discs(cid)
        collection = get_collection_details(cid)

        #if user is owner and wants to edit collection
        print(action == "edittitle" and collection['username'] == session['username'])
        if action == "edit" and collection['username'] == session['username']:
            print(f"Attempting to remove disc ID {remove_disc} from collection {cid}"+"\n\n\n")
            if remove_disc:
                disc_id_to_remove = int(remove_disc)
                if disc_id_to_remove in [disc['id'] for disc in userdiscs]:
                    userdiscs = [disc for disc in userdiscs if disc['id'] != disc_id_to_remove]
                    updated_disc_ids = ','.join(str(disc['id']) for disc in userdiscs)
                    conn = get_db_connection(database='users.db')
                    cur = conn.cursor()
                    cur.execute("UPDATE collections SET discs = ? WHERE id = ?", (updated_disc_ids, cid))
                    conn.commit()
                    conn.close()
                    collection['discs'] = updated_disc_ids  # Update collection details after removal
            return render_template('collection-edit.html', user=getuserdetails(), collection=collection, userdiscs=userdiscs, images=imageindex)
        elif action == "edittitle" and collection['username'] == session['username']:
            new_title = request.args.get('title', '')
            print(f"Received new title: '{new_title}' for collection ID {cid}"+"\n\n\n")
            if new_title:
                conn = get_db_connection(database='users.db')
                cur = conn.cursor()
                cur.execute("UPDATE collections SET name = ? WHERE id = ?", (new_title, cid))
                conn.commit()
                conn.close()
                collection['name'] = new_title  # Update collection details after title change
                return render_template('collection-detail.html', user=getuserdetails(), collection=collection, userdiscs=userdiscs, images=imageindex)
           
        else:
            return render_template('collection-detail.html', user=getuserdetails(), collection=collection, userdiscs=userdiscs, images=imageindex, userlikes=get_collection_likes(cid))

    #action for new collection
    if action == "newcollection":
        return redirect('/create_collection')    

    
    return render_template('collections.html', user=getuserdetails())

def get_collection_likes(cid):
    conn = get_db_connection(database='users.db')
    cur = conn.cursor()
    cur.execute("SELECT likes FROM collections WHERE id = ?", (cid,))
    likes_text = cur.fetchone()['likes']
    conn.close()

    if not likes_text:
        return []

    user_ids = [int(x) for x in likes_text.split(',') if x.strip().isdigit()]

    return user_ids

@app.route('/create_collection', methods=['GET', 'POST'])
def create_collection():
    if not 'user_id' in session:
        return render_template('login.html')   

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        ispublic = 1 if request.form.get('public') == 'on' else 0
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection(database='users.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO collections (user_id, name, created_at, ispublic) VALUES (?, ?, ?, ?)", (session['user_id'], title, created_at, ispublic))
        conn.commit()
        #create new collection
        return redirect('/collections?cid=' + str(cursor.lastrowid))


    return render_template('create_collection.html', user=getuserdetails())

@app.route('/search-collections')
def search_collections():

    q = request.args.get('q', '').strip()

    users_conn = get_db_connection(database='users.db')
    users_cur = users_conn.cursor()
    if not q:
        #return all collections if no search query
        users_cur.execute("SELECT c.id, c.name, c.ispublic, c.discs, u.username FROM collections c LEFT JOIN users u ON u.id = c.user_id ORDER BY c.created_at DESC LIMIT 50")
    else:
        pattern = f"%{q}%"
        users_cur.execute("""
            SELECT c.id, c.name, c.ispublic, c.discs, u.username
            FROM collections c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE c.name LIKE ? OR u.username LIKE ?
            ORDER BY c.created_at DESC
            LIMIT 50
        """, (pattern, pattern))
    rows = users_cur.fetchall()
    users_conn.close()

    discs_conn = get_db_connection(database='minidisc.db')
    discs_cur = discs_conn.cursor()

    items = []
    for row in rows:
        if row['ispublic'] == 0:
            continue  # Skip private collections
        disc_ids = []
        discs_text = (row['discs'] or '').strip()
        if discs_text:
            for value in discs_text.split(','):
                value = value.strip()
                if value.isdigit():
                    disc_ids.append(int(value))

        image_paths = []
        for disc_id in disc_ids[:4]:
            discs_cur.execute(
                "SELECT file_path FROM images WHERE disc_id = ? LIMIT 1",
                (disc_id,)
            )
            image = discs_cur.fetchone()
            if image and image['file_path']:
                image_paths.append("../static/" + image['file_path'])

        items.append({
            'id': row['id'],
            'name': row['name'],
            'username': row['username'] or 'Unknown',
            'images': image_paths
        })

    discs_conn.close()
    return render_template('_search_results_c.html', items=items)

@app.route('/database')
def database():
    if 'user_id' not in session:
        return redirect('/login')

    q = request.args.get('q', '').strip()

    return render_template(
        'database.html',
        user=getuserdetails(),
        search_query=q
    )

@app.route('/delete_collection', methods=['GET', 'POST'])
def delete_collection():
    if 'user_id' not in session:
        return redirect('/login')
    
    cid = request.form.get('cid') or request.args.get('cid')
    if not cid:
        return redirect('/collections')
    
    conn = get_db_connection(database='users.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM collections WHERE id = ? AND user_id = ?", (cid, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/collections')

@app.route('/disc/<int:disc_id>')
def disc_detail(disc_id):
    if not 'user_id' in session:
        return redirect('/login')
    
    # Handle add to collection
    action = request.args.get('action')
    if action == 'add':
        conn = get_db_connection(database='users.db')
        cur = conn.cursor()
        # Check if already added
        cur.execute("SELECT * FROM favorite_discs WHERE user_id = ? AND disc_id = ?", (session['user_id'], disc_id))
        existing = cur.fetchone()
        
        if not existing:
            cur.execute("INSERT INTO favorite_discs (user_id, disc_id) VALUES (?, ?)", (session['user_id'], disc_id))
            conn.commit()
        conn.close()
        # Redirect back without the action parameter
        return redirect(f'/disc/{disc_id}')
    if action == 'remove':
        userdiscs = get_user_discs(session['user_id'])
        print(f"User {session['username']} has discs: {userdiscs}")

        conn = get_db_connection(database='users.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM favorite_discs WHERE user_id = ? AND disc_id = ?", (session['user_id'], disc_id))
        conn.commit()
        conn.close()
        return redirect(f'/user')
    
    
    conn = get_db_connection(database='minidisc.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM discs WHERE discs.id = ?", (disc_id,))
    disc = cur.fetchone()
    
    if not disc:
        conn.close()
        return "Disc not found", 404
    
    # Get all images for this disc
    cur.execute("SELECT file_path FROM images WHERE disc_id = ?", (disc_id,))
    images = cur.fetchall()
    image_paths = [("../static/" + img['file_path']).replace("\\", "/") for img in images]
    
    conn.close()
    return render_template('disc_detail.html', disc=disc, images=image_paths, user=getuserdetails())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

