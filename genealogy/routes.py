import json
import os
import secrets
from datetime import date, datetime

import flask_login
import markdown
from flask import (abort, flash, redirect, render_template, request,
                   send_from_directory, url_for)

from genealogy import app, login_manager


def load_users():
  DIR = 'data/login/'
  createDirIfNeeded(DIR)

  filename = 'login.md'
  open(os.path.join(DIR, filename), 'a').close() # make sure it exists

  users = {}
  with open(os.path.join(DIR, filename)) as file:
    for line in file:
      fields = line.rstrip().split(';')
      if len(fields) != 4:
        continue
      email = fields[2]
      users[email] = {'role': fields[0], 'name': fields[1], 'password': fields[3]}
  return users

def add_new_user(name, email):
  DIR = 'data/login/'
  createDirIfNeeded(DIR)

  filename = 'login.md'
  open(os.path.join(DIR, filename), 'a').close() # make sure it exists

  password = secrets.token_hex()
  with open(os.path.join(DIR, filename), "a") as file:
      file.write(f'inactive;{name};{email};{password}\n')

def read_relative(filename):
  try:
    with open(filename, 'r') as f:
      text = f.read()
  except:
    return None

  data = text.split('---\n', maxsplit=2)
  body = markdown.markdown(data[-1])
  relative = {'body': body}

  if len(data) == 3:
    meta = json.loads('{' + data[-2] + '}')
    relative.update(meta)

  return relative

def get_birthday(relative):
  birthday = relative['birthday']
  try:
    if len(birthday.split('.')) == 3:
      birthday = birthday.split('.')
      return date(birthday[2], birthday[1], birthday[0])
    if len(birthday.split('-')) == 3:
      birthday = birthday.split('-')
      return date(birthday[0], birthday[1], birthday[2])
  except:
    pass
  return date.today()

def get_relative_name(hash):
  if not hash:
    return ''

  try:
    relative = read_relative(os.path.join('data/relatives/', hash + '.md'))
    return relative['name']
  except:
    return 'Failed to resolve hash: ' + hash

def read_all_relatives(max_posts=-1, reverse=True):
  relatives = []

  for root, _, files in os.walk('data/relatives/', topdown=False):
    for name in files:
      if name.endswith('.md'):
        try:
          post = read_relative(os.path.join(root, name))
        except:
          pass
        else:
          relatives.append(post)

  relatives.sort(key=get_birthday, reverse=reverse)
  if max_posts > 0:
    return relatives[0:max_posts]
  return relatives

def write_relative(relative):
  DIR = 'data/relatives/'
  createDirIfNeeded(DIR)

  filename = f'{relative["hash"]}.md'

  def spouse_to_string(spouse):
    if len(spouse) == 0:
      return '[]'
    if len(spouse) == 1:
      return f'["{spouse[0]}"]'

    s = ', '.join([f'"{sp}"' for sp in spouse])
    return f"[{s}]"

  with open(os.path.join(DIR, filename), mode='w') as file:
    file.write('---\n')
    file.write(f'"hash":         "{relative["hash"]}",\n')
    file.write(f'"name":         "{relative["name"]}",\n')
    file.write(f'"sex":          "{relative["sex"]}",\n')
    file.write(f'"father":       "{relative["father"]}",\n')
    file.write(f'"mother":       "{relative["mother"]}",\n')
    file.write(f'"spouse":       {spouse_to_string(relative["spouse"])},\n')
    file.write(f'"birthday":     "{relative["birthday"]}",\n')
    file.write(f'"birthplace":   "{relative["birthplace"]}",\n')
    file.write(f'"weddingDay":   "{relative["weddingDay"]}",\n')
    file.write(f'"weddingPlace": "{relative["weddingPlace"]}",\n')
    file.write(f'"dayOfDeath":   "{relative["dayOfDeath"]}",\n')
    file.write(f'"placeOfDeath": "{relative["placeOfDeath"]}",\n')
    file.write(f'"profession":   "{relative["profession"]}",\n')
    file.write(f'"image":        "{relative["image"]}"\n')
    file.write('---\n')

def createDirIfNeeded(dir):
  if not os.path.exists(dir):
    os.makedirs(dir)

class User(flask_login.UserMixin):
  def __init__(self, name, email, role):
    self.name = name
    self.id = email
    self.role = role

@login_manager.user_loader
def user_loader(email):
  users = load_users()
  if email not in users:
    return None

  role = users[email]['role']
  if role == 'inactive':
    return None

  user = User(users[email]['name'], email, role)
  return user

@login_manager.unauthorized_handler
def unauthorized_handler():
  return redirect(url_for('login'))

@app.after_request
def after_request(response):
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  DIR = 'data/log/'
  createDirIfNeeded(DIR)

  filename = 'requests.md'
  open(os.path.join(DIR, filename), 'a').close() # make sure it exists

  with open(os.path.join(DIR, filename), "a") as file:
    file.write('| {} | {} | {} | {} | {} | {} |\n'.format(timestamp, request.remote_addr, request.method, request.scheme, request.full_path, response.status))
  return response

@app.route('/')
def index():
  relatives = read_all_relatives(4, reverse=True)
  return render_template('index.html', relatives=relatives)

@app.route('/generic')
@flask_login.login_required
def generic():
  return render_template('generic.html')

@app.route('/elements')
@flask_login.login_required
def elements():
  return render_template('elements.html')

@app.route('/relatives')
def relatives():
  relatives = read_all_relatives()
  return render_template('relatives.html', relatives=relatives)

