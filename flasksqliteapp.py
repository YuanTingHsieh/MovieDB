#! /usr/bin/env python

import datetime
import os
import json
import traceback
import sqlite3 as sql
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from flask_paginate import Pagination, get_page_parameter

UPLOAD_FOLDER = 'upload/'
ALLOWED_EXTENSIONS = set(['txt', 'json'])

def create_schema():
    con = sql_connect('database.db')
    script = open("create_schema.sql", "r").read()
    con.executescript(script)
    con.commit()
    con.close()

def sql_connect(filename):
    con = sql.connect(filename)
    con.execute("PRAGMA foreign_keys = ON")
    return con

def create_upload_dir():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
create_schema()
create_upload_dir()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/data_entry')
def data_entry():
    return render_template('data_entry.html')

@app.route('/browsing')
def browsing():
    return render_template('browsing.html')

@app.route('/link')
def link():
    return render_template('link.html')

@app.route('/bulk_load_movies')
def bulk_load_movies():
    return render_template('bulk_load_movies.html')

@app.route('/load_movies', methods=['POST'])
def load_movies():
    try:
        if request.files.get('file'):
            filename = secure_filename(request.files['file'].filename)
        else:
            filename = None

        if not filename or not allowed_file(filename):
            msg = "Empty file or invalid file extension"
            return render_template("add_result.html", msg=msg)
        else:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            request.files['file'].save(path)

        movies = None
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as f:
            movies = json.loads(f.read())
            # Convert movies JSON to tuples
            movies = [(m["id"], m["name"], m["release_date"], m["runtime"],
                       m["director_id"], m["img_src"],
                       m["overview"]) for m in movies]
    except:
        msg = "Error in loading file\n"
        msg += traceback.format_exc()
        return render_template("add_result.html", msg=msg)

    try:
        with sql_connect("database.db") as con:
            con.isolation_level = None
            cur = con.cursor()
            cur.execute("BEGIN TRANSACTION")
            cur.executemany("INSERT INTO Movie "
                            "VALUES (?,?,?,?,?,?,?)", movies)
            con.commit()
            msg = "Movies successfully bulk loaded"
    except:
        msg = "Error in movie bulk load operation\n"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/new_movie')
def new_movie():
    return render_template('new_movie.html')

def validate_add_movie_args(name, release_date, runtime, overview, director):
    """
    Returns (True, None) if all form arguments can be validated.
    Returns (False, error_msg) otherwise.
    """
    if not name:
        return False, "Movie name can not be empty"
    elif not director:
        return False, "Director name can not be empty"
    else:
        # Check for other errors
        try:
            # Try converting runtime to integer
            runtime = int(runtime)
            assert runtime >= 0
        except:
            return False, "Invalid value for runtime: %s" % runtime

        if len(overview) > 1000:
            return False, "Overview too long"

        if release_date:
            try:
                # Verify that release date is indeed in the right format
                release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d")
                release_date = release_date.strftime("%Y-%m-%d")
            except:
                return False, "Invalid value for release_date: %s" % release_date

    return True, None

@app.route('/add_movie', methods=['POST'])
def add_movie():
    try:
        name = request.form['name']
        release_date = request.form['release_date']
        runtime = request.form['runtime']
        overview = request.form['overview']
        director = request.form['director']

        # Validate add movie arguments
        valid, msg = validate_add_movie_args(name, release_date, runtime,
                                             overview, director)
        if not valid:
            return render_template("add_result.html", msg=msg)

        with sql_connect("database.db") as con:
            cur = con.cursor()

            # First find out director CID if it exists
            cur.execute("SELECT CID FROM Contributor WHERE Name = '%s'" %
                        director)
            rows = cur.fetchone();
            if rows:
                # We found a director
                director_cid = rows[0]
            else:
                msg = "Director not found. Please add new director first"
                return render_template("add_result.html", msg=msg)

            cur.execute("INSERT INTO Movie "
                        "(Name,ReleaseDT,Length,DirectorCID,Overview) "
                        "VALUES (?,?,?,?,?)", (name, release_date, runtime,
                                               director_cid, overview))
            con.commit()
            msg = "Movie successfully added"
    except:
        msg = "Error in movie insert operation"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/movie_list')
