from flask import Flask, render_template, request, flash, redirect, abort
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_restful import Api
from random import choice
import os

from data import db_session
from data.users import User
from data.dfts import Dft
from data.api import DftResource, DftListResource

from data.utils import get_current_duck, get_current_dft_number


app = Flask(__name__)
app.config['SECRET_KEY'] = 'duckystyle_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/img/dfts'

login_manager = LoginManager()
login_manager.init_app(app)

api = Api(app)
api.add_resource(DftListResource, '/api/dft')
api.add_resource(DftResource, '/api/dft/<int:dft_id>')


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/faq')
def faq():
    return 'This page is under development'


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/profile')

    if request.method == 'GET':
        return render_template('login.html')

    username, password = request.form['username'], request.form['password']
    session = db_session.create_session()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        flash('Username not found')
        return redirect('/login')

    if not user.check_password(password):
        flash('Incorrect password')
        return render_template('login.html', username=username)

    login_user(user)
    return redirect('/profile')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect('/profile')

    if request.method == 'GET':
        return render_template('signup.html')

    username, email, name, password = (request.form['username'], request.form['email'],
                                       request.form['name'], request.form['password'])

    session = db_session.create_session()
    user = session.query(User).filter_by(username=username).first()
    if user:
        flash('Username taken')
        return render_template('signup.html', email=email, name=name)

    user = session.query(User).filter_by(email=email).first()
    if user:
        flash('A user with this email already exists')
        return render_template('signup.html', username=username, name=name)

    user = User(
        username=username,
        email=email,
        name=(name if name else f'Duck #{get_current_duck()}'),
        balance=0,
        non_refundable=10
    )
    user.set_password(password)

    session.add(user)
    session.commit()

    login_user(user)
    return redirect('/profile?first_time')


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', first_time=request.args.get('first_time'))


@app.route('/changename', methods=['GET', 'POST'])
@login_required
def change_name():
    if request.method == 'GET':
        return render_template('changename.html')

    session = db_session.create_session()
    user = session.query(User).filter_by(username=current_user.username).first()
    user.name = request.form['name']
    session.commit()

    return redirect('/profile')


@app.route('/post', methods=['GET', 'POST'])
def post_dft():
    if request.method == 'GET':
        return render_template('postdft.html')

    image = request.files['image']

    image_name = get_current_dft_number() + '.' + image.filename.split('.')[-1]
    image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))

    session = db_session.create_session()
    dft = Dft(
        name=request.form['name'],
        price=request.form['price'],
        image=image_name,
        owner=current_user
    )
    new_object = session.merge(dft)
    session.add(new_object)
    session.commit()

    return redirect('/my')


@app.route('/collection')
def dft_collection():
    session = db_session.create_session()
    if current_user.is_authenticated:
        return render_template('dfts.html', title='DFT collection', my_title='My DFTs',
                               show_coins=True,
                               balance=(current_user.balance + current_user.non_refundable),
                               dfts=session.query(Dft).filter(Dft.owner != None))

    return render_template('dfts.html', title='DFTs collection', my_title='My DFTs',
                           show_coins=False, dfts=session.query(Dft).filter(Dft.owner != None))


@app.route('/collection/our')
def our_collection():
    session = db_session.create_session()
    if current_user.is_authenticated:
        return render_template('our_dfts.html', show_coins=True,
                               balance=(current_user.balance + current_user.non_refundable),
                               dfts=session.query(Dft).filter_by(owner_id=None))

    return render_template('our_dfts.html', show_coins=False)


@app.route('/my')
@login_required
def my_dfts():
    session = db_session.create_session()
    return render_template('dfts.html', title='My DFTs', my_title='My DFTs',
                           dfts=session.query(Dft).filter_by(owner_id=current_user.id))


@app.route('/dft/<int:dft_id>/')
@app.route('/dft/our/<int:dft_id>/')
def dft_info(dft_id):
    session = db_session.create_session()
    dft = session.query(Dft).get(dft_id)
    if dft.price != -1:
        if current_user.is_authenticated:
            return render_template('dft_info.html', dft=dft,
                                   show_coins=True,
                                   balance=(current_user.balance + current_user.non_refundable))

        return render_template('dft_info.html', dft=dft, show_coins=False)

    if not current_user.is_authenticated or current_user.id != dft.owner_id:
        abort(403)

    return render_template('my_dft.html', dft=dft)


@app.route('/dft/<int:dft_id>/buy', methods=['POST'])
@login_required
def buy_dft(dft_id):
    session = db_session.create_session()
    dft = session.query(Dft).get(dft_id)

    if current_user.id == dft.owner_id:
        abort(400)

    if current_user.balance < dft.price:
        flash('Not enough money. <a href="/about#balance" class="link">Why?</a>')
        return redirect('/topup')

    user_bought = session.query(User).get(current_user.id)
    user_bought.balance -= dft.price

    user_sold = session.query(User).get(dft.owner_id)
    user_sold.balance += dft.price * .95

    dft.owner_id = current_user.id
    dft.price = -1

    session.commit()

    return redirect('/my')


@app.route('/dft/our/<int:dft_id>/buy', methods=['POST'])
def buy_our_dft(dft_id):
    session = db_session.create_session()
    dft = session.query(Dft).get(dft_id)

    if current_user.id == dft.owner_id:
        abort(400)

    if current_user.balance + current_user.non_refundable < dft.price:
        flash('Not enough money. <a href="/about#balance" class="link">Why?</a>')
        return redirect('/topup')

    user_bought = session.query(User).get(current_user.id)
    if user_bought.non_refundable < dft.price:
        take_from_balance = dft.price - user_bought.non_refundable
        user_bought.non_refundable = 0
        user_bought.balance -= take_from_balance
    else:
        user_bought.non_refundable -= dft.price

    dft.owner_id = current_user.id
    dft.price = -1

    session.commit()

    return redirect('/my')


@app.route('/wallet')
@login_required
def my_wallet():
    return render_template('wallet.html')


@app.route('/earn')
@login_required
def earn_coins():
    return render_template('earncoins.html')


@app.route('/earn/watch')
@login_required
def watch_an_ad():
    ads = ('sample-10s.mp4',)
    return render_template('ad.html', url=choice(ads))


@app.route('/earn/getaward', methods=['POST'])
@login_required
def get_award():
    session = db_session.create_session()
    user = session.query(User).get(current_user.id)
    user.non_refundable = round(user.non_refundable + .1, 2)
    session.commit()
    return redirect('/wallet')


@app.route('/topup')
@login_required
def top_up():
    return render_template('topup.html')


@app.route('/topup/success', methods=['POST'])
@login_required
def top_up_success():
    session = db_session.create_session()
    user = session.query(User).get(current_user.id)
    user.balance = round(user.balance + int(request.form['amount']), 2)
    session.commit()
    return redirect('/wallet')


@app.route('/withdraw')
@login_required
def withdraw_duckcoins():
    return render_template('withdraw.html')


@app.route('/withdraw/success', methods=['POST'])
@login_required
def withdraw_success():
    session = db_session.create_session()
    user = session.query(User).get(current_user.id)
    user.balance = round(user.balance - int(request.form['amount']), 2)
    session.commit()
    return redirect('/wallet')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


if __name__ == '__main__':
    db_session.global_init('db/dfts.db')
    app.run(debug=False, host='0.0.0.0')
