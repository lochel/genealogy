import ast
import os
import subprocess
from datetime import datetime

import flask_login
from flask import (abort, flash, redirect, render_template, request,
                   send_from_directory, url_for)

from genealogy import app, dir, login_manager
from genealogy.relatives import (empty_relative, read_all_relatives,
                                 read_relative, write_relative)
from genealogy.user import (User, add_new_user, load_users)

from genealogy.graph import generate_tree


@app.after_request
def after_request(response):
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  DIR = 'data/log/'
  dir.createDirIfNeeded(DIR)

  filename = 'requests.md'
  open(os.path.join(DIR, filename), 'a').close() # make sure it exists

  with open(os.path.join(DIR, filename), "a") as file:
    file.write('| {} | {} | {} | {} | {} | {} |\n'.format(timestamp, request.remote_addr, request.method, request.scheme, request.full_path, response.status))
  return response

@app.route('/')
def index():
  relatives = read_all_relatives(6, reverse=True)
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
@flask_login.login_required
def relatives():
  relatives = read_all_relatives()
  return render_template('relatives.html', relatives=relatives)

@app.route('/relatives/<relative_hash>')
@flask_login.login_required
def relative(relative_hash):
  relatives = read_all_relatives()
  children = [p['hash'] for p in relatives if p['father'] == relative_hash or p['mother'] == relative_hash]
  relative = [p for p in relatives if p['hash'] == relative_hash]
  if relative:
    relative = relative[0]
    relative['children'] = children
  else:
    relative = empty_relative(relative_hash)
  return render_template('relative.html', relative=relative)

@app.route('/relatives/<relative_hash>/edit', methods=['GET', 'POST'])
@flask_login.login_required
def relative_edit(relative_hash):
  relatives = read_all_relatives()
  relative = [p for p in relatives if p['hash'] == relative_hash]
  if relative:
    relative = relative[0]
  else:
    relative = empty_relative(relative_hash)

  if request.method == 'GET':
    return render_template('relative_edit.html', relative=relative)

  new_hash = request.form['hash']
  relative['name'] = request.form['name']
  relative['sex'] = request.form['sex']
  relative['father'] = request.form['father']
  relative['mother'] = request.form['mother']
  relative['spouse'] = ast.literal_eval(request.form['spouse'])
  relative['birthday'] = request.form['birthday']
  relative['birthplace'] = request.form['birthplace']
  relative['weddingDay'] = request.form['weddingDay']
  relative['weddingPlace'] = request.form['weddingPlace']
  relative['dayOfDeath'] = request.form['dayOfDeath']
  relative['placeOfDeath'] = request.form['placeOfDeath']
  relative['profession'] = request.form['profession']
  relative['body'] = request.form['body']

  # Check that the new hash isn't already used
  if relative_hash != new_hash:
    for r in relatives:
      if new_hash == r['hash']:
        flash('Warning: Unable to modify hash, as it already exists.')
        return redirect(url_for('relative', relative_hash=relative_hash))

  if relative['father']:
    found = False
    for r in relatives:
      if relative['father'] == r['hash']:
        found = True
        break
    if not found:
      flash('Warning: Unable to find father, invalid cross-reference')
      return redirect(url_for('relative', relative_hash=relative_hash))

  if relative['mother']:
    found = False
    for r in relatives:
      if relative['mother'] == r['hash']:
        found = True
        break
    if not found:
      flash('Warning: Unable to find mother, invalid cross-reference')
      return redirect(url_for('relative', relative_hash=relative_hash))

  for spouse in relative['spouse']:
    found = False
    for r in relatives:
      if spouse == r['hash']:
        found = True
        break
    if not found:
      flash(f'Warning: Unable to find spouse "{spouse}", invalid cross-reference')
      return redirect(url_for('relative', relative_hash=relative_hash))

  # Change all cross-references
  if relative_hash != new_hash:
    for r in relatives:
      need_to_be_updated = False
      if r['father'] == relative_hash:
        need_to_be_updated = True
        r['father'] = new_hash
      if r['mother'] == relative_hash:
        need_to_be_updated = True
        r['mother'] = new_hash
      if relative_hash in r['spouse']:
        need_to_be_updated = True
        r['spouse'] = [s if s != relative_hash else new_hash for s in r['spouse']]
      if need_to_be_updated:
        write_relative(r)
        flash(f'Info: Cross-references updated for "{r["hash"]}"')

  if relative_hash != new_hash:
    relative['hash'] = new_hash
    os.rename('data/relatives/' + relative_hash + '.md', 'data/relatives/' + relative['hash'] + '.md')
    relative_hash = relative['hash']

  write_relative(relative)

  generate_tree(relative['hash'])
  return redirect(url_for('relative', relative_hash=relative_hash))

@app.route('/generate/<relative_hash>')
@flask_login.login_required
def generate(relative_hash):
  generate_tree(relative_hash)
  return 'Ok ' + relative_hash

@app.route('/generate')
@flask_login.login_required
def generate_all():
  relatives = read_all_relatives()
  for p in relatives:
    generate_tree(p['hash'])
  return 'Ok'

@app.route('/validate')
@flask_login.login_required
def validate():
  relatives = {}
  warnings = []

  # import all data
  for root, _, files in os.walk('data/relatives/', topdown=False):
    for name in files:
      if name.endswith('.md'):
        try:
          relative = read_relative(os.path.join(root, name))
          if relative['hash'] != name[:-3]:
            warnings.append('Wrong filename ' + os.path.join(root, name))
        except:
          warnings.append('Failed to read ' + os.path.join(root, name))
        else:
          relatives[relative['hash']] = relative

  for relative in relatives.values():
    if relative['father'] and relative['father'] not in relatives:
      warnings.append(relative['hash'] + " has an invalid cross-reference to their father " + relative['father'])
    if relative['mother'] and relative['mother'] not in relatives:
      warnings.append(relative['hash'] + " has an invalid cross-reference to their mother " + relative['mother'])
    for spouse in relative['spouse']:
      if not spouse:
        warnings.append(relative['hash'] + " contains an empty spouse entry")
      else:
        if spouse not in relatives:
          warnings.append(relative['hash'] + " has an invalid cross-reference to their spouse " + spouse)
        if relative['hash'] not in relatives[spouse]['spouse']:
          warnings.append(spouse + " is missing a cross-reference to their spouse " + relative['hash'])

  return f'{len(relatives)} relatives, {len(warnings)} warnings</br></br>' + '</br>'.join(warnings)

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
@flask_login.login_required
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

  dir.createDirIfNeeded(DIR)

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

@app.route('/robots.txt')
def robots():
  return send_from_directory(app.static_folder, 'robots.txt')

@app.errorhandler(404)
def page_not_found(e):
  # note that we set the 404 status explicitly
  return render_template('404.html'), 404
