from flask import jsonify
from flask_restful import abort
from flask_restful import Resource, reqparse
import os
from data import db_session, __all_models


User, Book = __all_models.users.User, __all_models.books.Book

parser = reqparse.RequestParser()
parser.add_argument('nickname')
parser.add_argument('email')
parser.add_argument('password')
parser.add_argument('status')
parser.add_argument('img')
parser.add_argument('own_books', type=int, action='append')
parser.add_argument('books', type=int, action='append')
parser.add_argument('identifier')


# requesting_user = session.query(User).filter(User.identifier == str(args['identifier'])).first()
        
# if requesting_user is None or\
#    not (requesting_user.status == 2 or\
#    user.identifier == str(args['identifier'])):
#     return abort(403, message='no access')

# В запросах изменяющих пользователя должен присутствовать идентификатор пользователя, этот код проверяет имеет ли пользователь доступ для совершения действия 


class UserResource(Resource):
    
    def get(self, user_id):
        abort_if_user_not_found(user_id)
        session = db_session.create_session()
        user = session.get(User, user_id)
        d = user.to_dict(
            only=('nickname', 'email', 'img', 'status'))
        d['own_books'] = [book.id for book in user.own_books]
        return jsonify({'user': d})

    def delete(self, user_id):
        abort_if_user_not_found(user_id)
        args = parser.parse_args()
        session = db_session.create_session()
        requesting_user = session.query(User).filter(User.identifier == str(args['identifier'])).first()
        user = session.get(User, user_id)
        
        if requesting_user is None or\
           not (requesting_user.status == 2 or\
           user.identifier == str(args['identifier'])):
            return abort(403, message='no access')
        
        os.remove(f'static/img/profile_pictures/{user.img}')
        session.delete(user)
        session.commit()
        return jsonify({'success': 'OK'})
        
    
    def put(self, user_id):
        abort_if_user_not_found(user_id)
        args = parser.parse_args()
        session = db_session.create_session()
        requesting_user = session.query(User).filter(User.identifier == str(args['identifier'])).first()
        user = session.get(User, user_id)
        
        if requesting_user is None or\
           not (requesting_user.status == 2 or\
           user.identifier == str(args['identifier'])):
            return abort(403, message='no access')
        
        try:
            if args['nickname'] is not None and str(args['nickname']):
                user.nickname = str(args['nickname'])
                
            if args['img'] is not None and str(args['img']):
                user.img = str(args['img'])
                
            if args['email'] is not None and str(args['email']):
                user.email = str(args['email'])
            
            if args['password'] is not None and str(args['password']):
                user.set_password(str(args['password']))
                
            if args['status'] is not None and int(args['status']) in range(1, 3):
                user.status = int(args['status'])
                
            if args['own_books'] is not None and list(args['own_books']):
                user.own_books.clear()
                for book in args['own_books']:
                    user.own_books.append(session.get(Book, book))
                    
            if args['books'] is not None and list(args['books']):
                user.books.clear()
                for book in args['books']:
                    user.books.append(session.get(Book, book))
        
        except Exception as error:
            return abort(400, message=str(error))

        session.commit()
        return jsonify({'id': user.id})


class UsersListResource(Resource):
    
    def get(self):
        session = db_session.create_session()
        user = session.query(User).all()
        return jsonify({'users': [item.to_dict(
            only=('nickname', 'img', 'id')) for item in user]})

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        
        if len(session.query(User).filter(User.email == str(args['email'])).all()):
            return abort(400, message='Email Error')
        
        try:
            user = User(
                nickname=str(args['nickname']),
                email=str(args['email']),
                status=int(args['status']),
            )
            user.set_password(str(args['password']))
            img = str(args['img']).split('.')[-1]
            
        except Exception as error:
            return abort(400, message=str(error))
    
        session.add(user)        
        session.commit()
        user.img = f'user_{user.id}_profile.{img}'
        session.commit()
        
        return jsonify({'id': user.id, 'img': user.img})
    

def abort_if_user_not_found(user_id):
    session = db_session.create_session()
    user = session.get(User, user_id)
    if not user:
        abort(404, message=f"User {user_id} not found")
