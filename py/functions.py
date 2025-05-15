from PIL import Image
from flask import url_for
from flask import request
from flask_login import current_user


# Изменяет файл до размером size * size
def resize_file(filename, size):
    image = Image.open(filename)
    width, height = image.size
    
    if height <= width:
        image.thumbnail((int(size * width / height), size))
    
    else:
        image.thumbnail((size, int(size * height / width)))
        
    width = image.size[0]
    x0, x1 = 0, size
    if width > size:
        x0 = (width - size) // 2
        x1 = (width - size) // 2 + size
    image = image.crop((x0, 0, x1, size))
    image.save(filename)


# Возвращает базовые параметры для страниц
def create_params():
    params = {
        'base_user_img': url_for('static', filename='img/profile_pictures/noname.jpg'),
        'login_user': False,
        'theme': 'light-theme',
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


# Изменяет cookie текущей книги 
def reset_current_book(res, book_id):
    res.set_cookie('book_id', str(book_id), max_age=60*60*24*365*2)
    res.set_cookie('page', '0', max_age=60*60*24*365)
    return res