import requests
import json
import os
import sys

modules = {}

def write_json(data, filename):
    with open(filename, 'w') as output:
        json.dump(data, output, indent=2, ensure_ascii=False)
        output.write('\n')

def fetch_data_for_studienordnung(url, output_directory, excluded_module_ids=[]):
    global modules

    content = requests.get(url).content
    jsonContent = json.loads(content)

    categories = {}
    focuses = []

    def getIdForModule(kuerzel):
        return kuerzel.removeprefix('M_').replace('_p', 'p')

    def getIdForCategory(kuerzel):
        return kuerzel.removeprefix('I-').removeprefix('I_').removeprefix('Kat_').replace('IKTS-help', 'GWRIKTS')

    # 'kredits' contains categories
    kredits = jsonContent['kredits']
    for kredit in kredits:
        category = kredit['kategorien'][0]

        if category['kuerzel'] == 'IKTS-help':
            continue

        catId = getIdForCategory(category['kuerzel'])
        categories[catId] = {
            'id': catId,
            'required_ects': kredit['minKredits'],
            'name': category['bezeichnung'],
            'modules': [],
        }

    # 'zuordnungen' contains modules
    zuordnungen = jsonContent['zuordnungen']
    for zuordnung in zuordnungen:
        module = {
            'id': getIdForModule(zuordnung['kuerzel']),
            'name': zuordnung['bezeichnung'].strip(),
            'url': zuordnung['url'],
            'isThesis': zuordnung['istAbschlussArbeit'],
            'isRequired': zuordnung['istPflichtmodul'],
            'recommendedSemester': zuordnung['semEmpfehlung'],
            'focuses': [],
            'categories': [],
            'ects': 0,
            'isDeactivated': False,
            'term': '',
            'recommendedModuleIds': [],
            'dependentModuleIds': [],
            'successorModuleId': '',
            'predecessorModuleId': ''
        }

        if 'kategorien' in zuordnung:
            module['categories'] = [
                {'id': getIdForCategory(z['kuerzel']), 'name': z['bezeichnung'], 'ects': z['kreditpunkte']} for z in
                zuordnung['kategorien']]
            module['ects'] = zuordnung['kategorien'][0]['kreditpunkte']

        # These are the new IKTS modules. They are split into two separate modules, one of them being a "Projektarbeit".
        # This ensures that they can be differentiated in the UI.
        if zuordnung['kuerzel'].endswith('_p'):
            module['name'] += ' (Projektarbeit)'

        modules[module['id']] = module

    # load more infos about modules
    for module in modules.values():
        moduleContent = json.loads(requests.get(f'{BASE_URL}{module["url"]}').content)

        # needed for modules, whose credits do not count towards "Studiengang Informatik"
        if 'kreditpunkte' in moduleContent and module['ects'] == 0:
            module['ects'] = moduleContent['kreditpunkte']

        if 'durchfuehrungen' in moduleContent:
            if 'endSemester' in moduleContent['durchfuehrungen']:
                # todo: WS = HS, SS = FS
                module['term'] = moduleContent['durchfuehrungen']['endSemester']

        if 'nachfolger' in moduleContent:
            module['successorModuleId'] = getIdForModule(moduleContent['nachfolger']['kuerzel'])
        if 'vorgaenger' in moduleContent:
            module['predecessorModuleId'] = getIdForModule(moduleContent['vorgaenger']['kuerzel'])
    
        if 'empfehlungen' in moduleContent: 
            for empfehlung in moduleContent['empfehlungen']:
                module['recommendedModuleIds'].append(getIdForModule(empfehlung['kuerzel']))

        # For some reason each category is also present as a module.
        # This filters them out.
        if module['id'].startswith('Kat'):
            module['isDeactivated'] = True
            continue

        if module['id'] in excluded_module_ids:
            module['isDeactivated'] = True
            continue

        if 'categories' in module:
            for cat in module['categories']:
                if cat['id'] in categories:
                    categories[cat['id']]['modules'].append(
                        {'id': module['id'], 'name': module['name'], 'url': module['url']})
                elif cat['id'] == 'GWRIKTS':
                    categories['gwr']['modules'].append(
                        {'id': module['id'], 'name': module['name'], 'url': module['url']})

    for module in modules.values():
        for recommendedModuleId in module['recommendedModuleIds']:
            if recommendedModuleId in modules:
                modules[recommendedModuleId]['dependentModuleIds'].append(module['id'])
            else:
                successorIdOfRecommended = next((m['id'] for m in modules.values() if m['predecessorModuleId'] == recommendedModuleId), None)
                if not successorIdOfRecommended == None and successorIdOfRecommended in modules:
                    modules[successorIdOfRecommended]['dependentModuleIds'].append(module['id'])
                    print(f'module {module["id"]} has recommended {recommendedModuleId}, which has successor {successorIdOfRecommended}')
                else:
                    print(f'module {module["id"]} has recommended {recommendedModuleId}, which has no successor {successorIdOfRecommended}')

    modules = {key: value for (key, value) in modules.items() if value['isDeactivated'] == False}

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

            if moduleId == 'WIoT':
                moduleId = 'WsoT'

            if moduleId in modules:
                focus['modules'].append({
                    'id': moduleId,
                    'name': modules[moduleId]['name'],
                    'url': modules[moduleId]['url']})

                modules[moduleId]['focuses'].append({'id': focus['id'], 'name': focus['name'], 'url': focus['url']})

        focus['modules'].sort(key = lambda x: x['id'])
        focuses.append(focus)

    # id should be unique for each module
    idsSet = set([m['id'] for m in modules.values()])
    if len(idsSet) != len(modules):
        sys.exit(1)

    categories = list(categories.values())

    for category in categories:
        category['modules'].sort(key = lambda x: x['id'])

    categories.sort(key = lambda x: x['id'])
    focuses.sort(key = lambda x: x['id'])

    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    write_json(categories, f'{output_directory}/categories.json')
    write_json(focuses, f'{output_directory}/focuses.json')


BASE_URL = 'https://studien.ost.ch/'

# fetch_data_for_studienordnung(f'{BASE_URL}allStudies/10246_I.json', 'data23')
fetch_data_for_studienordnung(f'{BASE_URL}allStudies/10191_I.json', 'data21', ['RheKI','SecSW', 'WIoT'])
# keep MGE -> maybe ask Mirko, if it can be added again just deactivated?
# some IKTS are missing?

# {
#     "id": "MGE",
#     "name": "Mobile and GUI Engineering",
#     "url": "allModules/28254_M_MGE.json",
#     "isThesis": false,
#     "isRequired": false,
#     "recommendedSemester": 5,
#     "ects": 4,
#     "term": "HS",
#     "recommendedModuleIds": [],
#     "dependentModuleIds": [],
#     "predecessorModuleId": "",
#     "successorModuleId": "",
#     "categories_for_coloring": [
#       "Auf",
#       "Inf"
#     ]
#   },

for module in modules.values():
    module['categories_for_coloring'] = sorted([category['id'] for category in module['categories']])
    del module['focuses']
    del module['categories']
    del module['isDeactivated']

output_directory = 'data'

if not os.path.exists(output_directory):
    os.mkdir(output_directory)

modules = list(modules.values())
modules.sort(key = lambda x: x['id'])
write_json(modules, f'{output_directory}/modules.json')
