import requests
import json
import os
import sys

BASE_URL = 'https://studien.rj.ost.ch/'
OUTPUT_DIRECTORY = 'data'

content = requests.get(f'{BASE_URL}allStudies/10191_I.json').content
jsonContent = json.loads(content)

categories = {}
modules = {}
focuses = []

def getIdForModule(kuerzel):
    return kuerzel.removeprefix('M_')

def getIdForCategory(kuerzel):
    return kuerzel.removeprefix('I-').removeprefix('I_').removeprefix('Kat_')


# 'kredits' contains categories
kredits = jsonContent['kredits']
for kredit in kredits:
    category = kredit['kategorien'][0]
    catId = getIdForCategory(category['kuerzel'])
    categories[catId] = {
        'id': catId,
        'required_ects': kredit['minKredits'],
        'name': category['bezeichnung'],
        'total_ects': 0,
        'modules': [],
    }


# 'zuordnungen' contains modules
zuordnungen = jsonContent['zuordnungen']
for zuordnung in zuordnungen:
    module = {
        'id': getIdForModule(zuordnung['kuerzel']),
        'name': zuordnung['bezeichnung'],
        'url': zuordnung['url'],
        'isThesis': zuordnung['istAbschlussArbeit'],
        'isRequired': zuordnung['istPflichtmodul'],
        'recommendedSemester': zuordnung['semEmpfehlung'],
        'focuses': [],
        'categories': [],
        'ects': 0,
        'isDeactivated': False,
        'recommendedModuleIds': []
        }

    if 'kategorien' in zuordnung:
        module['categories'] = [{ 'id': getIdForCategory(z['kuerzel']), 'name': z['bezeichnung'], 'ects': z['kreditpunkte'] } for z in zuordnung['kategorien']]
        module['ects'] = zuordnung['kategorien'][0]['kreditpunkte']
        
    modules[module['id']] = module


# load more infos about modules
for module in modules.values():
    moduleContent = json.loads(requests.get(f'{BASE_URL}{module["url"]}').content)

    # needed for modules, whose credits do not count towards "Studiengang Informatik"
    if 'kreditpunkte' in moduleContent and module['ects'] == 0:
        module['ects'] = moduleContent['kreditpunkte'];
    
    if 'zustand' in moduleContent and moduleContent['zustand'] == 'deaktiviert':
        module['isDeactivated'] = True
        continue

    if 'categories' in module:
        for cat in module['categories']:
            categories[cat['id']]['modules'].append({'id': module['id'], 'name': module['name'],'url': module['url']})
            categories[cat['id']]['total_ects'] += module['ects']

    if 'empfehlungen' in moduleContent:
        for recommendation in moduleContent['empfehlungen']:
            module['recommendedModuleIds'].append(getIdForModule(recommendation['kuerzel']))

modules = {key: value for (key, value) in modules.items() if value['isDeactivated'] == False}

for module in modules.values():
    del module['isDeactivated']


# 'spezialisierungen' contains focuses
spezialisierungen = jsonContent['spezialisierungen']
for spez in spezialisierungen:
    focus = {
        'id': spez['kuerzel'],
        'url': spez['url'],
        'name': spez['bezeichnung'],
        'modules': []
        }
    focusContent = json.loads(requests.get(f'{BASE_URL}{spez["url"]}').content)
    for zuordnung in focusContent['zuordnungen']:
        moduleId = getIdForModule(zuordnung['kuerzel'])
        if moduleId in modules:
            focus['modules'].append({'id': moduleId, 'name': zuordnung['bezeichnung'], 'url': zuordnung['url']})
            modules[moduleId]['focuses'].append({'id': focus['id'], 'name': focus['name'], 'url': focus['url']})
    focuses.append(focus)


# id should be unique for each module
idsSet = set([m['id'] for m in modules.values()])
if len(idsSet) != len(modules):
    sys.exit(1)


modules = list(modules.values())
categories = list(categories.values())


if not os.path.exists(OUTPUT_DIRECTORY):
    os.mkdir(OUTPUT_DIRECTORY)

with open(f'{OUTPUT_DIRECTORY}/categories.json', 'w') as output:
    json.dump(categories, output, indent=2)

with open(f'{OUTPUT_DIRECTORY}/modules.json', 'w') as output:
    json.dump(modules, output, indent=2)

with open(f'{OUTPUT_DIRECTORY}/focuses.json', 'w') as output:
    json.dump(focuses, output, indent=2)
