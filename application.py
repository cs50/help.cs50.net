from builtins import range
from flask import abort, Flask, render_template, redirect, request, session, url_for
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from raven.contrib.flask import Sentry
from tempfile import mkdtemp

import flask_migrate
import math
import model
import os
import re
import requests
import urllib.parse

# application
app = Flask(__name__)
db = SQLAlchemy(app)
Migrate(app, db)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://{}:{}@{}/{}".format(
    urllib.parse.quote_plus(os.environ["MYSQL_USERNAME"]),
    urllib.parse.quote_plu(os.environ["MYSQL_PASSWORD"]),
    urllib.parse.quote_plu(os.environ["MYSQL_HOST"]),
    urllib.parse.quote_plu(os.environ["MYSQL_DATABASE"]))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

# monitoring
Sentry(app)

# whitespace control
# http://jinja.pocoo.org/docs/dev/templates/
app.jinja_env.keep_trailing_newline = True
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

class Output(db.Model):
    __tablename__ = "outputs"
    mysql_default_charset = "utf8",
    mysql_collate = "utf8_general_ci"
    id = db.Column(db.BigInteger, primary_key=True, nullable=False, autoincrement=True)
    output = db.Column(db.Text)

class Input(db.Model):
    __tablename__ = "inputs"
    mysql_default_charset = "utf8",
    mysql_collate =  "utf8_general_ci"
    id = db.Column(db.BigInteger, primary_key=True, nullable=False, autoincrement=True)
    cmd = db.Column(db.String(length=1024), nullable=True)
    _script = db.Column("script", db.Text, nullable=False)
    username = db.Column(db.String(length=32), nullable=True, index=True)
    created = db.Column(db.DateTime, default=func.now(), index=True)
    output_id = db.Column(db.BigInteger, db.ForeignKey("outputs.id"), nullable=True)
    reviewed = db.Column(db.Boolean, default=False, index=True)

    # getter, strips ANSI codes
    @property
    def script(self):
        return re.compile(r"\x1b[^m]*m").sub("", self._script)

    # setter, preserves ANSI codes
    @script.setter
    def script(self, script):
        self._script = script

# perform any migrations
@app.before_first_request
def configure():
    flask_migrate.upgrade()

# /
@app.route("/", methods=["GET", "POST"])
def index():

    # POST
    if request.method == "POST":

        # validate format
        format = request.form.get("format")
        if format not in ["ans", "html", "txt"]:
            abort(400)

        # validate script
        script = request.form.get("script")
        if script is None:
            abort(400)

        # remove any ANSI codes
        # http://stackoverflow.com/a/14693789
        script = re.compile(r"\x1b[^m]*m").sub("", script)

        import help50.internal
        help50.internal.load_helpers(os.getenv("HELPERS_PATH"))
        help = help50.internal.get_help(script)

        # helpful response
        if help:
            before, after = help
            after = " ".join(after)
            model.log(request.form.get("cmd"), request.form.get("username"), request.form.get("script"), after)
            return render_template("helpful." + format, script=script, before="\n".join(before), after=after)

        # unhelpful response
        model.log(request.form.get("cmd"), request.form.get("username"), request.form.get("script"), None)
        if os.getenv("WEBHOOK"):
            if request.form.get("cmd"):
                message = "```\n$ {}\n{}\n```".format(request.form.get("cmd"), script.rstrip())
            else:
                message = "```\n{}\n```".format(script.rstrip())
            requests.post(os.getenv("WEBHOOK"), json={"message": message})
        return render_template("unhelpful." + format, cmd=request.form.get("cmd"), script=script)

    # GET, HEAD, OPTION
    else:
        return render_template("index.html")

@app.route('/review', methods=["GET", "POST"])
def review():

    # POST if submitted password
    if request.method == "POST":
        # user submitted password to access review page
        if ("password" in request.form):
            if (request.form.get("password") == os.environ["HELP50_PASSWORD"]):
                session["authenticated"] = True
                page = request.args.get("page", 1)
                return show_review(page)
            else:
                return render_template("review_auth.html", invalid=True)

        # user submitted form on review page
        else:
            for input_id in request.form:
                model.mark_reviewed(input_id)
            return render_template("review.html", inputs=model.unreviewed_matchless())

    # GET
    else:
        if session.get("authenticated"):  # show requested page
            page = request.args.get("page", 1)
            return show_review(page)
        else:  # show authorization page if not logged in
            return render_template("review_auth.html")

def show_review(page):
    page = int(page)
    page_size = 25
    all_inputs = model.unreviewed_matchless()
    inputs = all_inputs.paginate(page, page_size, False).items
    num_pages = math.ceil(all_inputs.count() / page_size)
    return render_template("review.html", inputs=inputs, page=page, num_pages=num_pages)

@app.route("/logout")
def logout():
    session["authenticated"] = False
    return redirect(url_for("review"))


# 400 Bad Request
@app.errorhandler(400)
def bad_request(e):
    return render_template("400.html"), 400

# ANSI filter
@app.template_filter("ans")
def ans(value):
    return re.sub(r"`([^`]+)`", r"\033[1m\1\033[22m", value)

# HTML filter
@app.template_filter("html")
def html(value):
    return re.sub(r"`([^`]+)`", r"<strong>\1</strong>", value)
