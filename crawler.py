import requests
import json
import os
import sys

modules = {}

overwrite_module_data = {
    'ExEv': [['term', 'HS']],
    'ComEng1': [['term', 'FS']],
    'ComEng2': [['term', 'HS']],
    'NetAut': [['term', 'FS']],
    'SEProj': [['term', 'FS']],
    'PF': [['isDeactivated', True]],
    'SE1': [['successorModuleId', 'SEP2']],
    'SE2': [['successorModuleId', 'SEP2']],
    'SEP1': [['predecessorModuleId', 'SE1']],
    'SEP2': [['predecessorModuleId', 'SE2']],
    'BuPro': [['successorModuleId', 'WI2']],
    'WI2': [['predecessorModuleId', 'BuPro']],
    'RheKI': [['successorModuleId', 'RheKoI']],
    'RheKoI': [['predecessorModuleId', 'RheKI']],
    'SDW': [['successorModuleId', 'IBN']],
    'IBN': [['predecessorModuleId', 'SDW']],
    'FunProg': [['successorModuleId', 'FP']],
    'FP': [['predecessorModuleId', 'FunProg']],
    'IBN': [['predecessorModuleId', 'SDW']],
    'WIoT': [['successorModuleId', 'WsoT']],
    'WsoT': [['predecessorModuleId', 'WIoT']],
    # Inno2 and Inno_2 maybe
    # RKI, RheKoI, RheKI maybe
}

def write_json(data, filename):
    with open(filename, 'w') as output:
        json.dump(data, output, indent=2, ensure_ascii=False)
        output.write('\n')

def getIdForModule(kuerzel):
    return kuerzel.removeprefix('M_').replace('_p', 'p')

def getIdForCategory(kuerzel):
    return kuerzel.removeprefix('I-').removeprefix('I_').removeprefix('Kat_').replace('IKTS-help', 'GWRIKTS')