def movie_list():
    con = sql_connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("SELECT * FROM Movie")

    rows = cur.fetchall();
    total_len = len(rows)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    rows = rows[offset:offset+per_page]

    search = False
    q = request.args.get('q')
    if q:
        search = True

    pagination = Pagination(page=page, per_page=per_page, offset=offset,
                            total=total_len, search=search, record_name='rows',
                            css_framework='bootstrap4')

    return render_template("movie_list.html", rows=rows, pagination=pagination)

@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    con = sql_connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("SELECT m.Name, m.ReleaseDT, m.Length, "
                "c.Name as DirName, m.ImageLink, m.Overview "
                "FROM Movie m, Contributor c "
                "WHERE m.DirectorCID = c.CID AND m.MID = %s" % movie_id)

    rows = cur.fetchall();
    if not rows:
        flask.abort(404)

    details = rows[0]
    img_src = "https://image.tmdb.org/t/p/w342/%s" % details["ImageLink"]
    movie_info = {
        "name": details["Name"],
        "release_date": details["ReleaseDT"],
        "runtime": details["Length"],
        "director": details["DirName"],
        "overview": details["Overview"],
        "img_src": img_src,
    }

    # Get actor information
    cur.execute("SELECT c.Name "
                "FROM Movie m, Contributor c, Acted a "
                "WHERE m.MID = a.MID AND c.CID = a.ActorID "
                "AND m.MID = %s" % movie_id)
    actors = cur.fetchall();

    # Get reviews information
    cur.execute("SELECT r.Author, r.Content "
                "FROM Movie m, Review r "
                "WHERE m.MID = r.MID AND m.MID = %s" % movie_id)
    reviews = cur.fetchall();

    return render_template("movie_details.html", movie=movie_info, actors=actors,
                           reviews=reviews)

@app.route('/movie_search')
def movie_search():
    return render_template("search_movies.html")

@app.route('/search_movies', methods=['POST'])
def search_movies():
    movie_name = request.form['movie_name']
    director_name = request.form['director_name']
    actor_name = request.form['actor_name']
    from_date = request.form['from']
    to_date = request.form['to']

    where_clauses = ""

    if not (movie_name or director_name or actor_name or from_date or to_date):
        return render_template("add_result.html", msg="Error: at least one search field must be specified")

    if movie_name:
        where_clauses += "M.Name LIKE '%%%s%%'" %movie_name

    if director_name:
        if where_clauses:
            where_clauses += " AND "
        where_clauses += "C.Name LIKE '%%%s%%'" %director_name

    if actor_name:
        if where_clauses:
            where_clauses += " AND "
        where_clauses += "M.MID IN (SELECT MID FROM Contributor, Acted WHERE Name LIKE '%%%s%%' AND CID = ActorID)" %actor_name

    if from_date:
        try:
            # Try converting year to integer
            from_date = int(from_date)
            assert from_date >= 0
        except:
            return render_template("add_result.html", msg="Error: From year must be a positive number")

        if where_clauses:
            where_clauses += " AND "
        where_clauses += "strftime('%%Y',M.ReleaseDT) >= '%s'" % from_date

    if to_date:
        try:
            # Try converting year to integer
            to_date = int(to_date)
            assert to_date >= 0
            if from_date:
                assert from_date <= to_date
        except:
            return render_template("add_result.html", msg="Error: To year must be a positive number and greater than from year")

        if where_clauses:
            where_clauses += " AND "
        where_clauses += "strftime('%%Y',M.ReleaseDT) <= '%s'" % to_date

    con = sql_connect("database.db")
    con.row_factory = sql.Row

    query = "SELECT DISTINCT M.MID, M.Name, M.ReleaseDT, M.Length, C.Name AS DName, M.Overview FROM Movie AS M, Contributor AS C WHERE %s AND M.DirectorCID=C.CID" % where_clauses

    print query
    cur = con.cursor()
    cur.execute(query)

    rows = cur.fetchall();
    return render_template("movies_search_results.html", rows=rows)


