import json
import os

import markdown

from genealogy import dir


def read_relative(filename: str):
  try:
    with open(filename, 'r') as f:
      text = f.read()
  except:
    return None

  data = text.split('---\n', maxsplit=2)

  body = data[-1]
  body_html = markdown.markdown(data[-1])

  relative = {'body': body, 'body_html': body_html}

  if len(data) == 3:
    meta = json.loads('{' + data[-2] + '}')
    relative.update(meta)

  return relative

def write_relative(relative: dict):
  DIR = 'data/relatives/'
  dir.createDirIfNeeded(DIR)

  filename = f'{relative["hash"]}.md'

  with open(os.path.join(DIR, filename), mode='w') as file:
    file.write('---\n')
    file.write(f'"hash":         "{relative["hash"]}",\n')
    file.write(f'"name":         "{relative["name"]}",\n')
    file.write(f'"sex":          "{relative["sex"]}",\n')
    file.write(f'"father":       "{relative["father"]}",\n')
    file.write(f'"mother":       "{relative["mother"]}",\n')
    file.write(f'"spouse":       {str(relative["spouse"])},\n')
    file.write(f'"birthday":     "{relative["birthday"]}",\n')
    file.write(f'"birthplace":   "{relative["birthplace"]}",\n')
    file.write(f'"weddingDay":   "{relative["weddingDay"]}",\n')
    file.write(f'"weddingPlace": "{relative["weddingPlace"]}",\n')
    file.write(f'"dayOfDeath":   "{relative["dayOfDeath"]}",\n')
    file.write(f'"placeOfDeath": "{relative["placeOfDeath"]}",\n')
    file.write(f'"profession":   "{relative["profession"]}",\n')
    file.write(f'"image":        "{relative["image"]}"\n')
    file.write('---\n')
    file.write(relative['body'])

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
              'image': 'unknown.png',
              'body': '',
              'body_html': ''}
  return relative
