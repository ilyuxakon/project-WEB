from flask import Flask
from flask import request
from flask import render_template, redirect, make_response, jsonify, url_for, abort

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, SubmitField, EmailField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename

from flask_login import LoginManager
from flask_login import current_user
from flask_login import login_user, login_required, logout_user

from flask_restful import Api, reqparse

from requests import post, get, put, delete

from PIL import Image

from data import db_session, __all_models
import users_resources
import books_resources


app = Flask(__name__)
app.config['SECRET_KEY'] = 'qwertyuiop'

api = Api(app)
api.add_resource(users_resources.UserResource, '/api/users/<int:user_id>')
api.add_resource(users_resources.UsersListResource, '/api/users') 
api.add_resource(books_resources.BookResource, '/api/books/<int:book_id>')
api.add_resource(books_resources.BooksListResource, '/api/books') 

login_manager = LoginManager()
login_manager.init_app(app)

db_session.global_init('db/db.db')
session = db_session.create_session()
User, Book, Genre = __all_models.users.User, __all_models.books.Book, __all_models.genres.Genre

WORD_COUNT = 100

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
    img = FileField('Аватар')
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
    submit = SubmitField('Создать')


class Edit_Book_Form(Create_Book_Form):
    text = FileField('Файл с текстом')
    img = FileField('Обложка книги')


def resize_file(filename, size):
    image = Image.open(filename)
    width, height = image.size
    
    if height <= width:
        image.thumbnail((int(size * width / height), size))
    
    else:
        image.thumbnail(size, int(size, int(size * height / width)))
        
    width = image.size[0]
    x0, x1 = 0, size
    if width > size:
        x0 = (width - size) // 2
        x1 = (width - size) // 2 + size
    image = image.crop((x0, 0, x1, size))
    image.save(filename)


def create_params():
    params = {
        'base_user_img': url_for('static', filename='img/profile_pictures/noname.jpg'),
        'login_user': False,
        'theme': 'light-theme'
    }

    if current_user.is_authenticated:
        params['username'] = current_user.nickname
        params['login_user'] = True
        params['user_id'] = current_user.id
        params['user_status'] = current_user.status
        if current_user is not None:
            params['user_img'] = url_for('static', filename='img/profile_pictures/' + current_user.img)
    
    if int(request.cookies.get("theme", 0)):
        params['theme'] = 'dark-theme'    
    
    return params


def reset_current_book(res, book_id):
    res.set_cookie('book_id', str(book_id), max_age=60*60*24*365*2)
    res.set_cookie('page', '0', max_age=60*60*24*365)
    return res


@app.route('/', methods=['GET', 'POST'])
@app.route('/<int:page>', methods=['GET', 'POST'])
def main_page(page=1):
    filter_form = Filter_Form()
    search_form = Search_Form()
    books = session.query(Book)

    if current_user.is_authenticated:
        if page == 2:
            books = current_user.books

        elif page == 3:
            books = current_user.own_books
            
        elif page == 4:
            books = current_user.end_books

    if request.method == 'POST':
        if filter_form.validate_on_submit() and filter_form.submit1.data:
            key_words = filter_form.key_words.data
            genres = filter_form.genres.data
            author = filter_form.author.data

            if key_words is not None:
                key_words.split()
                if len(key_words) != 0:
                    new_books = books.filter(Book.name.like(f'%{key_words[0].lower()}%') | Book.intro.like(f'{key_words[0].lower()}'))
                    if len(key_words) > 1:
                        for key in key_words[1:]:
                            new_books.union(books.filter(Book.name.like(f'%{key.lower()}%') | Book.intro.like(f'{key.lower()}')))
                    books = new_books

            if len(genres) != 0:
                new_books = books.filter(Book.genres.any(Genre.name == session.query(Genre).filter(Genre.name == genres[0]).first().name))
                if len(genres) > 1:
                    for genre in session.query(Genre).filter(Genre.name in genres[1:]).all():
                        new_books.union(books.filter(Book.genres.any(Genre.name == genre.name)))
                books = new_books

            if author is not None and author != '':
                books = books.filter(Book.author.like(f'%{author.lower()}%'))

        if search_form.validate_on_submit() and search_form.submit2.data:
            name = search_form.search.data
            books = books.filter(Book.name.like(f'%{name.lower()}%'))

    params = create_params()
    books_list = list()

    for book in books:
        books_list.append(
            {
                'img': url_for('static', filename='img/book_jackets/' + book.img),
                'name': book.name,
                'genres': [genre.name for genre in book.genres],
                'intro': book.intro,
                'id': book.id,
                'user_id': book.user_id,
            }
        )
        if current_user.is_authenticated:
            books_list[-1]['in_users_favorite_books'] = book in current_user.books

    params['books'] = books_list
    params['page'] = page

    return render_template('main.html', params=params, search_form=search_form, filter_form=filter_form)