@app.route('/bulk_load_contributors')
def bulk_load_contributors():
    return render_template('bulk_load_contributors.html')

@app.route('/load_contributors', methods=['POST'])
def load_contributors():
    try:
        if request.files.get('file'):
            filename = secure_filename(request.files['file'].filename)
        else:
            filename = None

        if not filename or not allowed_file(filename):
            msg = "Empty file or invalid file extension"
            return render_template("add_result.html", msg=msg)
        else:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            request.files['file'].save(path)

        contributors = None
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as f:
            contributors = json.loads(f.read())
            # Convert movies JSON to tuples
            contributors = [(c["id"], c["name"], c["birthday"], c["gender"],
                             c["biography"]) for c in contributors]
    except:
        msg = "Error in loading file\n"
        msg += traceback.format_exc()
        return render_template("add_result.html", msg=msg)

    try:
        with sql_connect("database.db") as con:
            con.isolation_level = None
            cur = con.cursor()
            cur.execute("BEGIN TRANSACTION")
            cur.executemany("INSERT INTO Contributor "
                            "VALUES (?,?,?,?,?)", contributors)
            con.commit()
            msg = "Contributors successfully bulk loaded"
    except:
        msg = "Error in contributor bulk load operation\n"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/new_contributor')
def new_contributor():
    return render_template('new_contributor.html')

def validate_add_contributor_args(name, birthdate, biography):
    """
    Returns (True, None) if all form arguments can be validated.
    Returns (False, error_msg) otherwise.
    """
    if not name:
        return False, "Contributor name can not be empty"

    if birthdate:
        try:
            # Verify that birthdate is indeed in the right format
            birthdate = datetime.datetime.strptime(birthdate, "%Y-%m-%d")
            birthdate = birthdate.strftime("%Y-%m-%d")
        except:
            return False, "Invalid value for birthdate: %s" % birthdate

    if len(biography) > 1000:
        return False, "Biography too long"

    return True, None

@app.route('/add_contributor', methods=['POST'])
def add_contributor():
    try:
        name = request.form['name']
        birthdate = request.form['birthdate']
        biography = request.form['biography']

        valid, msg = validate_add_contributor_args(name, birthdate, biography)
        if not valid:
            return render_template("add_result.html", msg=msg)

        # Gender is a checkbox
        gender_value = request.form.getlist('gender')
        if gender_value == ["Unknown"] or gender_value == []:
            # If no checkbox is entered, assume unknown gender
            gender = 0
        elif gender_value == ["Female"]:
            gender = 1
        elif gender_value == ["Male"]:
            gender = 2
        else:
            msg = "Invalid gender selected: %s" % gender_value
            return render_template("add_result.html", msg=msg)

        with sql_connect("database.db") as con:
            cur = con.cursor()
            cur.execute("INSERT INTO Contributor "
                        "(Name,DoB,Gender,Bio) "
                        "VALUES (?,?,?,?)", (name, birthdate, gender,
                                             biography))
            con.commit()
            msg = "Contributor successfully added"
    except:
        msg = "Error in contributor insert operation"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/contributor_list')
def contributor_list():
    con = sql_connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("SELECT * FROM Contributor")

    rows = cur.fetchall();
    total_len = len(rows)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    rows = rows[offset:offset+per_page]

    search = False
    q = request.args.get('q')
    if q:
        search = True

    pagination = Pagination(page=page, per_page=per_page, offset=offset,
                            total=total_len, search=search, record_name='rows',
                            css_framework='bootstrap4')
    return render_template("contributors_list.html", rows=rows,
                           pagination=pagination)

@app.route('/contrib_search')
def contrib_search():
    return render_template("search_contributors.html")

@app.route('/search_contributors', methods=['POST'])
def search_contributors():
    name = request.form['name']
    if not name:
        return render_template("add_result.html",
                               msg="Invalid value for name: %s" % name)

    con = sql_connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("SELECT * FROM Contributor WHERE Name LIKE '%%%s%%'" % name)

    rows = cur.fetchall();
    return render_template("contributors_search_results.html", rows=rows)

