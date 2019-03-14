from passlib.context import CryptContext
from functools import wraps
import re
from sqlalchemy import create_engine
import os
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, session, render_template, request
from passlib.apps import custom_app_context as pwd_context
import urllib.request
import json

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


# Show alerts to users in new refreshed page
#-------------------------------------------------------------------------

def alert_user(message, alert_type, page):
    return render_template(page, title='<div class="alert ' + alert_type + '" role="alert">' + message + '</div>')

#-------------------------------------------------------------------------


def create_user(email, password1):
    """Hashes the password and inserts a new user into database"""

    # define hashing parameters
    hasher = CryptContext(schemes=["sha256_crypt"])

    # hash the user passwordhttps://adminer.cs50.net/?pgsql=ec2-54-75-230-41.eu-west-1.compute.amazonaws.com&username=ddpkorerjncawh&db=d9omadq2g7l2f9&ns=public&table=users
    hash1 = hasher.hash(password1)

    # check if the email is not already taken
    rows = db.execute("SELECT * FROM users WHERE email =:email",  {"email": email}).fetchall()
    if len(rows) == 1:
        return alert_user("Email already exists", "alert-danger", "index.html")
    else:
        # insert a new user to the database and redirect to the index page with the current balance
        db.execute("INSERT INTO users (email,hash) VALUES(:email, :hash)", {"email": email, "hash": hash1})
        db.commit()
        rows = db.execute("SELECT * FROM users WHERE email = :email", {"email": request.form.get("email")}).fetchall()
        session["user_id"] = rows[0].id

        return alert_user("A new user was created successfuly. You can log in now!", "alert-success", "index.html")

# Check if input consists only from a validated characters
#-------------------------------------------------------------------------


def symbol_check(word):

    validChars = re.compile("^[A-Za-z0-9._~()!*:@,!?+-]*$")
    for char in word:
        if not validChars.search(word):
            return True
    else:
        return False

#-------------------------------------------------------------------------
# Search


def searchbook():

    results = "No results"

    id = session["user_id"]
    isbn = request.form.get("isbn")
    title = request.form.get("title")
    author = request.form.get("author")

    if isbn:
        isbn = "%" + isbn + "%"
    else:
        isbn = "%"
    if title:
        title = "%" + title + "%"
    else:
        title = "%"
    if author:
        author = "%" + author + "%"
    else:
        author = "%"

    results = db.execute("SELECT title,isbn,author,year FROM books \
            WHERE isbn LIKE :isbn AND LOWER(title) LIKE LOWER(:title) AND LOWER(author) LIKE LOWER(:author) \
            ORDER BY title",  {"isbn": isbn, "title": title, "author": author}).fetchall()

    return(results)


#-------------------------------------------------------------------------
def update_rating(isbn):

    allratings = db.execute("SELECT rating FROM reviews WHERE book_isbn =:book_isbn",
                            {"book_isbn": isbn}).fetchall()

    new_rating = 0
    element_nr = 0
    rating_count = len(allratings)

    if len(allratings) > 0:
        for item in allratings:
            new_rating += allratings[element_nr].rating
            element_nr += 1
        new_rating = new_rating / rating_count

    db.execute("UPDATE books SET average_score = :average_score, review_count = :review_count  WHERE isbn = :isbn",
               {"average_score": new_rating, "review_count": rating_count, "isbn": isbn})
    db.commit()