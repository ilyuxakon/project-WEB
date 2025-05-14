from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, SubmitField, EmailField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired

from data import db_session, __all_models

db_session.global_init('db/db.db')
session = db_session.create_session()
User, Book, Genre = __all_models.users.User, __all_models.books.Book, __all_models.genres.Genre


class Filter_Form(FlaskForm):
    key_words = StringField('Ключевые слова')
    genres_list = [genre.name for genre in session.query(Genre)]
    genres = SelectMultipleField('Жанры', choices=genres_list, default=1)
    author = StringField('Автор')
    submit1 = SubmitField('Поиск')


class Search_Form(FlaskForm):
    search = StringField('Поиск')
    submit2 = SubmitField('Поиск')


class Login_Form(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class Register_Form(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    repeat_password = PasswordField('Повторите пароль', validators=[DataRequired()])
    nickname = StringField('Имя', validators=[DataRequired()])
    img = FileField('Аватар', validators=[FileRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class Create_Book_Form(FlaskForm):
    name = StringField('Название книги', validators=[DataRequired()])
    author = StringField('Автор книги', validators=[DataRequired()])
    intro = StringField('Описание книги', validators=[DataRequired()])
    genres_list = [genre.name for genre in session.query(Genre)]
    genres = SelectMultipleField('Жанры книги', choices=genres_list, default=1, validators=[DataRequired()])
    text = FileField('Файл с текстом', validators=[FileRequired()])
    img = FileField('Обложка книги', validators=[FileRequired()])
    submit = SubmitField('Готово')


class Edit_Book_Form(Create_Book_Form):
    text = FileField('Файл с текстом')
    img = FileField('Обложка книги')