@app.route('/relatives/<relative_hash>')
def relative(relative_hash):
  relatives = read_all_relatives()
  relative = [p for p in relatives if p['hash'] == relative_hash]
  if relative:
    relative = relative[0]
    return render_template('relative.html', relative=relative)
  return render_template('404.html'), 404

@app.route('/relatives/<relative_hash>/edit', methods=['GET', 'POST'])
def relative_edit(relative_hash):
  relatives = read_all_relatives()
  relative = [p for p in relatives if p['hash'] == relative_hash]
  if relative:
    relative = relative[0]
  else:
    return render_template('404.html'), 404

  if request.method == 'GET':
    return render_template('relative_edit.html', relative=relative)

  relative['hash'] = request.form['hash']
  relative['name'] = request.form['name']
  relative['sex'] = request.form['sex']
  relative['father'] = request.form['father']
  relative['mother'] = request.form['mother']
  relative['spouse'] = [s[1:-1].strip() for s in request.form['spouse'][1:-1].split(',')]
  relative['birthday'] = request.form['birthday']
  relative['birthplace'] = request.form['birthplace']
  relative['weddingDay'] = request.form['weddingDay']
  relative['weddingPlace'] = request.form['weddingPlace']
  relative['dayOfDeath'] = request.form['dayOfDeath']
  relative['placeOfDeath'] = request.form['placeOfDeath']
  relative['profession'] = request.form['profession']

  if relative_hash != relative['hash']:
    # TODO: Update all references
    pass

  # TODO: Check all cross-references
  write_relative(relative)
  return redirect(url_for('relative', relative_hash=relative_hash))

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'GET':
    return render_template('login.html')

  email = request.form['email']
  users = load_users()
  if email in users:
    name = users[email]['name']
    role = users[email]['role']
    password = users[email]['password']
    if password == request.form['password']:
      if role == 'inactive':
        flash('User is not yet activated')
      else:
        user = User(name, email, role)
        flask_login.login_user(user)
        return redirect(url_for('index'))
  else:
    flash('Bad login')
  return redirect(url_for('login'))

@app.route('/signup', methods=['POST'])
def signup():
  if not request.method == 'POST':
    return redirect(url_for('login'))

  name = request.form['name']
  email = request.form['email']

  if not name or not email:
    flash('Registration failed: both name and email are required')
    return redirect(url_for('login'))

  users = load_users()
  if len(users) > 100:
    flash('There is unusually high traffic at the moment. Please try to send your message later again.')
    return redirect(url_for('index'))

  if not email in users:
    add_new_user(name, email)

  flash('All accounts get activated manually. You will get an email as soon as your request is processed.')
  return redirect(url_for('index'))

@app.route('/logout')
@flask_login.login_required
def logout():
  flask_login.logout_user()
  return redirect(url_for('index'))

@app.route('/search', methods=['GET', 'POST'])
def search():
  if not request.method == 'POST':
    return redirect(url_for('index'))

  query = request.form['query']

  all_relatives = read_all_relatives()
  all_relatives = [relative for relative in all_relatives if query.lower() in relative['name'].lower()]
  return render_template('search.html', relatives=all_relatives, query=query)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
  DIR = 'data/contact/'

  if not request.method == 'POST':
    comments = []
    users = []

    if not flask_login.current_user.is_anonymous and flask_login.current_user.role == "admin":
      #comments = [read_post(os.path.join(DIR, name)) for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name))]
      #comments.sort(key=get_birthday, reverse=True)

      for email, user in load_users().items():
        users.append({'email': email, 'name': user['name'], 'rank': user['role']})
    return render_template('contact.html', comments=comments, users=users)

  createDirIfNeeded(DIR)

  num_comments = len([name for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name))])
  if num_comments >= 100:
    flash('There is unusually high traffic at the moment, which forced us to stop receiving messages. Please try to send your message later again.')
    filename = 'last.md'
  else:
    filename = f'{num_comments+1}.md'

  date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  name = request.form['name']
  email = request.form['email']
  message = request.form['message']

  with open(os.path.join(DIR, filename), 'w') as file:
    file.write('---\n')
    file.write(f'"date":  "{date}",\n')
    file.write(f'"name":  "{name}",\n')
    file.write(f'"email": "{email}"\n')
    file.write('---\n')
    file.write(message)
    return redirect(url_for('index'))

@app.route('/favicon.ico')
def favicon():
  return send_from_directory(app.static_folder, 'favicon/favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/apple-touch-icon.png')
def apple_touch_icon():
  return send_from_directory(app.static_folder, 'favicon/apple-touch-icon.png', mimetype='image/png')

@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon_precomposed():
  return send_from_directory(app.static_folder, 'favicon/apple-touch-icon.png', mimetype='image/png')

@app.route('/trips/pin-icon-start.png')
def pin_icon_start():
  return send_from_directory(app.static_folder, 'icons/pin-icon-start.png', mimetype='image/png')

@app.route('/trips/pin-icon-end.png')
def pin_icon_end():
  return send_from_directory(app.static_folder, 'icons/pin-icon-end.png', mimetype='image/png')

@app.route('/trips/pin-shadow.png')
def pin_shadow():
  return send_from_directory(app.static_folder, 'icons/pin-shadow.png', mimetype='image/png')

@app.route('/robots.txt')
def robots():
  return send_from_directory(app.static_folder, 'robots.txt')

@app.errorhandler(404)
def page_not_found(e):
  # note that we set the 404 status explicitly
  return render_template('404.html'), 404
