import os
import subprocess

from genealogy.relatives import read_relative


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

def generate_tree(relative_hash):
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
  children = [p['hash'] for p in relatives.values() if p['father'] == relative_hash or p['mother'] == relative_hash]

  # get parents
  NODES = ''
  HUBS = ''
  CONNECTIONS = ''

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
  for p in children:
    NODES += generateTexNode(relatives[p], 10 + i*5, 0)
    i += 1
    hub = f'hub-{relatives[p]["father"]}-{relatives[p]["mother"]}'
    CONNECTIONS += r'\draw[line width=0.4cm, white] (id-' + p + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.2cm, black] (id-' + p + r')|-(' + hub + ');'

  i = 0
  for p in ego['spouse']:
    hub = f'hub-{relative_hash}-{p}'
    HUBS += f'\\coordinate ({hub}) at ({10+i*5}cm, {6.5+0.5*i}cm);'
    hub = f'hub-{p}-{relative_hash}'
    HUBS += f'\\coordinate ({hub}) at ({10+i*5}cm, {6.5+0.5*i}cm);'
    CONNECTIONS += r'\draw[line width=0.4cm, white] (id-' + relative_hash + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.4cm, white] (id-' + p + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.2cm, black] (id-' + relative_hash + r')|-(' + hub + ');'
    CONNECTIONS += r'\draw[line width=0.2cm, black] (id-' + p + r')|-(' + hub + ');'
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
