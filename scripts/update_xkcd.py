import os
import requests, json
from dataclasses import dataclass
import wikitextparser as wtp
import re
import urllib.parse
import gzip

@dataclass
class Comic:
    id: str
    explainurl: str
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
        return {"id": self.id, "title": self.title, "explainurl": self.explainurl, "characters": self.characters, "alt": self.alt, "image_url": self.image_url, "year": self.year, "month": self.month, "day": self.day, "transcript": self.transcript, "explanation": self.explanation, "complete": self.complete}

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
    explainname = urllib.parse.quote(re.match(r'.*#REDIRECT[ :]*\[\[(.*)\]\].*', r.json()['parse']['wikitext']['*'], re.IGNORECASE).group(1))
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
    return Comic(i, f'https://explainxkcd.com/wiki/index.php/{explainname}', api['title'], characters, api['alt'], api['img'], int(api['year']), int(api['month']), int(api['day']), newTranscript.strip(), sections.get('Explanation', sections.get('Eggsplanation')), complete)

done = set()

latest_api = requests.get('https://xkcd.com/info.0.json')
latest_api.raise_for_status()

latest_comic_num = latest_api.json()['num']

download = [str(i) for i in range(1,latest_comic_num+1)]

if os.path.exists('./data/xkcd/all.jsonl.gz'):
    all_f = open('./data/xkcd/all.jsonl.gz', 'rb')
    all_data = gzip.decompress(all_f.read()).decode('utf-8')
    all_f.close()
else:
    all_data = ''

for line in all_data.split('\n'):
    if line:
        l = json.loads(line)
        if l['complete']:
            done.add(l['id'])

import traceback

for num in download:
    if num in done: continue
    print(f"Downloading comic {num}")
    try:
        comic = get_xkcd_wiki(num)
    except Exception as e:
        comic = None
        print(f"ERROR ON COMIC {num}")
        print(traceback.format_exc())
    if comic:
        jsonstr = json.dumps(comic.json())
        with open(f'./data/xkcd/{num}.json', 'w') as f:
            f.write(jsonstr)
            f.flush()
        all_data += jsonstr + '\n'

all_f = open('./data/xkcd/all.jsonl.gz', 'wb')
all_f.write(gzip.compress(all_data.encode('utf-8')))
all_f.close()
