from urllib.request import urlopen
import json
import datetime
import mwparserfromhell

def parse_date(wiki_data):
    ''' Parse a mediawiki date template -- assumes years, month, day
    Input:
        a mwparser object containing just the date to be parsed
    Returns:
        datetime.date object of the date
    '''
    template = mwparserfromhell.parse(str(wiki_data.value))
    datedata = map(template.filter_templates()[0].get, [1,2,3])
    datedata = [int(str(x.value)) for x in datedata]
    return datetime.date(*datedata)


def parse_infobox(page):
    '''Parse out the nice mediawiki markdown to get birth and death
    Input:
        mediawiki unicode page string
    Returns:
        a dictionary with name(string), birth_date:DateTime, death_date:DateTime
    '''
    try:
        code = mwparserfromhell.parse(page)
        for template in code.filter_templates():
            if 'Infobox' in template.name or 'infobox' in template.name:
                # Found the right template -- attempting to extract data
                output = {}
                if 'birth_name' in template:
                    output['name'] = str(template.get('birth_name').value).strip()
                else:
                    output['name'] = str(template.get('name').value).strip()
                # Do it a bit safer by catching missing values
                for date in ['birth_date', 'death_date']:
                    try:
                        item = parse_date(template.get(date))
                    except ValueError:
                        item = None
                    output[date] = item

                # ok we are done here
                return output
        raise ValueError('Missing InfoBox')
    except Exception as exc:
        raise exc


def wiki_data(wiki_title, function=None):
    ''' Parse a wikipedia url to run a function on the data
    Input:
        wiki_title : Title of a wiki page for an individual with born and died date
        function : a python function which operates on a mediawikipage
    Output:
        Person Dictionary with ['name', 'birth_date', 'death_date'

    Example:
        person = wiki_data('Albert_Einstein', function=parse_infobox)
        assert person['name'] == 'Albert Einstein'
        assert person['birth_date'] == datetime.date(1879, 03, 14) # '14 March 1879'
        assert person['death_date'] == datetime.date(1955, 04, 18) # '18 April 1955'
    '''
    url_template = 'http://en.wikipedia.org/w/api.php?format=json&action=query&titles=%s&prop=revisions&rvprop=content'

    # Attempt to read page otherwise error out on all errors
    try:
        page_json = urlopen(url_template%(wiki_title)).readlines()[0]
    except Exception as exc:
        raise exc

    # Now that we have some json Data
    try:
        page = json.loads(page_json)
        # The data is three dictionaries deep:
        # Ignoring the extra data
        page = page['query']['pages']
        pageid = list(page.keys())[0]
        page = page[pageid]['revisions'][0]['*']
        # Page should now contain the mediawiki unicode markup text
        # runs function to try to grab what you want out of it
        # print page
        if function is None:
            return page
        return function(page)

    except Exception as exc:
        raise exc

def age(birthdate, today):
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age

def get_players(year):
    players = []
    code = mwparserfromhell.parse(wiki_data(f'{year}_FIFA_World_Cup_squads'))
    argentina = False
    for el in code.filter():
        if isinstance(el, mwparserfromhell.nodes.heading.Heading):
            title = str(getattr(el, 'title', ''))
            if 'Argentina' in title:
                argentina = True
            elif argentina and title != '':
                argentina = False

        if argentina:
            if isinstance(el, mwparserfromhell.nodes.template.Template):
                if el.name in (
                        'National football squad player',
                        'nat fs player',
                        'nat fs g player',
                    ):
                    name = el.get('name').value.strip('[]').split('(')[0].split(']')[0].strip()
                    age_els = [int(x) for x in el.get('age').value.strip('{} ').split('|') if x.isdigit()]
                    if len(age_els) != 6: continue
                    yos = age(
                        datetime.date(int(age_els[3]), int(age_els[4]), int(age_els[5])),
                        datetime.date(int(age_els[0]), int(age_els[1]), int(age_els[2])),
                    )
                    players.append((name, yos))
    return players

if __name__ == '__main__':
    # get_players(1934)
    # import sys
    # os.exit(0)
    for year in range(1930, 2026, 4):
        if year in (1938, 1942, 1946, 1950, 1954, 1970): continue
        players = get_players(year)
        if len(players) == 0:
            print(f'no players for {year}')
        else:
            print(json.dumps(players))