@app.route('/bulk_load_reviews')
def bulk_load_reviews():
    return render_template('bulk_load_reviews.html')

@app.route('/load_reviews', methods=['POST'])
def load_reviews():
    try:
        if request.files.get('file'):
            filename = secure_filename(request.files['file'].filename)
        else:
            filename = None

        if not filename or not allowed_file(filename):
            msg = "Empty file or invalid file extension"
            return render_template("add_result.html", msg=msg)
        else:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            request.files['file'].save(path)

        reviews = None
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as f:
            reviews = json.loads(f.read())
            # Convert movies JSON to tuples
            reviews = [(r["id"], r["author"], r["content"], r["movie_id"]) for r in reviews]

    except:
        msg = "Error in loading file\n"
        msg += traceback.format_exc()
        return render_template("add_result.html", msg=msg)

    try:
        with sql_connect("database.db") as con:
            con.isolation_level = None
            cur = con.cursor()
            cur.execute("BEGIN TRANSACTION")
            cur.executemany("INSERT INTO Review "
                            "VALUES (?,?,?,?)", reviews)
            con.commit()
            msg = "Reviews successfully bulk loaded"
    except:
        msg = "Error in review bulk load operation\n"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/new_review')
def new_review():
    return render_template('new_review.html')


@app.route('/add_review', methods=['POST'])
def add_review():
    try:
        author = request.form['author']
        content = request.form['content']
        movie_name = request.form['movie_name']

        if not movie_name:
            msg = "Movie name can't be empty!"
            return render_template("add_result.html", msg=msg)

        with sql_connect("database.db") as con:
            cur = con.cursor()

            # First find out movie MID if it exists
            cur.execute("SELECT MID FROM Movie WHERE Name = '%s'" % movie_name)
            rows = cur.fetchone()
            if rows:
                # We found a movie
                movie_mid = rows[0]
            else:
                # suggested some names
                msg = "Movie not found.\n"
                cur.execute("SELECT Name FROM Movie WHERE Name LIKE '%%%s%%'" % movie_name)
                rows = cur.fetchall()
                if rows:
                    msg += "Maybe you mean:\n"
                    for i, r in enumerate(rows):
                        msg += "%2d: %s\n" % (i, r)
                else:
                    msg += " Please add the movie first."

                return render_template("add_result.html", msg=msg)

            cur.execute("INSERT INTO Review "
                        "(Author,Content,MID) "
                        "VALUES (?,?,?)", (author, content, movie_mid))
            con.commit()
            msg = "Review successfully added"
    except:
        msg = "Error in Review insert operation"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/review_list')
def review_list():
    con = sql_connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("SELECT * FROM Review")

    rows = cur.fetchall();
    total_len = len(rows)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    rows = rows[offset:offset+per_page]

    search = False
    q = request.args.get('q')
    if q:
        search = True

    pagination = Pagination(page=page, per_page=per_page, offset=offset,
                            total=total_len, search=search, record_name='rows',
                            css_framework='bootstrap4')
    return render_template("review_list.html", rows=rows, pagination=pagination)


@app.route('/review_search')
def review_search():
    return render_template("search_reviews.html")

