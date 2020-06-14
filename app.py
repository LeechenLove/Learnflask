import os, sys
import click
from flask import Flask, url_for, request, redirect, flash
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user
from flask_login import login_required, current_user, UserMixin

# 兼容Windows系统
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev' # 等同于app.secret_key='dev'
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #关闭对模型修改的监控
# 在扩展类实例化前加载配置
db = SQLAlchemy(app)
login_manager = LoginManager(app) # 实例化扩展类
login_manager.login_view

# 数据库表User类
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True) # 主键
    name = db.Column(db.String(20)) # 名字
    username = db.Column(db.String(20)) # 用户名
    password_hash = db.Column(db.String(128)) # 密码散列值

    def set_password(self, password): # 用来设置密码的方法，接受密码作为参数
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password) # 返回布尔值

# 数据库表Movie类
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True) # 主键
    title = db.Column(db.String(60)) # 电影标题
    year = db.Column(db.String(4)) # 电影年份

@app.cli.command() # 注册为命令
@click.option('--drop', is_flag=True, help='Create after drop.') # 设置选项
def initdb(drop):
    """
    Initialize the database.
    :param drop: 输入drop命令，表示删掉数据库表重建
    :return:
    """
    if drop: # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.') # 输出提示信息

@app.cli.command()
def forge():
    """
    Generate fake data.
    :return:
    """
    db.create_all

    # 数据
    name = 'LeechenLove'
    movies = [
    {'title': 'My Neighbor Totoro', 'year': '1988'},
    {'title': 'Dead Poets Society', 'year': '1989'},
    {'title': 'A Perfect World', 'year': '1993'},
    {'title': 'Leon', 'year': '1994'},
    {'title': 'Mahjong', 'year': '1996'},
    {'title': 'Swallowtail Butterfly', 'year': '1996'},
    {'title': 'King of Comedy', 'year': '1999'},
    {'title': 'Devils on the Doorstep', 'year': '1999'},
    {'title': 'WALL-E', 'year': '2008'},
    {'title': 'The Pork of Music', 'year': '2012'},
    ]

    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'], year=m['year'])
        db.session.add(movie)
    db.session.commit()
    click.echo('Done.')

@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo('Updating  user...')
        user.username = username
        user.set_password(password)
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password) # 设置密码
        db.session.add(user)
    db.session.commit()
    click.echo('Done.')


@app.context_processor
def inject_user():
    '''
    上下文处理函数，定义变量，给上下文使用
    :return:
    '''
    user = User.query.first()
    return dict(user=user)

@login_manager.user_loader
def load_user(user_id):
    '''
    创建用户加载回调函数，接受用户ID作为参数
    :param user_id:
    :return:
    '''
    user = User.query.get(int(user_id))
    return user # 返回用户对象

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']

        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))

        current_user.name = name
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用户
        # user = User.qeuery.first()
        # user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))
    return render_template('settings.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    登录函数
    :return:
    '''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.first()
        print(user.username)
        # 验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user) # 登入用户
            flash('Login success.')
            return redirect(url_for('index'))

        flash('Invalid username or password.') # 如果验证失败，显示错误消息
        return redirect(url_for('login')) # 重定向回登录页面

    return render_template('login.html')

@app.route('/logout')
@login_required # 用于视图保护
def logout():
    '''
    登出函数
    :return:
    '''
    logout_user() # 登出用户
    flash('Goodbye.')
    return redirect(url_for('index')) # 重定向回首页

@app.route('/', methods=['GET', 'POST'])
@app.route('/index')
def index():
    '''
    首页处理函数
    :return:
    '''
    if request.method == 'POST':
        if not current_user.is_authenticated: # 如果当前用户未认证
            return redirect(url_for('index')) # 重定向到主页

        # 获取表单数据
        title = request.form.get('title')
        year = request.form.get('year')

        #验证数据
        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.') # 显示错误信息
            return redirect(url_for('index')) # 重定向回主页

        # 保存表单数据到数据库
        movie = Movie(title=title, year=year) # 创建记录
        db.session.add(movie) # 添加到数据库会话
        db.session.commit() # 提交数据库会话
        flash('Item created') # 显示成功创建的提示
        return redirect(url_for('index')) # 重定向回主页

    movies = Movie.query.all()
    return render_template('index.html', movies=movies)

@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def edit(movie_id):
    '''
    更新movie函数
    :param movie_id:
    :return:
    '''
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST': # 处理编辑表单的提交请求
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invaild input.')
            return redirect(url_for('edit', movie_id=movie_id)) # 重定向回编辑页面

        movie.title = title # 更新标题
        movie.year = year # 更新年份
        db.session.commit() # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index')) # 重定向回主页

    return render_template('edit.html', movie=movie) # 传入被编辑的电影记录

@app.route('/movie/delete/<int:movie_id>', methods=['POST']) # 限定只接受POST请求
@login_required
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id) # 获取电影记录
    db.session.delete(movie) # 删除对应的记录
    db.session.commit() # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index')) # 重定向回主页

@app.errorhandler(404)
def page_not_found(e):
    '''
    404错误处理函数
    :param e:
    :return:
    '''
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run()