import requests, json
from dataclasses import dataclass
import wikitextparser as wtp
import re
import urllib.parse

@dataclass
class Comic:
    id: str
    title: str
    characters: list[str]
    alt: str
    image_url: str
    year: int
    month: int
    day: int
    transcript: str
    explanation: str
    complete: bool

    def json(self):
        return {"title": self.title, "characters": self.characters, "alt": self.alt, "image_url": self.image_url, "year": self.year, "month": self.month, "day": self.day, "transcript": self.transcript, "explanation": self.explanation, "complete": self.complete}

def get_xkcd_wiki(i):
    r = requests.get(f'https://xkcd.com/{i}/info.0.json')
    if r.status_code != 200:
        print(f"Error getting data from xkcd.com for comic {i}")
        return None
    api = r.json()
    r = requests.get(f'https://www.explainxkcd.com/wiki/api.php?action=parse&page={api["num"]}&prop=wikitext&sectiontitle=Explanation&format=json')
    if r.status_code != 200:
        print(f"Error getting redirect from explainxkcd.com for comic {i}")
        return None
    explainname = urllib.parse.quote(re.match(r'#REDIRECT ?\[\[(.*)\]\].*', r.json()['parse']['wikitext']['*'], re.IGNORECASE).group(1))
    r = requests.get(f'https://www.explainxkcd.com/wiki/api.php?action=parse&page={explainname}&prop=wikitext&sectiontitle=Explanation&format=json')
    if r.status_code != 200:
        print(f"Error getting data from explainxkcd.com for comic {explainname}")
        return None
    explainwikitext = r.json()['parse']['wikitext']['*']
    discussionloc = explainwikitext.lower().index('{{comic discussion}}') if '{{comic discussion}}' in explainwikitext.lower() else explainwikitext.index('==Discussion==')
    before_discussion = explainwikitext[:discussionloc]
    after_discussion = explainwikitext[discussionloc:]

    complete = True
    if '{{incomplete|' in explainwikitext:
        complete = False

    explain = wtp.parse(before_discussion)

    sections = {}
    for section in explain.sections:
        if section.title is None: continue
        sections[section.title.strip()] = wtp.parse(section.contents).plain_text()

    characters = [i.group(1) for i in re.finditer(r'\[\[Category:Comics featuring (.*)\]\]', after_discussion)]

    newTranscript = ''
    if 'Transcript' in sections:
        for line in sections['Transcript'].split('\n'):
            line = line.strip().lstrip(':')
            newTranscript += line + '\n'
    else:
        print(f"Comic {i} doesn't have a transcript")
    return Comic(i, api['title'], characters, api['alt'], api['img'], int(api['year']), int(api['month']), int(api['day']), newTranscript.strip(), sections.get('Explanation', sections['Eggsplanation']), complete)

data = {}

with open('./data/xkcd.json') as f:
    data = json.load(f)

latest_api = requests.get('https://xkcd.com/info.0.json')
latest_api.raise_for_status()

latest_comic_num = latest_api.json()['num']

done = set([i for i in data if data[i]["complete"]])
download = [str(i) for i in range(1,latest_comic_num+1)]

try:
    for num in download:
        if num in done: continue
        print(f"Downloading comic {num}")
        comic = get_xkcd_wiki(num)
        if comic:
            data[comic.id] = comic.json()
finally:
    print("Saving")
    with open('./data/xkcd.json', 'w') as f:
        data_json = '{\n'
        keys = list(data.keys())
        for num in keys:
            if num != keys[-1]:
                data_json += f'"{num}":' + json.dumps(data[num], separators=(',', ':')) + ',\n'
            else:
                data_json += f'"{num}":' + json.dumps(data[num], separators=(',', ':')) + '\n'
        data_json += '}\n'
        f.write(data_json)
        f.flush()
