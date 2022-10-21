import requests
import json
import os

BASE_URL = 'https://studien.rj.ost.ch/'
OUTPUT_DIRECTORY = 'data'

EXCLUDED_MODULES = ['SecSW', 'WSLS', 'WIoT', 'RKI']

content = requests.get(f'{BASE_URL}allStudies/10191_I.json').content
jsonContent = json.loads(content)

# collect categories -> kredits
kredits = jsonContent['kredits']
categories = {};
for kredit in kredits:
    kategorie = kredit['kategorien'][0]
    categories[kategorie['id']] = {
        'id': kategorie['id'],
        'required_ects': kredit['minKredits'],
        'name': kategorie['bezeichnung'],
        'short': kategorie['kuerzel'],
        'total_ects': 0,
        'modules': [],
    }

# collect modules -> zuordnungen
# "M_KatAufbauInf"
zuordnungen = jsonContent['zuordnungen']
modules = {}
# todo: map id, name, short, url, isThesis, isRequired, recommendedSem
for zuordnung in zuordnungen:
    module = {
        'id': zuordnung['id'],
        'name': zuordnung['bezeichnung'],
        'short': zuordnung['kuerzel'],
        'url': zuordnung['url'],
        'isThesis': zuordnung['istAbschlussArbeit'],
        'isRequired': zuordnung['istPflichtmodul'],
        'recommendedSem': zuordnung['semEmpfehlung'],
        'recommendedModules': [],
        'dependantModules': [],
        'focuses': []
        }
    
    if 'kategorien' in zuordnung:
        module['categories'] = zuordnung['kategorien']
        module['ects'] = zuordnung['kategorien'][0]['kreditpunkte']

        for cat in module['categories']:
            categories[cat['id']]['modules'].append(module)
            categories[cat['id']]['total_ects'] += module['ects']
        
    modules[zuordnung['id']] = module

# map recommended and dependant modules for modules (url)
for module in modules.values():
    moduleContent = json.loads(requests.get(f'{BASE_URL}{module["url"]}').content)
    if 'empfehlungen' in moduleContent:
        reqs = moduleContent['empfehlungen']
        module['recommendedModules'].append(reqs)
        for req in reqs:
            # for each recommended module, add current module to its dependant modules
            if req['id'] in modules:
                modules[req['id']]['dependantModules'].append(module)

# collect focuses -> spezialisierungen
spezialisierungen = jsonContent['spezialisierungen']
focuses = [];
for spez in spezialisierungen:
    focus = {
        'id': spez['id'],
        'url': spez['url'],
        'name': spez['bezeichnung'],
        'short': spez['kuerzel'],
        'modules': []
        }
    focusContent = json.loads(requests.get(f'{BASE_URL}{spez["url"]}').content)
    for zuordnung in focusContent['zuordnungen']:
        focus['modules'].append({'id': zuordnung['id'], 'short': zuordnung['kuerzel'], 'name': zuordnung['bezeichnung'], 'url': zuordnung['url']})
        modules[zuordnung['id']]['focuses'].append({'id': focus['id'], 'short': focus['short'], 'name': focus['name'], 'url': focus['url']})
    focuses.append(focus)

modules = list(modules.values())
categories = list(categories.values())


if not os.path.exists(OUTPUT_DIRECTORY):
    os.mkdir(OUTPUT_DIRECTORY)

with open(f'{OUTPUT_DIRECTORY}/categories_adunis.json', 'w') as output:
    json.dump(categories, output, indent=2)

with open(f'{OUTPUT_DIRECTORY}/modules_adunis.json', 'w') as output:
    json.dump(modules, output, indent=2)

with open(f'{OUTPUT_DIRECTORY}/focuses_adunis.json', 'w') as output:
    json.dump(focuses, output, indent=2)

