import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .db_session import SqlAlchemyBase
from flask_login import UserMixin, AnonymousUserMixin
from uuid import uuid4


def default_uuid():
    return uuid4().hex


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    nickname = sqlalchemy.Column(sqlalchemy.String)
    img = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String, 
                              unique=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    identifier = sqlalchemy.Column(sqlalchemy.String, default=default_uuid)
    status = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    books = orm.relationship("Book",
                          secondary="users_to_books",
                          backref="books")
    own_books = orm.relationship("Book",
                          backref="users_own_books")
    end_books = orm.relationship("Book",
                          secondary="users_to_end_books",
                          backref="end_books")
    
    
    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
    