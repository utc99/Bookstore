import requests

from functions import *

from flask import Flask, session, render_template, request, redirect, url_for, make_response, jsonify
from flask_session import Session
from flask_jsglue import JSGlue
from sqlalchemy.orm import scoped_session, sessionmaker
from tempfile import mkdtemp

app = Flask(__name__)

# Check for environment variables
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
if not os.getenv("GOODREADS_API_KEY"):
    raise RuntimeError("GOODREADS_API_KEY")

# Configure session to use filesystem
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)
JSGlue(app)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Set up Goodreads API key
goodreads_key = os.getenv("GOODREADS_API_KEY")

#-------------------------------------------------------------------------
# Allow access only for logged in users


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("index", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

#-------------------------------------------------------------------------
# Index route


@app.route("/")
def index():
    return render_template("index.html")

#-------------------------------------------------------------------------
# Register a new user


@app.route("/registration", methods=["GET", "POST"])
def registration():
    """Register user."""

    # if user reached route via POST
    if request.method == "POST":

        # get user input
        email = request.form.get("email")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if not email:
            return alert_user("Email is required", "alert-danger", "index.html")

        # ensure password was submitted
        elif not password1:
            return alert_user("Password is required", "alert-danger", "index.html")

        # ensure password was confirmed
        elif not password2:
            return alert_user("Password was not confirmed", "alert-danger", "index.html")

        # Check for forbiden characters
        if symbol_check(password1) == True or symbol_check(password2) == True or symbol_check(email) == True:
            return alert_user("Forbiden characters not allowed", "alert-danger", "index.html")

        # limit password length
        elif len(password1) > 32:
            return alert_user("Password is too long, maximum 32 characters", "alert-danger", "index.html")

        # minimum password length
        elif len(password1) < 4:
            return alert_user("Password is too short, at least 4 characters", "alert-danger", "index.html")
        # check if passwords do match
        if password1 != password2:
            return alert_user("Passwords do not match", "alert-danger", "index.html")
        else:
            # hash the password and insert a new user into the database, a new user gets redirected to index
            return create_user(email, password1)

    else:
        return render_template("index.html")

# Sign in route
#-------------------------------------------------------------------------


@app.route("/signin", methods=["GET", "POST"])
def signin():
    """Log user in."""
    # forget any user_id
    session.clear()

    # if user reached route via POST
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("email-sign-in"):
            return alert_user("Email is required", "alert-danger", "index.html")

        # ensure password was submitted
        elif not request.form.get("password-sign-in"):
            return alert_user("Password is required", "alert-danger", "index.html")

        # query database for username
        try:
            rows = db.execute("SELECT * FROM users WHERE email = :email", {"email": request.form.get("email-sign-in")}).fetchall()
        except:
            return alert_user("DB event (01). Report to administrator.", "alert-danger", "index.html")

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password-sign-in"), rows[0]["hash"]):
            return alert_user("Invalid username and/or password", "alert-danger", "index.html")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("search"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("index.html")

# Search page route - MAIN ROUTE
#-------------------------------------------------------------------------


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    if request.method == "POST":
        return render_template("search.html", result=searchbook(), title="Search results:")
    else:
        return render_template("search.html")

# Sign out route
#-------------------------------------------------------------------------


@app.route("/signout")
def signout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("index"))

# OUR JSON API ROUTE
#-------------------------------------------------------------------------


@app.route("/api/<isbn>")
def api(isbn):

    try:
        isbn = db.execute("SELECT isbn,title,author,year,review_count,average_score FROM books WHERE isbn = :isbn", {
            "isbn": isbn}).fetchall()
    except:
        return make_response(jsonify({'error': 'DB Connection error'}), 404)

    if len(isbn) != 1:
        return make_response(jsonify({'error': 'Not found'}), 404)
    else:
        return jsonify(dict(isbn[0]))

# Get data from goodread.com API
#-------------------------------------------------------------------------


@app.route("/GoodreadsAPI", methods=["GET"])
def GoodreadsAPI():

    isbn = request.args.get("isbn")
    key = goodreads_key

    try:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn})
        data = res.json()
        data = data["books"]
        data = data[0]
    except:
        return jsonify({"status": "No data"})

    return jsonify(dict(data))

