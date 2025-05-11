import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Book(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'books'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    img = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    genres = orm.relationship("Genre",
                          secondary="books_to_genres",
                          backref="books_to_genres_table")
    text = sqlalchemy.Column(sqlalchemy.String, unique=True)
    intro = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    author = sqlalchemy.Column(sqlalchemy.String)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, 
                                sqlalchemy.ForeignKey("users.id"))
    user = orm.relationship('User')
    users_to_books = sqlalchemy.Table(
        'users_to_books',
        SqlAlchemyBase.metadata,
        sqlalchemy.Column('users', sqlalchemy.Integer,
                        sqlalchemy.ForeignKey('users.id')),
        sqlalchemy.Column('books', sqlalchemy.Integer,
                        sqlalchemy.ForeignKey('books.id'))
    )
    users_to_end_books = sqlalchemy.Table(
        'users_to_end_books',
        SqlAlchemyBase.metadata,
        sqlalchemy.Column('users', sqlalchemy.Integer,
                        sqlalchemy.ForeignKey('users.id')),
        sqlalchemy.Column('books', sqlalchemy.Integer,
                        sqlalchemy.ForeignKey('books.id'))
    )
    