from flask import Flask, render_template, request, redirect, url_for, abort
import datetime as dt
from functools import wraps
import random
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_gravatar import Gravatar
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField, EmailField, PasswordField
from wtforms.validators import DataRequired, Email
from flask_ckeditor import CKEditorField, CKEditor

# Create the app
app = Flask(__name__)
app.secret_key = "tigrutz"
Bootstrap(app)

# Create the Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

# Configure the ckeditor
app.config['CKEDITOR_PKG_TYPE'] = 'standard'
app.config["CKEDITOR_ENABLE_CSRF"] = False
ckeditor = CKEditor(app)

# Get the current year for the copyright
date = dt.datetime.today()
YEAR = date.year

# Set up the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# GRAVATAR endpoint
GRAVATAR = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
GRAVATAR_IMG = ['mg', 'identicon', 'monsterid', 'wavatar', 'retro', 'robohash']


# Create an admin only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If the current_user.id != 1 abort with 403 error
        if current_user.is_authenticated:
            if current_user.id != 1:
                return abort(403)
            # Else continue with the route function
            return f(*args, **kwargs)
        return abort(403)

    return decorated_function


# Create a function who verifies if the user is logged in
def login_only(f):
    wraps(f)

    def decorated_function(*args, **kwargs):
        # If the user is logged in then continue with the initial path
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        # if the user isn't logged in then redirect him to the login page
        # Warn the user that he needs to have an account to post a comment
        else:
            error = "You need to have an account in order to post a comment. "
            return redirect(url_for('login', er=error))

    return decorated_function


# Create table for the database
class BlogPost(db.Model):
    # Using sqlalchemy define a 'one to many' relationship
    __tablename__ = 'blog_post'
    id = db.Column(db.Integer, primary_key=True)

    # Create a foreign key, 'users.id' the users refers to the table-name of User
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    # Create reference to the User object, the 'posts' refers to the
    # posts property in the User class.
    author = relationship('Users', back_populates="posts")

    # This will act as a list for Comment objects
    comments = relationship('Comment', back_populates='comment_blog')

    # Create the table using flask-sqlalchemy
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


# Create a users database
class Users(UserMixin, db.Model):
    # Using sqlalchemy define the relationship between the Users and BlogPost
    __tablename__ = 'users'
    # This will act like a List of BlogPost objects attached to each User.
    # The 'author' refers to the author property in the BlogPost/Comment class.
    # Save the posts wrote by the specific user in a list
    posts = relationship('BlogPost', back_populates="author")
    # Save the comments wrote by the specific user in a list
    comments = relationship('Comment', back_populates="comment_author")

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)

    # Give the user a random parameter to generate an image from GRAVATAR
    img = db.Column(db.String(250), nullable=False)


# Create a table for comments
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # Create a foreign key who refers to the Users table
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    # Create reference to the User object, the 'comments' refers to the
    # 'comments' property in the User class.
    comment_author = relationship('Users', back_populates='comments')

    # Create a foreign key who refers to the BlogPost tabel
    post_id = db.Column(db.Integer, ForeignKey('blog_post.id'))
    # Create a reference to the BlogPost object, the 'comments' refers to the 'comments' property in the BlogPost table
    comment_blog = relationship('BlogPost', back_populates='comments')


# This line will reset the existing tables and create the new ones
# db.drop_all()
# db.create_all()
# db.session.commit()


# Create the form
class NewPost(FlaskForm):
    title = StringField(label="Title", validators=[DataRequired()])
    subtitle = StringField(label="Subtitle", validators=[DataRequired()])
    img_url = StringField(label="Blog Image URL", validators=[DataRequired()])
    body = CKEditorField(label="Blog Content", validators=[DataRequired()])
    submit = SubmitField(label="Post!")


# Create the form for the register
class Register(FlaskForm):
    name = StringField(label="name", validators=[DataRequired()])
    email = EmailField(label='email', validators=[DataRequired(), Email()])
    password = PasswordField(label='password', validators=[DataRequired()])
    submit_register = SubmitField(label='Sign Me Up!')
    submit_log = SubmitField(label="Log In")


# Create a Comment form to allow the users to leave comments
class CommentForm(FlaskForm):
    comment = CKEditorField(label="Comment")
    submit = SubmitField(label="Submit Comment")


@login_manager.user_loader
def user_loader(user_id):
    return Users.query.get(user_id)


