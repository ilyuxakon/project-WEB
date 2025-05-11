import sqlalchemy
from .db_session import SqlAlchemyBase
   
   
class Genre(SqlAlchemyBase):
    __tablename__ = 'genres'
    books_to_genres_table = sqlalchemy.Table(
        'books_to_genres',
        SqlAlchemyBase.metadata,
        sqlalchemy.Column('books', sqlalchemy.Integer,
                        sqlalchemy.ForeignKey('books.id')),
        sqlalchemy.Column('genres', sqlalchemy.Integer,
                        sqlalchemy.ForeignKey('genres.id'))
    )
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, 
                           autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    