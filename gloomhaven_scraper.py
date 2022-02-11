#!/usr/bin/env python3

import re
import requests
import requests_cache
import logging
from collections import OrderedDict
import pandas as pd
from gspread_pandas import Spread

requests_cache.install_cache('cache')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log_format = '[%(asctime)s] %(levelname)-8s %(message)s'
formatter = logging.Formatter(log_format)
s_handler = logging.StreamHandler()
s_handler.setLevel(logging.DEBUG)
s_handler.setFormatter(formatter)
log.addHandler(s_handler)

spreadsheet_name = 'gloomhaven_abilities'

spread = Spread('gloomhaven_abilities')

##

def get_reddit_wiki_markdown(url):
    """Given a Reddit wiki url, return the markdown as a string."""
    if not url.endswith('.json'):
        url = f'{url}.json'
    req = requests.get(url, headers={'User-agent': 'Gloomhaven Sheet 0.1'})
    md = req.json()['data']['content_md']
    return md

# declare a dictionary that will contain the dataframes
dataframes = {}

for class_number in [str(i + 1).zfill(2) for i in range(17)]:
    abilities_url = f'https://reddit.com/r/Gloomhaven/wiki/class_guides/class{class_number}/abilities'
    log.debug(abilities_url)
    abilities_markdown = get_reddit_wiki_markdown(abilities_url)
    this_class = None
    this_level = None
    rows = []

    # obtain the class name, which we expect to be near the top of each page
    for chunk in abilities_markdown.split('\r\n\r\n'):
        chunk = chunk.strip()

        m = re.match(r'^#\s+(.+)\s*Abilities', chunk)
        if m:
            this_class = m.group(1).strip().lower().replace(' ', '_')
            log.debug(f'this_class = {this_class}')
            break

    # obtain the abilities
    for chunk in abilities_markdown.split('\r\n\r\n'):
        chunk = chunk.strip()

        # obtain the ability level, which we expect to be updated before we reach the relevant ability cards
        m = re.match(r'^##.*(\w+)\s*Abilities', chunk)
        if m:
            this_level = m.group(1)
            log.debug(f'this_level = {this_level}')
            continue

        # obtain the initiative and ability name from the first line
        m = re.match(r'^###\s*\((?P<initiative>\d+)\)\s*(?P<name>.+)', chunk)
        if m:
            this_initiative = m.groupdict()['initiative']
            this_name = m.groupdict()['name'].strip()
            # slice the chunk into a list that contains both the top and bottom abilities
            ability_lines = [i.strip() for i in chunk.split('\r\n')][1:]
            # the lines before the dashes are the top ability
            this_top = '\n'.join(ability_lines[:ability_lines.index('─────')])
            # the lines after the dashes are the bottom ability
            this_bottom = '\n'.join(ability_lines[ability_lines.index('─────') + 1:])
            log.debug(this_top)
            log.debug(this_bottom)

            row = OrderedDict()
            row['level'] = this_level
            row['name'] = this_name
            row['initiative'] = this_initiative
            row['top'] = this_top
            row['bottom'] = this_bottom

            rows.append(row)

    dataframes[f'{class_number}_{this_class}'] = pd.DataFrame(rows)

##

for worksheet_name in dataframes.keys():
    log.debug(f'Updating worksheet: {worksheet_name}')
    spread.df_to_sheet(dataframes[worksheet_name], index=False, sheet=worksheet_name, start='A1', replace=True)