@app.route('/search_reviews', methods=['POST'])
def search_reviews():
    movie_name = request.form['movie_name']
    director_name = request.form['director_name']
    actor_name = request.form['actor_name']

    where_clauses = "WHERE R.MID = M.MID"
    from_clauses = "Review AS R, Movie AS M"

    if not movie_name and not director_name and not actor_name:
        msg = "Need to specify either movie name or director name or actor name!"
        return render_template("add_result.html", msg=msg)

    if movie_name:
        where_clauses += " AND "
        where_clauses += "M.Name LIKE '%%%s%%'" %movie_name

    if director_name:
        where_clauses += " AND "
        where_clauses += "C.Name LIKE '%%%s%%' AND CID=M.DirectorCID" %director_name
        from_clauses += ", Contributor AS C "

    if actor_name:
        if not director_name:
            from_clauses += ", Contributor AS C "
        where_clauses += " AND "
        where_clauses += " C.Name LIKE '%%%s%%' AND C.CID = A.ActorID AND M.MID = A.MID " %actor_name
        from_clauses += ", Acted AS A "

    con = sql_connect("database.db")
    con.row_factory = sql.Row

    query = "SELECT DISTINCT R.RID, R.MID, R.Author, M.Name, R.Content FROM %s %s" % (from_clauses, where_clauses)

    print query
    cur = con.cursor()
    cur.execute(query)

    rows = cur.fetchall()

    return render_template("reviews_search_results.html", rows=rows)



@app.route('/bulk_load_acted')
def bulk_load_acted():
    return render_template("bulk_load_acted.html")

@app.route('/load_acted', methods=['POST'])
def load_acted():
    try:
        if request.files.get('file'):
            filename = secure_filename(request.files['file'].filename)
        else:
            filename = None

        if not filename or not allowed_file(filename):
            msg = "Empty file or invalid file extension"
            return render_template("add_result.html", msg=msg)
        else:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            request.files['file'].save(path)


        acted = None
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as f:
            acted = json.loads(f.read())
            # Convert movies JSON to tuples
            acted = [(c["movie_id"], c["actor_id"]) for c in acted]

    except:
        msg = "Error in loading file\n"
        msg += traceback.format_exc()
        return render_template("add_result.html", msg=msg)

    try:
        with sql_connect("database.db") as con:
            con.isolation_level = None
            cur = con.cursor()
            cur.execute("BEGIN TRANSACTION")
            cur.executemany("INSERT INTO Acted "
                            "VALUES (?,?)", acted)
            con.commit()
            msg = "Acted successfully bulk loaded"
    except:
        msg = "Error in Acted bulk load operation\n"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/new_acted')
def new_acted():
    return render_template('new_acted.html')

def validate_add_acted_args(movie, actor):
    """
    Returns (True, None) if all form arguments can be validated.
    Returns (False, error_msg) otherwise.
    """
    if not movie:
        return False, "Movie name can not be empty"
    elif not actor:
        return False, "Actor name can not be empty"

    return True, None

@app.route('/add_acted', methods=['POST'])
def add_acted():
    try:
        movie = request.form['movie']
        actor = request.form['actor']

        valid, msg = validate_add_acted_args(movie, actor)
        if not valid:
            return render_template("add_result.html", msg=msg)

        movie_id = 0
        actor_id = 0
        with sql_connect("database.db") as con:
            cur = con.cursor()

            # Find the movie ID if it exists
            cur.execute("SELECT MID FROM Movie WHERE Name = '%s'" %
                        movie)
            rows = cur.fetchone();
            if rows:
                # We found a director
                movie_id = rows[0]
            else:
                msg = "Movie not found. Please add new movie first"
                return render_template("add_result.html", msg=msg)

            # Find the actor ID if it exists
            cur.execute("SELECT CID FROM Contributor WHERE Name = '%s'" %
                        actor)
            rows = cur.fetchone();
            if rows:
                # We found a director
                actor_id = rows[0]
            else:
                msg = "Actor not found. Please add new movie actor in contributor first"
                return render_template("add_result.html", msg=msg)

            cur.execute("INSERT INTO Acted "
                        "(MID,ActorID) "
                        "VALUES (?,?)", (movie_id, actor_id))
            con.commit()
            msg = "Acted relationship successfully added"

    except:
        msg = "Error in Acted insert operation"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/acted_list')
def acted_list():

    con = sql_connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("SELECT * FROM Acted")

    rows = cur.fetchall();
    total_len = len(rows)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    rows = rows[offset:offset+per_page]

    search = False
    q = request.args.get('q')
    if q:
        search = True

    pagination = Pagination(page=page, per_page=per_page, offset=offset,
                            total=total_len, search=search, record_name='rows',
                            css_framework='bootstrap4')
    return render_template("acted_list.html", rows=rows, pagination=pagination)