@app.route('/create_book', methods=['POST', 'GET'])
@login_required
def create_book():
    params = create_params()
    form = Create_Book_Form()

    if form.validate_on_submit():
        response = post(request.host_url + f'api/books', json={
            'name': form.name.data,
            'author': form.author.data,
            'intro': form.intro.data,
            'img': form.img.data.filename,
            'genres': [genre.id for genre in session.query(Genre).filter(Genre.name.in_(form.genres.data)).all()],
            'user_id': current_user.id,
            'identifier': current_user.identifier
            }).json()

        filename = 'static/img/book_jackets/' + secure_filename(response['img'])
        form.img.data.save(filename)
        resize_file(filename, 128)

        filename = 'static/txt/' + secure_filename(response['text'])
        form.text.data.save(filename)

        return render_template('create_book.html', form=form, params=params, message='Книга добавлена в библиотеку')

    return render_template('create_book.html', form=form, params=params)


@app.route('/edit_book/<int:book_id>', methods=['POST', 'GET'])
@login_required
def edit_book(book_id):
    form = Edit_Book_Form()
    book = get(request.host_url + f'api/books/{book_id}').json()['book']
    
    if 'message' in book:
        return redirect('/')
    
    params = create_params()
    params['img'] = url_for('static', filename='img/book_jackets/' + book['img'])
    with open(f'static/txt/{book['text']}', 'r', encoding='utf-8') as txt_file:
            text = txt_file.read()
            params['text'] = text

    if form.validate_on_submit():
        json={
            'name': form.name.data,
            'author': form.author.data,
            'intro': form.intro.data,
            'genres': [genre.id for genre in session.query(Genre).filter(Genre.name.in_(form.genres.data)).all()],
            'user_id': current_user.id,
            'identifier': current_user.identifier
        }
        
        if form.img.data is not None:
            img = f'book_{book['id']}_jacket.{form.img.data.filename.split('.')[-1]}'
            filename = 'static/img/book_jackets/' + secure_filename(img)
            form.img.data.save(filename)
            resize_file(filename, 128)
            json['img'] = img

        if form.text.data is not None:
            text = f'book_{book['id']}_text.txt'
            filename = 'static/txt/' + secure_filename(text)
            form.text.data.save(filename)
            json['text'] = text

        response = put(request.host_url + f'api/books/{book_id}', json=json).json()

        if 'id' in response:
            return render_template('edit_book.html', form=form, params=params, message='Книга обновлена')

    else:
        form.name.data = book['name']
        form.author.data = book['author']
        form.intro.data = book['intro']
        img = url_for('static', filename='img/book_jackets/' + book['img'])
        form.genres.data = [genre.name for genre in session.query(Genre).filter(Genre.id.in_(book['genres'])).all()]

    return render_template('edit_book.html', form=form, params=params)


@app.route('/delete_book', methods=['POST'])
@login_required
def delete_book():
    args = request.form
    response = delete(request.host_url + f'api/books/{args['book_id']}', json={'identifier': current_user.identifier}).json()
    if 'success' in response:
        return {'success': True}
    return {'success': False}
    
    