# Update book's rating
#-------------------------------------------------------------------------


@app.route("/rate", methods=["POST"])
@login_required
def rate():

    userid = session["user_id"]

    # get the user input
    data = request.get_json()

    # if input format is correct
    if 'rating' in data and 'isbn' in data:
        rating = data["rating"]
        isbn = data["isbn"]

        alreadyvoted = db.execute("SELECT id FROM reviews WHERE user_id=:user_id AND book_isbn =:book_isbn",
                                  {"user_id": userid, "book_isbn": isbn}).fetchall()
        if len(alreadyvoted) == 1:
            review_id = alreadyvoted[0].id
            db.execute("UPDATE reviews SET rating = :rating WHERE id = :id", {"id": review_id, "rating": rating})
            db.commit()
            update_rating(isbn)
            return jsonify({"status": "Success"})

        elif len(alreadyvoted) == 0:
            print("new")
            db.execute("INSERT INTO reviews (user_id, book_isbn, rating) VALUES(:user_id, :book_isbn, :rating)",
                       {"user_id": userid, "book_isbn": isbn, "rating": rating})
            db.commit()
            update_rating(isbn)
            return jsonify({"status": "Success"})

        else:
            jsonify({"status": "Event(01). Report to administrator."})

    else:
        return jsonify({"status": "Event(02). Report to administrator."})

# Update book's review
#-------------------------------------------------------------------------


@app.route("/submit_review", methods=["POST"])
@login_required
def submit_review():

    userid = session["user_id"]

    # get the user input
    data = request.get_json()

    # if input format is correct
    if 'review' in data and 'isbn' in data:
        review = data["review"]
        isbn = data["isbn"]

        alreadyvoted = db.execute("SELECT id FROM reviews WHERE user_id=:user_id AND book_isbn =:book_isbn",
                                  {"user_id": userid, "book_isbn": isbn}).fetchall()
        if len(alreadyvoted) == 1:
            review_id = alreadyvoted[0].id
            db.execute("UPDATE reviews SET review = :review WHERE id = :id", {"id": review_id, "review": review})
            db.commit()
            return jsonify({"status": "Success"})

        elif len(alreadyvoted) == 0:
            db.execute("INSERT INTO reviews (user_id, book_isbn, review) VALUES(:user_id, :book_isbn, :review)",
                       {"user_id": userid, "book_isbn": isbn, "review": review})
            db.commit()
            return jsonify({"status": "Success"})

        else:
            jsonify({"status": "Event(05). Report to administrator."})

    else:
        return jsonify({"status": "Event(06). Report to administrator."})

# Fetch book's review
#-------------------------------------------------------------------------


@app.route("/reviews_data", methods=["POST"])
@login_required
def reviews_data():

    userid = session["user_id"]

    # get the user input
    data = request.get_json()
    isbn = data["isbn"]

    # if json is correct
    if 'isbn' in data:

        reviews = db.execute("SELECT user_id, rating, review, email FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_isbn =:book_isbn",
                             {"book_isbn": isbn}).fetchall()
        if len(reviews) > 0:

            reviewslist = []
            for item in reviews:
                u_id = item[0]
                u_rating = item[1]
                u_review = item[2]
                u_email = item[3]
                if u_id == userid:
                    u_id = "ME"
                reviewslist.append({"user_id": u_id, "rating": u_rating, "review": u_review, "email": u_email})

            return jsonify(reviewslist)

        return jsonify({"status": "No reviews"})

    else:
        return jsonify({"status": "Event(04). Report to administrator."})