import os

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
from datetime import timedelta


app = Flask(__name__)
app.secret_key = b"admin"

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config['DEBUG'] = True

#Session(app)



# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
goodreadsKey = ""




def getReviews(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"isbns": "0380795272", "key": "R02aORIUpZqnTScLahXQ"})
    data = res.json()
    ratings_count = data['books'][0]['ratings_count']
    average_rating = data['books'][0]['average_rating']
    dict = {"ratings_count":ratings_count, "average_rating":average_rating}
    return dict

@app.route("/")
def index():
    title = "Book Review Tool"
    return render_template("index.html", title=title)

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/register_attempt", methods=["POST"])
def register_attempt():
    username = request.form.get("username")
    password = request.form.get("password")
    if db.execute("SELECT username FROM users WHERE username = :username", {"username":username}).rowcount > 0:
        return render_template("error.html", message="Username already taken.")

    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password})
    db.commit()
    return render_template("layout.html", headmsg="Success!", bodymsg="You are successfully registered.")

@app.route("/login")
def login():
    if "username" in session:
        return redirect(url_for("home"))
    session.clear()
    return render_template("login.html")

@app.route("/login_attempt", methods=["POST"])
def login_attempt():
    username = request.form.get("username")
    password = request.form.get("password")

    if db.execute("SELECT FROM users WHERE username = :username AND password = :password", {"username":username, "password":password}).rowcount == 0:
        return render_template("error.html", message="Login incorrect.")

    userIDResults = db.execute("SELECT id FROM users WHERE username = :username", {"username": username}).fetchone()
    userID = userIDResults[0]
    usernameResults = db.execute("SELECT username FROM users WHERE id = :id", {"id": userID}).fetchone()
    userID = db.execute("SELECT id FROM users WHERE username = :username", {"username":username}).fetchone()
    session.clear()
    session['userID'] = userID[0]
    username = usernameResults[0]

    session['username'] = username
    #if "username" in session:
        #return "it worked!"
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/home")
def home():
    if "username" in session:
        return render_template("home.html")
    session.clear()
    return redirect(url_for("login"))

@app.route("/search", methods=["POST"])
def search():
    search = "%"+request.form.get("searchInput")+"%"
    query = db.execute("SELECT * FROM books WHERE title LIKE :search OR isbn LIKE :search OR author LIKE :search", {"search":search})
    if query.rowcount == 0:
        return "No books found"
    results = query.fetchall()
    return render_template("results.html", results=results)

@app.route("/book/<string:isbn>")
def books(isbn):
    session.pop("isbn", None)
    session["isbn"] = isbn
    session.modified = True
    #if 'isbn' in session:
      #  return str(session.items())
    #return "isbn is not working"
    query = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn})
    results = query.fetchall()
    data = getReviews(isbn)
    ratings_count = data['ratings_count']
    average_rating = data['average_rating']
    reviews = db.execute("SELECT username, review, rating FROM reviews JOIN users ON users.id = reviews.userid WHERE bookid = :isbn", {"isbn":isbn}).fetchall()
    return render_template("bookdetails.html", results=results, average_rating=average_rating, ratings_count=ratings_count, isbn=isbn, reviews = reviews)

@app.route("/submit_review/", methods=["POST"])
def submit_review():
    #if 'isbn' in session:
     #   return str(session.items())
    #return "isbn is not working"
    review = request.form.get("review")
    rating = request.form.get("rating")
    isbn = str(request.args.get("isbn"))
    username = session["username"]
    userID = session['userID']

    if db.execute("SELECT * FROM reviews WHERE userid = :userid AND bookid = :isbn", {"userid":userID, "isbn":isbn}).rowcount > 0:
        return "you already have an existing review"
    db.execute("INSERT INTO reviews (review, rating, bookid, userid) VALUES (:review, :rating, :bookid, :userid)", {"review":review, "rating":rating, "bookid":isbn, "userid":userID})
    db.commit()
    return render_template("layout.html", headmsg = "Success!", bodymsg="Your review has been submitted")

@app.route("/delete_review", methods=["POST"])
def delete_review():
    userID = session['userID']
    isbn = session['isbn']
    db.execute("DELETE FROM reviews WHERE userid = :userID AND bookid = :isbn ", {"userID":userID, "isbn":isbn})
    db.commit()
    string = '/book/' + session['isbn']
    return redirect(string)

@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    book = db.execute("SELECT * from books WHERE isbn = :isbn", {"isbn":isbn}).fetchall()
    if len(book) == 0:
        return jsonify({"error":"Invalid ISBN"}), 422
    title = book[0][1]
    author = book[0][2]
    year = book[0][3]
    reviewDict = getReviews(isbn)
    average_rating = reviewDict["average_rating"]
    ratings_count = reviewDict["ratings_count"]

    return jsonify({"title":title, "author":author, "year":year, "isbn":isbn, "average_ratings":float(average_rating), "ratings_count":ratings_count})