@app.route('/bulk_load_release_dates')
def bulk_load_release_dates():
    return render_template("bulk_load_release_dates.html")

@app.route('/load_release_dates', methods=['POST'])
def load_release_dates():
    try:
        if request.files.get('file'):
            filename = secure_filename(request.files['file'].filename)
        else:
            filename = None

        if not filename or not allowed_file(filename):
            msg = "Empty file or invalid file extension"
            return render_template("add_result.html", msg=msg)
        else:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            request.files['file'].save(path)

        release_dates = None
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as f:
            release_dates = json.loads(f.read())
            # Convert movies JSON to tuples
            release_dates = [(c["movie_id"], c["country"], c["certification"],
                                            c["release_date"]) for c in release_dates]
    except:
        msg = "Error in loading file\n"
        msg += traceback.format_exc()
        return render_template("add_result.html", msg=msg)

    try:
        with sql_connect("database.db") as con:
            con.isolation_level = None
            cur = con.cursor()
            cur.execute("BEGIN TRANSACTION")
            cur.executemany("INSERT INTO Release_Date "
                            "VALUES (?,?,?,?)", release_dates)
            con.commit()
            msg = "Release dates successfully bulk loaded"
    except:
        msg = "Error in Acted bulk load operation\n"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/new_release_date')
def new_release_date():
    return render_template('new_release_date.html')


def validate_add_release_date_args(movie, country, release_date):
    """
    Returns (True, None) if all form arguments can be validated.
    Returns (False, error_msg) otherwise.
    """
    if not movie:
        return False, "Movie name can not be empty"
    elif not country:
        return False, "Country can not be empty"
    elif not release_date:
        return False, "Release date can not be empty"

    try:
        # Verify that release date is indeed in the right format
        release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d")
        release_date = release_date.strftime("%Y-%m-%d")
    except:
        return False, "Invalid value for release_date: %s" % release_date

    return True, None


@app.route('/add_release_date', methods=['POST'])
def add_release_date():
    try:
        movie = request.form['movie']
        country = request.form['country']
        certification = request.form['certification']
        release_date = request.form['release_date']

        valid, msg = validate_add_release_date_args(movie, country, release_date)

        if not valid:
            return render_template("add_result.html", msg=msg)
        movie_id = 0

        with sql_connect("database.db") as con:
            cur = con.cursor()

            # Find the movie ID if it exists
            cur.execute("SELECT MID FROM Movie WHERE Name = '%s'" %
                        movie)
            rows = cur.fetchone();
            if rows:
                # We found a director
                movie_id = rows[0]
            else:
                msg = "Movie not found. Please add new movie first"
                return render_template("add_result.html", msg=msg)

            cur.execute("INSERT INTO Release_Date "
                        "(MID,Country,Certification,ReleaseDT) "
                        "VALUES (?,?,?,?)", (movie_id, country, certification, release_date))
            con.commit()
            msg = "Release date successfully added"
    except:
        msg = "Error in Release date insert operation"
        msg += traceback.format_exc()
        con.rollback()

    finally:
        return render_template("add_result.html", msg=msg)
        con.close()

@app.route('/release_date_list')
def release_date_list():
    con = sql_connect("database.db")
    con.row_factory = sql.Row

    cur = con.cursor()
    cur.execute("SELECT * FROM Release_Date")

    rows = cur.fetchall();
    total_len = len(rows)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    offset = (page - 1) * per_page
    rows = rows[offset:offset+per_page]

    search = False
    q = request.args.get('q')
    if q:
        search = True

    pagination = Pagination(page=page, per_page=per_page, offset=offset,
                            total=total_len, search=search, record_name='rows',
                            css_framework='bootstrap4')
    return render_template("release_date_list.html", rows=rows,
                           pagination=pagination)

@app.route('/reset')
def reset():
    os.remove('database.db')
    create_schema()
    return render_template('add_result.html', msg="Database has been reset successfully")


if __name__ == '__main__':
    app.run(debug = True)