def create_module(content):
    return {
        'id': getIdForModule(content['kuerzel']),
        'name': content['bezeichnung'].strip(),
        'url': content['url'],
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

def set_term_for_module(module, moduleContent):
    if 'durchfuehrungen' in moduleContent:
        if 'endSemester' in moduleContent['durchfuehrungen']:
            beginSemester = moduleContent['durchfuehrungen']['beginSemester']
            endSemester = moduleContent['durchfuehrungen']['endSemester']

            if endSemester != 'HS' and endSemester != 'FS':
                print(f'Module {module["id"]} has no valid term')
            elif beginSemester != 'HS' and beginSemester != 'FS':
                module['term'] = endSemester
            elif beginSemester != endSemester:
                module['term'] = 'both'
            else:
                module['term'] = endSemester
    else:
        print(f'{module["id"]} has no term')

def set_successor_and_predecessor_for_module(module, moduleContent, modules):
    if 'nachfolger' in moduleContent and moduleContent['nachfolger']['kuerzel'] != moduleContent['kuerzel']:
        successorModuleId = getIdForModule(moduleContent['nachfolger']['kuerzel'])
        module['successorModuleId'] = successorModuleId
        if successorModuleId in modules and modules[successorModuleId]['predecessorModuleId'] == "":
            modules[successorModuleId]['predecessorModuleId'] = module['id']
    if 'vorgaenger' in moduleContent and moduleContent['vorgaenger']['kuerzel'] != moduleContent['kuerzel']:
        predecessorModuleId = getIdForModule(moduleContent['vorgaenger']['kuerzel'])
        module['predecessorModuleId'] = predecessorModuleId
        if predecessorModuleId in modules and modules[predecessorModuleId]['successorModuleId'] == "":
            modules[predecessorModuleId]['successorModuleId'] = module['id']

def set_recommended_modules_for_module(module, moduleContent):
    if 'empfehlungen' in moduleContent: 
        for empfehlung in moduleContent['empfehlungen']:
            recommendedModuleId = getIdForModule(empfehlung['kuerzel'])
            if recommendedModuleId in modules:
                # modules not for "Studiengang Informatik" can be recommended, such as AN1aE, which we do not care about
                module['recommendedModuleIds'].append(getIdForModule(empfehlung['kuerzel']))

def set_deactivated_for_module(module, moduleContent): 
    # assumption: module is deactivated, if 'zustand' is 'deaktiviert' and either (1) 'endJahr' of 'durchfuehrungen' was last year or earlier or (2) no 'durchfuehrungen' is defined
    if 'zustand' in moduleContent and moduleContent['zustand'] == 'deaktiviert':
        if 'durchfuehrungen' not in moduleContent:
            module['isDeactivated'] = True
        if 'durchfuehrungen' in moduleContent and 'endJahr' in moduleContent['durchfuehrungen']:
            currentYear = 2024
            if moduleContent['durchfuehrungen']['endJahr'] < currentYear:
                module['isDeactivated'] = True

def overwrite_module_with_data(module):
    if module['id'] not in overwrite_module_data:
        return
    overwrite_data = overwrite_module_data[module['id']]
    for data in overwrite_data:
        module[data[0]] = data[1]


def fetch_data_for_studienordnung(url, output_directory, additional_module_urls=[]):
    global modules

    content = requests.get(f'{BASE_URL}{url}').content
    jsonContent = json.loads(content)

    categories = {}
    focuses = []

    def enrich_module_from_json(module, moduleContent):
        # needed for modules, whose credits do not count towards "Studiengang Informatik"
        if 'kreditpunkte' in moduleContent and module['ects'] == 0:
            module['ects'] = moduleContent['kreditpunkte']

        set_term_for_module(module, moduleContent)

        set_successor_and_predecessor_for_module(module, moduleContent, modules)

        set_recommended_modules_for_module(module,moduleContent)

        set_deactivated_for_module(module, moduleContent)

        overwrite_module_with_data(module)

        if 'categories' in module:
            for cat in module['categories']:
                if cat['id'] in categories:
                    categories[cat['id']]['modules'].append(
                        {'id': module['id'], 'name': module['name'], 'url': module['url']})
                elif cat['id'] == 'GWRIKTS':
                    categories['gwr']['modules'].append(
                        {'id': module['id'], 'name': module['name'], 'url': module['url']})

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
        module = create_module(zuordnung)

        # For some reason each category is also present as a module.
        if module['id'].startswith('Kat'):
            continue

        if 'kategorien' in zuordnung:
            module['categories'] = [{'id': getIdForCategory(z['kuerzel']), 'name': z['bezeichnung'], 'ects': z['kreditpunkte']} for z in zuordnung['kategorien']]
            module['ects'] = zuordnung['kategorien'][0]['kreditpunkte']

        # IKTS modules are often split into two separate modules, one of them being a "Projektarbeit".
        # This ensures that they can be differentiated in the UI.
        if zuordnung['kuerzel'].endswith('_p'):
            module['name'] += ' (Projektarbeit)'

        modules[module['id']] = module

    for additional_module_url in additional_module_urls:
        moduleContent = json.loads(requests.get(f'{BASE_URL}{additional_module_url}').content)
        moduleContent['url'] = additional_module_url
        module = create_module(moduleContent)
        categoriesForStudienordnung = [z['kategorien'] for z in moduleContent['zuordnungen'] if z['url'] == url][0]
        module['categories'] = [{'id': getIdForCategory(c['kuerzel']), 'name': c['bezeichnung'], 'ects': c['kreditpunkte']} for c in categoriesForStudienordnung]
        module['ects'] = moduleContent['kreditpunkte']
        modules[module['id']] = module

    for module in modules.values():
        try:
            moduleContent = json.loads(requests.get(f'{BASE_URL}{module["url"]}').content)
        except:
            print(f'Could not get data for {module["id"]} with {BASE_URL}{module["url"]}')
            continue
        enrich_module_from_json(module, moduleContent)


    for module in modules.values():
        for recommendedModuleId in module['recommendedModuleIds']:
            if recommendedModuleId in modules:
                modules[recommendedModuleId]['dependentModuleIds'].append(module['id'])
                if modules[recommendedModuleId]['isDeactivated'] == False:
                    continue;
            
            # if recommendedModuleId is not in modules or inactive, then try to find its successor and attach module as depdendent
            successorIdOfRecommended = next((m['id'] for m in modules.values() if m['predecessorModuleId'] == recommendedModuleId), None)
            if not successorIdOfRecommended == None and successorIdOfRecommended in modules:
                modules[successorIdOfRecommended]['dependentModuleIds'].append(module['id'])

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

fetch_data_for_studienordnung('allStudies/10246_I.json', 'data23')
# keeping MGE, since UIP replaces both PF and MGE, but only MGE got removed from STD
fetch_data_for_studienordnung('allStudies/10191_I.json', 'data21', ['allModules/28254_M_MGE.json'])

for module in modules.values():
    module['categoriesForColoring'] = sorted([category['id'] for category in module['categories']])
    del module['focuses']
    del module['categories']

output_directory = 'data'

if not os.path.exists(output_directory):
    os.mkdir(output_directory)

modules = list(modules.values())
modules.sort(key = lambda x: x['id'])
write_json(modules, f'{output_directory}/modules.json')