@app.route('/read/<int:book_id>')
def read_book(book_id):
    params = create_params()
    response = get(request.host_url + f'api/books/{book_id}').json()

    if response:
        if 'message' in response:
            return redirect('/')
        
        book = response['book']
        book['genres'] = [genre.name for genre in session.query(Genre).filter(Genre.id.in_(book['genres']))]
        book['img'] = url_for('static', filename='img/book_jackets/' + book['img'])
        book['id'] = book_id
        book['page'] = 0
        
        if book_id == int(request.cookies.get('book_id', 0)):
            book['page'] = int(request.cookies.get('page', 0))
        
        if current_user.is_authenticated:
            book['in_users_favorite_books'] = book in current_user.books
        
        with open(f'static/txt/{book['text']}', 'r', encoding='utf-8') as txt_file:
            text = txt_file.read()
            text = text.split()
            if len(text) <= WORD_COUNT:
                book['text'] = [' '.join(text)]
            
            else:
                book['text'] = [' '.join(text[n:n + 800]) for n in range(0, len(text) - 800, 800)]
                book['text'].append(' '.join(text[len(text) // 800 * 800:]))
                
            book['book_len'] = len(book['text'])
        
        response = make_response(render_template('read_book.html', params=params, book=book))

        if book_id != int(request.cookies.get('book_id', 0)):
            response = reset_current_book(response, book_id)
            
        return response
    
    else:
        return redirect('/')


@app.route('/end_book/<int:book_id>')
@login_required
def end_book(book_id):
    book = session.get(Book, book_id)
    current_user.end_books.append(book)
    session.commit()
    return redirect('/')


@app.route('/set_current_page/<int:page>', methods=['POST'])
def set_current_page(page):
    response = make_response()
    response.set_cookie('page', str(page), max_age=60*60*24*365)
    return response


@app.route('/current_book')
def current_book():
    book_id = int(request.cookies.get('book_id', 0))
    if book_id == 0:
        return redirect('/')
    
    return redirect(f'/read/{book_id}')
    
    
@app.route('/login', methods=['POST', 'GET'])
def login():
    form = Login_Form()
    params = create_params()

    if form.validate_on_submit():
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect('/1')

        return render_template('login.html', message='Неверный логин или пароль', form=form, params=params)

    return render_template('login.html', form=form, params=params)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = Register_Form()
    params = create_params()

    if form.validate_on_submit():
        if form.password.data == form.repeat_password.data:
            response = post(request.host_url + 'api/users', json={
                'email': form.email.data,
                'password': form.password.data,
                'nickname': form.nickname.data,
                'img': form.img.data.filename,
                'status': 1
                }).json()

            if 'message' in response and response['message'] == 'Email Error':
                return render_template('register.html', form=form, message='Эта почта уже используется')

            login_user(session.get(User, response['id']), remember=form.remember_me.data)
            filename = 'static/img/profile_pictures/' + secure_filename(response['img'])
            form.img.data.save(filename)
            resize_file(filename, 64)

            return redirect('/1')

        return render_template('register.html', form=form, message='Неверный пароль', params=params)

    return render_template('register.html', form=form, params=params)


@app.route('/switch_theme', methods=['POST'])
def switch_theme():
    theme = int(request.cookies.get("theme", 0))
    theme = str(int(not theme))
    res = jsonify({'success': True})
    res.set_cookie("theme", theme, max_age=60*60*24*365*2)
    return res


@app.route('/edit_users_books', methods=['POST'])
def edit_users_books():
    args = request.form
    book = session.get(Book, args['book_id'])
    
    if book in current_user.books:
        res = jsonify({
            'success': True,
            'status': 0
        })
        current_user.books.remove(book)
        
    else:
        res = jsonify({
            'success': True,
            'status': 1
        })
        current_user.books.append(book)
    
    session.commit()
    return res


@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.errorhandler(404)
def not_found(_):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(403)
def not_found(_):
    return make_response(jsonify({'error': 'No access'}), 403)


@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


@app.errorhandler(500)
def bad_request(_):
    return make_response(jsonify({'error': 'Eternal server error'}), 500)


if __name__ == '__main__':
    app.run('127.0.0.1', 8080)
