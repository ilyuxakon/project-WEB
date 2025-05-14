from flask import Flask
from flask import request
from flask import render_template, redirect, make_response, jsonify, url_for

from werkzeug.utils import secure_filename

from flask_login import LoginManager
from flask_login import current_user
from flask_login import login_user, login_required, logout_user

from flask_restful import Api

from requests import post, get, put, delete

import os

from data import db_session, __all_models
import users_resources
import books_resources
from classes import *
from functions import *

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


@app.route('/', methods=['GET', 'POST'])
@app.route('/<int:page>', methods=['GET', 'POST'])
def main_page(page=1):
    filter_form = Filter_Form()
    search_form = Search_Form()
    books = session.query(Book)

    # Начальный список книг
    if current_user.is_authenticated:
        if page == 2:
            books = books.filter(Book.id.in_([b.id for b in current_user.books]))

        elif page == 3:
            books = books.filter(Book.id.in_([b.id for b in current_user.own_books]))
            
        elif page == 4:
            books = books.filter(Book.id.in_([b.id for b in current_user.end_books]))

    if request.method == 'POST':
        # Фильтрация книг по активным фильтрам
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

        # Поиск книги по названию
        if search_form.validate_on_submit() and search_form.submit2.data:
            name = search_form.search.data
            books = books.filter(Book.name.like(f'%{name.lower()}%'))

    params = create_params()
    books_list = list()

    # Параметры для страницы
    for book in books:
        books_list.append(
            {
                'img': url_for('static', filename='img/book_jackets/' + book.img),
                'name': book.name,
                'author': book.author,
                'genres': [genre.name for genre in book.genres],
                'intro': book.intro,
                'id': book.id,
                'user_id': book.user_id,
                'owner': book.user.nickname
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
        response = post(request.host_url + 'api/books', json={
            'name': form.name.data,
            'author': form.author.data,
            'intro': form.intro.data,
            'img': form.img.data.filename,
            'genres': [genre.id for genre in session.query(Genre).filter(Genre.name.in_(form.genres.data)).all()],
            'user_id': current_user.id,
            'identifier': current_user.identifier
            }).json()

        # Сохраняет изображения пользователя в нужном размере в память сервера
        filename = 'static/img/book_jackets/' + secure_filename(response['img'])
        form.img.data.save(filename)
        resize_file(filename, 128)

        # Сохраняет текст пользователя в память сервера
        filename = 'static/txt/' + secure_filename(response['text'])
        form.text.data.save(filename)

        return render_template('create_book.html', form=form, params=params, book=False, message='Книга добавлена в библиотеку')

    return render_template('create_book.html', form=form, params=params, book=False)


@app.route('/edit_book/<int:book_id>', methods=['POST', 'GET'])
@login_required
def edit_book(book_id):
    form = Edit_Book_Form()
    book = get(request.host_url + f'api/books/{book_id}').json()['book']
    
    # Сработате при любой ошибке
    if 'message' in book:
        return redirect('/')
    
    params = create_params()
    params['img'] = url_for('static', filename='img/book_jackets/' + book['img'])

    if form.validate_on_submit():
        json={
            'name': form.name.data,
            'author': form.author.data,
            'intro': form.intro.data,
            'genres': [genre.id for genre in session.query(Genre).filter(Genre.name.in_(form.genres.data)).all()],
            'user_id': current_user.id,
            'identifier': current_user.identifier
        }
        
        # Сохраняет изображения пользователя в нужном размере и заменяет старое в памяти сервера
        if form.img.data is not None:
            img = f'book_{book["id"]}_jacket.{form.img.data.filename.split(".")[-1]}'
            filename = 'static/img/book_jackets/' + secure_filename(img)
            form.img.data.save(filename)
            resize_file(filename, 128)
            json['img'] = img

        # Сохраняет текст пользователя и заменяет старое в памяти сервера
        if form.text.data is not None:
            text = f'book_{book["id"]}_text.txt'
            filename = 'static/txt/' + secure_filename(text)
            form.text.data.save(filename)
            json['text'] = text

        response = put(request.host_url + f'api/books/{book_id}', json=json).json()

        if 'id' in response:
            return render_template('edit_book.html', form=form, params=params, book=False, message='Книга обновлена')

    else:
        form.name.data = book['name']
        form.author.data = book['author']
        form.intro.data = book['intro']
        img = url_for('static', filename='img/book_jackets/' + book['img'])
        form.genres.data = [genre.name for genre in session.query(Genre).filter(Genre.id.in_(book['genres'])).all()]

    return render_template('edit_book.html', form=form, params=params, book=False)


@app.route('/delete_book', methods=['POST'])
@login_required
def delete_book():
    args = request.form
    response = delete(request.host_url + f'api/books/{args["book_id"]}', json={'identifier': current_user.identifier}).json()
    if 'success' in response:
        return {'success': True}
    return {'success': False}
    
    
@app.route('/read/<int:book_id>')
def read_book(book_id):
    params = create_params()
    params['page'] = 0
    response = get(request.host_url + f'api/books/{book_id}').json()

    if response:
        # Сработате при любой ошибке
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
            book['in_users_favorite_books'] = session.get(Book, book_id) in current_user.books
        
        # Берёт цельный текст книги и делит на страницы по "WORD_COUNT" слов на каждой
        with open(f'static/txt/{book["text"]}', 'r', encoding='utf-8') as txt_file:
            text = txt_file.read()
            text = text.split()
            if len(text) <= WORD_COUNT:
                book['text'] = [' '.join(text)]
            
            else:
                book['text'] = [' '.join(text[n:n + 800]) for n in range(0, len(text) - 800, 800)]
                book['text'].append(' '.join(text[len(text) // 800 * 800:]))
                
            book['book_len'] = len(book['text'])
        
        response = make_response(render_template('read_book.html', params=params, book=book))

        # Если пользователь откроет новую книгу, она будет считаться текущей -> будут обновлены cookie
        if book_id != int(request.cookies.get('book_id', 0)):
            response = reset_current_book(response, book_id)
            
        return response
    
    else:
        return redirect('/')


# Добавляет книгу в "Прочитанное" и возвращает на главную
@app.route('/end_book/<int:book_id>')
@login_required
def end_book(book_id):
    book = session.get(Book, book_id)
    if book not in current_user.end_books:
        current_user.end_books.append(book)
        session.commit()
    return redirect('/')


# Запоминает на какой странице остановился пользователь
@app.route('/set_current_page/<int:page>', methods=['POST'])
def set_current_page(page):
    response = make_response()
    response.set_cookie('page', str(page), max_age=60*60*24*365)
    return response


# Перенаправляет на страницу последней книги которую читал пользователь 
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
                return render_template('register.html', form=form, message='Эта почта уже используется', params=params)

            login_user(session.get(User, response['id']), remember=form.remember_me.data)
            
            # Сохраняет изображения пользователя в нужном размере в память сервера
            filename = 'static/img/profile_pictures/' + secure_filename(response['img'])
            form.img.data.save(filename)
            resize_file(filename, 64)

            return redirect('/1')

        return render_template('register.html', form=form, message='Неверный пароль', params=params)

    return render_template('register.html', form=form, params=params)


# Меняет значение темы в cookie
@app.route('/switch_theme', methods=['POST'])
def switch_theme():
    theme = int(request.cookies.get("theme", 0))
    theme = str(int(not theme))
    res = jsonify({'success': True})
    res.set_cookie("theme", theme, max_age=60*60*24*365*2)
    return res


# Добавляет книгу в избранное или убирает её оттуда
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
