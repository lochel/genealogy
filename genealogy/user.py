import os
import secrets

import flask_login
from flask import (abort, flash, redirect, render_template, request,
                   send_from_directory, url_for)

from genealogy import app, dir, login_manager
from genealogy.relatives import (empty_relative, read_all_relatives,
                                 read_relative, write_relative)

def load_users():
  DIR = 'data/login/'
  dir.createDirIfNeeded(DIR)

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
  dir.createDirIfNeeded(DIR)

  filename = 'login.md'
  open(os.path.join(DIR, filename), 'a').close() # make sure it exists

  password = secrets.token_hex()
  with open(os.path.join(DIR, filename), "a") as file:
      file.write(f'inactive;{name};{email};{password}\n')

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
