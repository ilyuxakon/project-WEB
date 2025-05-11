from flask import jsonify
from flask_restful import abort
from flask_restful import Resource, reqparse
import os
from data import db_session, __all_models


User, Book, Genre = __all_models.users.User, __all_models.books.Book, __all_models.genres.Genre

parser = reqparse.RequestParser()
parser.add_argument('name')
parser.add_argument('img')
parser.add_argument('genres', type=int, action='append')
parser.add_argument('text')
parser.add_argument('intro')
parser.add_argument('author')
parser.add_argument('user_id')
parser.add_argument('identifier')


class BookResource(Resource):
    
    def get(self, book_id):
        abort_if_book_not_found(book_id)
        session = db_session.create_session()
        book = session.get(Book, book_id)
        d = book.to_dict(
            only=('name', 'img', 'text', 'intro', 'author', 'user_id'))
        d['genres'] = [genre.id for genre in book.genres]
        return jsonify({'book': d})

    def delete(self, book_id):
        abort_if_book_not_found(book_id)
        args = parser.parse_args()
        session = db_session.create_session()
        requesting_user = session.query(User).filter(User.identifier == str(args['identifier'])).first()
        book = session.get(Book, book_id)
        
        if not (requesting_user.status == 2 or\
           book.user_id == requesting_user.id):
            return abort(403, message='no access')
        
        os.remove(f'static/img/book_jackets/{book.img}')
        os.remove(f'static/txt/{book.text}')
        session.delete(book)
        session.commit()
        return jsonify({'success': 'OK'})
    
    def put(self, book_id):
        abort_if_book_not_found(book_id)
        args = parser.parse_args()
        session = db_session.create_session()
        requesting_user = session.query(User).filter(User.identifier == str(args['identifier'])).first()
        book = session.get(Book, book_id)
        
        if not (requesting_user.status == 2 or\
           book.user_id == requesting_user.id):
            return abort(403, message='no access')
        
        try:
            if args['name'] is not None and str(args['name']):
                book.name = str(args['name'])
                
            if args['img'] is not None and str(args['img']):
                book.img = str(args['img'])
                
            if args['text'] is not None and str(args['text']):
                book.text = (str(args['text']))
                
            if args['intro'] is not None and str(args['intro']) in range(1, 3):
                book.intro = str(args['intro'])
            
            if args['author'] is not None and str(args['author']) in range(1, 3):
                book.author = str(args['author'])
                
            if args['genres'] is not None and list(args['genres']):
                book.genres.clear()
                for genre in args['genres']:
                    book.genres.append(session.get(Genre, genre))
        
        except Exception as error:
            return abort(400, message=str(error))

        session.commit()
        return jsonify({'id': book.id})


class BooksListResource(Resource):
    
    def get(self):
        session = db_session.create_session()
        book = session.query(Book).all()
        return jsonify({'books': [item.to_dict(
            only=('name', 'img', 'id')) for item in book]})

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        requesting_user = session.query(User).filter(User.identifier == str(args['identifier'])).first()
        
        if requesting_user.status == 0:
            return abort(403, message='no access')
        
        try:
            book = Book(
                name=str(args['name']),
                intro=str(args['intro']),
                author=str(args['author']),
                genres=[session.get(Genre, i) for i in args['genres']],
                user=session.get(User, int(args['user_id'])),
                user_id=session.get(User, int(args['user_id'])).id
            )
            img = str(args['img']).split('.')[-1]
        
        except Exception as error:
            return abort(400, message=str(error))
    
        session.add(book)
        session.commit()
        book.img = f'book_{book.id}_jacket.{img}'
        book.text = f'book_{book.id}_text.txt'    
        session.commit()
        
        return jsonify({'id': book.id, 'img': book.img, 'text': book.text})
    

def abort_if_book_not_found(book_id):
    session = db_session.create_session()
    book = session.get(Book, book_id)
    if not book:
        abort(404, message=f"Book {book_id} not found")
