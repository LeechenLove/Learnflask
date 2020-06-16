import os, sys

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager


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

db = SQLAlchemy(app) # 在扩展类实例化前加载配置
login_manager = LoginManager(app) # 实例化扩展类

@login_manager.user_loader
def load_user(user_id):
    '''
    创建用户加载回调函数，接受用户ID作为参数
    :param user_id:
    :return:
    '''
    from watchlist.models import User
    user = User.query.get(int(user_id))
    return user # 返回用户对象

login_manager.login_view = 'login'

@app.context_processor
def inject_user():
    '''
    上下文处理函数，定义变量，给上下文使用
    :return:
    '''
    from watchlist.models import User
    user = User.query.first()
    return dict(user=user)

from watchlist import views, errors, commands