@app.route('/')
def home():
    if current_user.is_authenticated:
        print(current_user.id)
    data = BlogPost.query.all()
    parent = Users.query.get('author')
    return render_template("index.html", posts=data, ck=ckeditor,
                           logged_in=current_user.is_authenticated,
                           parent=parent,
                           year=YEAR)


@app.route('/about')
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated,
                           year=YEAR)


@app.route('/contact')
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated,
                           year=YEAR)


@app.route('/post/<post_id>', methods=["POST", "GET"])
def post(post_id):
    post_to_display = BlogPost.query.get(post_id)
    comment_form = CommentForm()

    # Verify if the user is logged in if we wants to post a comment
    if request.method == "POST":
        if current_user.is_authenticated:
            new_comment = Comment(text=comment_form.comment.data,
                                  author_id=current_user.id,
                                  post_id=post_to_display.id)
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('post', post_id=post_id))
        else:
            error = "You need to be logged in if you want to post an comment."
            return redirect(url_for('login', er=error))

    return render_template("post.html", p=post_to_display,
                           logged_in=current_user.is_authenticated,
                           f=comment_form,
                           gravatar=GRAVATAR,
                           year=YEAR)


@app.route('/create-post', methods=["GET", 'POST'])
@admin_only
def create_post():
    form = NewPost()
    if form.validate_on_submit() or request.method == "POST":
        today = dt.datetime.today()
        month = today.strftime('%B')
        day = today.day
        year = today.year
        post_time = f"{month} {day}, {year}"
        title = form.title.data
        subtitle = form.subtitle.data
        img_url = form.img_url.data
        body = form.body.data

        new_post = BlogPost(
            title=title,
            subtitle=subtitle,
            date=post_time,
            body=body,
            img_url=img_url,
            author_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template('create_post.html', f=form, logged_in=current_user.is_authenticated,
                           year=YEAR)


@app.route('/edit-post/<post_id>', methods=["GET", "POST"])
@admin_only
def edit(post_id):
    post_to_edit = BlogPost.query.get(post_id)
    # Auto complete the input so that the user doesn't need to rewrite the post from the beginning
    form = NewPost(
        title=post_to_edit.title,
        subtitle=post_to_edit.subtitle,
        author=post_to_edit.author,
        img_url=post_to_edit.img_url,
        body=post_to_edit.body
    )
    # Save the changes
    if form.validate_on_submit():
        edit_edit = BlogPost.query.get(post_id)
        edit_edit.title = form.title.data
        edit_edit.subtitle = form.subtitle.data
        edit_edit.author = form.author.data
        edit_edit.img_url = form.img_url.data
        edit_edit.body = form.body.data

        db.session.commit()

        return redirect(url_for('home'))

    return render_template("edit.html", f=form, logged_in=current_user.is_authenticated,
                           year=YEAR)


@app.route('/delete-post/<post_id>')
def delete(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = Register()
    # Get the information of the user and save them in the database
    # Hash the password using werkzeug
    if request.method == "POST":
        print("post")
        name = form.data.get('name')
        email = form.data.get('email')
        password = form.data.get('password')
        hashed_password = generate_password_hash(password)

        # If the email doesn't already exist in the database then save the new user
        # If the email already exists in the database make the user aware
        if Users.query.filter_by(email=email).first():
            error = "You already have an account with this email."
            return redirect(url_for('login', er=error, email=email))
        else:
            print('success')
            # After saving the user's information redirect them to the login page
            new_user = Users(
                name=name,
                email=email,
                password=hashed_password,
                img=random.choice(GRAVATAR_IMG)
            )
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login', email=email))

    return render_template('register.html', f=form, year=YEAR)


@app.route('/log-in', methods=['GET', "POST"])
def login():
    # Get a hold of the user's email from registration and auto-write it in the login email input
    email = request.args.get('email')
    form = Register(email=email)
    # Get the data of the user from the database and compare the passwords
    if request.method == "POST":
        # Check if the email exists in the database
        if Users.query.filter_by(email=form.email.data).first():
            logged_user = Users.query.filter_by(email=form.email.data).first()
            # If the user's email exits in the database then compare the password
            if check_password_hash(pwhash=logged_user.password, password=form.password.data):
                user_id = logged_user.id
                login_user(logged_user)
                return redirect(url_for('home', user_id=user_id))
            else:
                error = "Please make sure you wrote the right password."
                return redirect(url_for('login', er=error, email=form.email.data))
        else:
            error = "Invalid email. Please make sure you wrote the right email."
            return redirect(url_for('login', er=error))

    return render_template("login.html", f=form, year=YEAR)


@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
