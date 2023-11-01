import ast
import json
import os
import secrets
import subprocess
from datetime import datetime

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
  birthday = relative['birthday'].split('.')
  if len(birthday) == 3:
    return f"{birthday[2]}-{birthday[1]}-{birthday[0]}"
  return relative['birthday']

def get_relative_name(hash):
  if not hash:
    return ''

  try:
    relative = read_relative(os.path.join('data/relatives/', hash + '.md'))
    if relative['name']:
      return relative['name']
    else:
      return hash
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

def empty_relative(hash):
  relative = {'hash': hash,
              'name': '',
              'sex': '',
              'father': '',
              'mother': '',
              'spouse': [],
              'birthday': '',
              'birthplace': '',
              'weddingDay': '',
              'weddingPlace': '',
              'dayOfDeath': '',
              'placeOfDeath': '',
              'profession': '',
              'image': 'unknown.png'}
  return relative

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
  return redirect(url_for('relative', relative_hash=relative_hash))

def generateTexNode(relative, x, y):
  template = r'''\node[draw=<[color]>!70!white, fill=white, line width=0.1cm, minimum width=4cm, minimum height=9cm, path picture={
\node [draw=<[color]>!10!white, fill=<[color]>!10!white, rounded corners=0, text width=3.6cm, inner sep=0.2cm, minimum width=4cm, minimum height=3cm, anchor=north] at (0cm,-1.5cm) {\begin{dynminipage}<[name]><[born]><[married]><[died]><[profession]>\end{dynminipage}};
\fill [fill overzoom image={../relatives/images/<[image]>}, rounded corners=0] (-2cm,-1.5cm) rectangle (2cm,4.5cm);
}, rectangle, rounded corners=0.2cm] (<[id]>) at <[pos]> {};
'''

  color = 'black'
  if relative['sex'] == 'male':
    color = 'blue'
  if relative['sex'] == 'female':
    color = 'red'
  template = template.replace('<[color]>', color)

  template = template.replace('<[id]>',    f'id-{relative["hash"]}')
  template = template.replace('<[pos]>',   f'({x}cm, {y}cm)')
  template = template.replace('<[name]>',  r'\textbf{' + relative['name'] + r'}')
  template = template.replace('<[image]>', relative['image'])

  born = ''
  if relative['birthday'] or relative['birthplace']:
    born += r'\\\gtrsymBorn'
  if relative['birthday']:
    born += f'~{relative["birthday"]}'
  if relative['birthplace']:
    born += f' in {relative["birthplace"]}'

  married = ''
  if relative['weddingDay'] or relative['weddingPlace']:
    married += r'\\\gtrsymMarried'
  if relative['weddingDay']:
    married += f'~{relative["weddingDay"]}'
  if relative['weddingPlace']:
    married += f' in {relative["weddingPlace"]}'

  died = ''
  if relative['dayOfDeath'] or relative['placeOfDeath']:
    died += r'\\\gtrsymDied'
  if relative['dayOfDeath']:
    died += f'~{relative["dayOfDeath"]}'
  if relative['placeOfDeath']:
    died += f' in {relative["placeOfDeath"]}'

  template = template.replace('<[born]>', born)
  template = template.replace('<[married]>', married)
  template = template.replace('<[died]>', died)

  profession = r'\\\textit{' + relative['profession'] + r'}' if relative['profession'] else ''
  template = template.replace('<[profession]>', profession)

  return template

@app.route('/generate/<relative_hash>')
@flask_login.login_required
def generate(relative_hash):
  relatives = {}

  # import all data
  for root, _, files in os.walk('data/relatives/', topdown=False):
    for name in files:
      if name.endswith('.md'):
        try:
          relative = read_relative(os.path.join(root, name))
        except:
          pass
        else:
          relatives[relative['hash']] = relative


  ego = relatives[relative_hash]
  children = []

  # get parents
  NODES = ''
  if ego['father']:
    NODES += generateTexNode(relatives[ego['father']], 5, 26)
  if ego['mother']:
    NODES += generateTexNode(relatives[ego['mother']], 10, 26)
  NODES += generateTexNode(ego, 7.5, 13)
  i = 0
  for p in ego['spouse']:
    NODES += generateTexNode(relatives[p], 12.5 + i*5, 13)
    i += 1
  i = 0
  for p in relatives.values():
    if relative_hash in [p['father'], p['mother']]:
      NODES += generateTexNode(p, 10 + i*5, 0)
      children.append(p['hash'])
      i += 1

  HUBS = ''
  CONNECTIONS = ''

  i = 0
  for p in ego['spouse']:
    HUBS += r'\coordinate  (hub-' + relative_hash + r'-' + p + r') at (10cm, 6.5cm);'
    i += 1
  if ego['father'] and ego['mother']:
    hub = f'hub-{ego["father"]}-{ego["mother"]}'
    HUBS += f'\\coordinate ({hub}) at (7.5cm, 19.5cm);'
    CONNECTIONS += r'\draw[line width=0.4cm, white] (id-' + ego['father'] + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.4cm, white] (id-' + ego['mother'] + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.4cm, white] (id-' + relative_hash + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.2cm, black] (id-' + ego['father'] + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.2cm, black] (id-' + ego['mother'] + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.2cm, black] (id-' + relative_hash + r')|-(' + hub + ');'

  with open('data/tex/template-family.tex', 'r') as templatefile:
    template = templatefile.read()

  with open(f"data/tex/{relative_hash}.tex", 'w') as writefile:
    template = template.replace('%<<DEFINE-NODES>>', NODES)
    template = template.replace('%<<DEFINE-HUBS>>', HUBS)
    template = template.replace('%<<DEFINE-CONNECTIONS>>', CONNECTIONS)
    writefile.write(template)

  subprocess.call(['pdflatex', f'{relative_hash}.tex'], cwd='data/tex/')
  subprocess.call(['pdftoppm', f'{relative_hash}.pdf', f'{relative_hash}', '-png'], cwd='data/tex/')
  subprocess.call(['mv', f'{relative_hash}-1.png', f'../relatives/images/family/{relative_hash}.png'], cwd='data/tex/')
  return 'Ok ' + relative_hash

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

@app.route('/robots.txt')
def robots():
  return send_from_directory(app.static_folder, 'robots.txt')

@app.errorhandler(404)
def page_not_found(e):
  # note that we set the 404 status explicitly
  return render_template('404.html'), 404
