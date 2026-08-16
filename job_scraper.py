"""Construction job scraper: US entry-level / 0-2 YOE.
Supports Greenhouse, Lever, Ashby, Workday, SmartRecruiters, JSON-LD and safe career-search crawling.
"""
import os,re,html,time,warnings,json
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin,urlparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import pandas as pd
import requests
from bs4 import BeautifulSoup,MarkupResemblesLocatorWarning
warnings.filterwarnings('ignore',category=MarkupResemblesLocatorWarning)

SESSION=requests.Session()
SESSION.headers.update({'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'en-US,en;q=0.9'})
results=[]; old_links=set(); errors=[]
# Strict construction-role classifier. Avoids generic matches such as software "field engineering"
# and prevents service/marketing pages from becoming fake job postings.
DIRECT_ROLES=[
    'project engineer','field engineer','construction engineer','construction coordinator',
    'project coordinator','assistant project manager','assistant construction manager',
    'assistant superintendent','field coordinator','assistant estimator','junior estimator',
    'estimating engineer','cost engineer','bim engineer','bim coordinator','vdc engineer',
    'vdc coordinator','mep coordinator','mep engineer','site engineer','office engineer',
    'construction inspector','safety engineer','quantity surveyor','graduate civil engineer',
    'entry level civil engineer','entry-level civil engineer'
]
CONTEXT_ROLES=['estimator','scheduler','project scheduler','planning engineer','project controls','cost analyst',
               'civil engineer','structural engineer','quality engineer','qa/qc','quality control',
               'field inspector','ehs engineer','design coordinator','preconstruction']
CONSTRUCTION_CONTEXT=['construction','general contractor','contractor','building','jobsite','job site','civil',
                      'infrastructure','concrete','commercial construction','preconstruction','subcontractor',
                      'project controls','bim','vdc','mep','superintendent','estimating','field operations']
TITLE_EXCLUDES=['senior',' sr.',' sr ','principal','director','vice president',' vp ','head of','chief','executive',
                'general superintendent','senior superintendent','project executive','lead ','manager','architect',
                'engineer iii','engineer iv','estimator iii','superintendent ii','superintendent iii']
EXP_PATTERNS=[re.compile(r'(?:minimum|min\.?|at least|requires?|required|must have|need(?:s|ed)?)[^.!;]{0,70}?(\d+)\s*\+?\s*(?:years?|yrs?)',re.I),re.compile(r'(\d+)\s*\+\s*(?:years?|yrs?)[^.!;]{0,45}?(?:required|minimum|experience)',re.I),re.compile(r'(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:years?|yrs?)[^.!;]{0,55}?(?:required|minimum|experience)',re.I)]

def clean(s):
    s=str(s or '')
    if '<' not in s and '>' not in s: return html.unescape(s).strip()
    return BeautifulSoup(html.unescape(s),'html.parser').get_text(' ',strip=True)
def log(c,m): errors.append(f'[WARN] {c}: {str(m)[:220]}')
def role_match(title,desc=''):
    t=' '+clean(title).lower()+' '
    d=clean(desc).lower()
    # Assistant Project/Construction Manager are valid early-career roles; other managers are not.
    protected=('assistant project manager' in t or 'assistant construction manager' in t)
    if not protected and any(k in t for k in TITLE_EXCLUDES): return False
    if any(k in t for k in DIRECT_ROLES):
        # "field engineer" can be non-construction at tech companies; require construction context in description
        # unless the title itself contains an unmistakably construction-specific role.
        if 'field engineer' in t and not any(x in d for x in CONSTRUCTION_CONTEXT): return False
        return True
    if any(k in t for k in CONTEXT_ROLES):
        return any(x in d for x in CONSTRUCTION_CONTEXT)
    return False
def experience_ok(title,desc=''):
    t=(clean(title)+' '+clean(desc)).lower()
    for p in EXP_PATTERNS:
        for m in p.finditer(t):
            nums=[int(x) for x in m.groups() if x and str(x).isdigit()]
            if nums and nums[0]>2:
                prefix=t[max(0,m.start()-35):m.start()]
                if 'preferred' not in prefix: return False
    return True
def is_us(loc):
    if not loc: return True
    s=' '+clean(loc).lower()+' '
    if any(x in s for x in ['united states',' usa ',' u.s. ','remote - us','remote, us','remote us']): return True
    states='al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny nc nd oh ok or pa ri sc sd tn tx ut vt va wa wv wi wy dc'.split()
    names='alabama alaska arizona arkansas california colorado connecticut delaware florida georgia hawaii idaho illinois indiana iowa kansas kentucky louisiana maine maryland massachusetts michigan minnesota mississippi missouri montana nebraska nevada ohio oklahoma oregon pennsylvania tennessee texas utah vermont virginia washington wisconsin wyoming'.split()
    return any(n in s for n in names) or any(re.search(r'[, ]'+a+r'(?:[, ]|$)',s) for a in states) or bool(re.search(r'\b(new york|new jersey|new mexico|new hampshire|north carolina|south carolina|north dakota|south dakota|rhode island|west virginia)\b',s))
def add(company,title,location,link,posted='N/A',desc=''):
    if not link or link in old_links: return
    if role_match(title,desc) and experience_ok(title,desc) and is_us(location):
        results.append({'company':company,'title':clean(title),'location':clean(location) or 'N/A','link':link,'posted':posted}); old_links.add(link)

def greenhouse(url,company):
    m=re.search(r'(?:boards|job-boards)\.greenhouse\.io/([^/?#]+)',url); 
    if not m: return False
    org=m.group(1); r=SESSION.get(f'https://boards-api.greenhouse.io/v1/boards/{org}/jobs?content=true',timeout=20); r.raise_for_status()
    for j in r.json().get('jobs',[]): add(company,j.get('title'),j.get('location',{}).get('name'),j.get('absolute_url'),j.get('updated_at','N/A'),j.get('content',''))
    return True
def lever(url,company):
    m=re.search(r'jobs\.lever\.co/([^/?#]+)',url); 
    if not m: return False
    org=m.group(1); r=SESSION.get(f'https://api.lever.co/v0/postings/{org}?mode=json',timeout=20); r.raise_for_status()
    for j in r.json(): add(company,j.get('text'),j.get('categories',{}).get('location'),j.get('hostedUrl'),'N/A',(j.get('descriptionPlain') or '')+' '+(j.get('additionalPlain') or ''))
    return True
def ashby(url,company):
    m=re.search(r'jobs\.ashbyhq\.com/([^/?#]+)',url); 
    if not m: return False
    org=m.group(1); r=SESSION.get(f'https://api.ashbyhq.com/posting-api/job-board/{org}',timeout=20); r.raise_for_status()
    for j in r.json().get('jobs',[]): add(company,j.get('title'),j.get('location'),j.get('jobUrl'),j.get('publishedAt','N/A'),j.get('descriptionPlain') or j.get('descriptionHtml') or '')
    return True
def workday(url,company):
    p=urlparse(url); host=p.netloc
    hm=re.match(r'([^.]+)\.(wd\d+)\.myworkdayjobs\.com',host)
    if not hm: return False
    sub,wd=hm.groups(); parts=[x for x in p.path.split('/') if x and x.lower() not in ('en-us','en_us','en')]
    if not parts: return False
    site=parts[0]; api=f'https://{sub}.{wd}.myworkdayjobs.com/wday/cxs/{sub}/{site}/jobs'; headers={'Content-Type':'application/json','Accept':'application/json','Origin':f'https://{host}','Referer':url,'Accept-Language':'en-US,en;q=0.9'}
    offset=0
    while offset<1000:
        r=SESSION.post(api,json={'appliedFacets':{},'limit':20,'offset':offset,'searchText':''},headers=headers,timeout=20)
        if r.status_code!=200: raise RuntimeError(f'Workday {r.status_code} at {api}')
        data=r.json(); posts=data.get('jobPostings',[])
        if not posts: break
        for j in posts:
            title=j.get('title',''); loc=j.get('locationsText',''); path=j.get('externalPath',''); link=f'https://{sub}.{wd}.myworkdayjobs.com/en-US/{site}{path}'; desc=''
            if path and (any(k in (' '+clean(title).lower()+' ') for k in DIRECT_ROLES+CONTEXT_ROLES)):
                try:
                    d=SESSION.get(f'https://{sub}.{wd}.myworkdayjobs.com/wday/cxs/{sub}/{site}{path}',timeout=12)
                    if d.ok: desc=d.json().get('jobPostingInfo',{}).get('jobDescription','')
                except Exception: pass
            add(company,title,loc,link,j.get('postedOn','N/A'),desc)
        offset+=20
        if offset>=data.get('total',0): break
    return True

def smartrecruiters(url,company):
    m=re.search(r'(?:jobs\.smartrecruiters\.com|careers\.smartrecruiters\.com)/([^/?#]+)',url,re.I)
    if not m: return False
    org=m.group(1); off=0
    while off<1000:
        r=SESSION.get(f'https://api.smartrecruiters.com/v1/companies/{org}/postings',params={'limit':100,'offset':off},timeout=20); r.raise_for_status(); data=r.json()
        posts=data.get('content',[])
        if not posts: break
        for j in posts:
            loc=j.get('location') or {}; location=', '.join(str(loc.get(x,'')) for x in ('city','region','country') if loc.get(x))
            jid=j.get('id'); link=f'https://jobs.smartrecruiters.com/{org}/{jid}' if jid else j.get('ref')
            desc=''
            if jid:
                try:
                    d=SESSION.get(f'https://api.smartrecruiters.com/v1/companies/{org}/postings/{jid}',timeout=12)
                    if d.ok:
                        dj=d.json(); desc=' '.join(clean(x.get('text','')) for x in (dj.get('jobAd',{}).get('sections',{}) or {}).values() if isinstance(x,dict))
                except Exception: pass
            add(company,j.get('name'),location,link,j.get('releasedDate','N/A'),desc)
        off+=len(posts)
        if off>=data.get('totalFound',0): break
    return True

def jsonld_jobs(base,text,company):
    soup=BeautifulSoup(text,'html.parser'); count=0
    for tag in soup.find_all('script',type=lambda x:x and 'ld+json' in x.lower()):
        try: data=json.loads(tag.string or tag.get_text() or '{}')
        except Exception: continue
        stack=data if isinstance(data,list) else [data]
        for obj in stack:
            if isinstance(obj,dict) and '@graph' in obj and isinstance(obj['@graph'],list): stack.extend(obj['@graph'])
            if not isinstance(obj,dict) or str(obj.get('@type','')).lower()!='jobposting': continue
            title=obj.get('title',''); desc=obj.get('description',''); link=obj.get('url') or base
            loc=''
            jl=obj.get('jobLocation') or []
            if isinstance(jl,dict): jl=[jl]
            bits=[]
            for item in jl:
                a=(item or {}).get('address',{}) if isinstance(item,dict) else {}
                if isinstance(a,dict): bits.append(', '.join(str(a.get(k,'')) for k in ('addressLocality','addressRegion','addressCountry') if a.get(k)))
            loc='; '.join(x for x in bits if x)
            add(company,title,loc,link,obj.get('datePosted','N/A'),desc); count+=1
    return count

def safe_job_links(base,text):
    soup=BeautifulSoup(text,'html.parser'); out=[]
    host=urlparse(base).netloc.lower()
    pats=[r'/job/[^?#]+',r'/jobs/[^/?#]*\d[^?#]*',r'/careers/(?:job|position)/[^?#]+',r'/positions/[^?#]*\d[^?#]*']
    for a in soup.find_all('a',href=True):
        u=urljoin(base,a['href']); pu=urlparse(u)
        if pu.netloc.lower()!=host: continue
        if any(re.search(p,pu.path,re.I) for p in pats): out.append(u.split('#')[0])
    return list(dict.fromkeys(out))[:300]

def crawl_search_page(url,company):
    r=SESSION.get(url,timeout=25,allow_redirects=True); r.raise_for_status()
    found=jsonld_jobs(r.url,r.text,company)
    links=safe_job_links(r.url,r.text)
    # Only fetch URLs that structurally look like job-detail pages. This prevents service pages from becoming jobs.
    for u in links[:160]:
        try:
            d=SESSION.get(u,timeout=12,allow_redirects=True)
            if d.ok: found+=jsonld_jobs(d.url,d.text,company)
        except Exception: pass
    return found

def ats_from_links(base,text):
    soup=BeautifulSoup(text,'html.parser')
    links=[urljoin(base,a.get('href')) for a in soup.find_all('a',href=True)]
    for u in links:
        if re.search(r'(?:boards|job-boards)\.greenhouse\.io/[^/?#]+',u): return 'greenhouse',u
        if re.search(r'jobs\.lever\.co/[^/?#]+',u): return 'lever',u
        if re.search(r'jobs\.ashbyhq\.com/[^/?#]+',u): return 'ashby',u
        if re.search(r'\.wd\d+\.myworkdayjobs\.com/',u): return 'workday',u
        if re.search(r'(?:jobs|careers)\.smartrecruiters\.com/[^/?#]+',u): return 'smartrecruiters',u
    return None,None

def generic(url,company):
    """Safe discovery: ATS first, then structured JobPosting data only.
    Never converts ordinary service/marketing pages into jobs.
    """
    r=SESSION.get(url,timeout=25,allow_redirects=True)
    if r.status_code in (401,403,406,429):
        raise RuntimeError(f'public careers page blocked ({r.status_code}); direct source adapter needed')
    r.raise_for_status()
    plat,ats=ats_from_links(r.url,r.text)
    if plat:
        return {'greenhouse':greenhouse,'lever':lever,'ashby':ashby,'workday':workday,'smartrecruiters':smartrecruiters}[plat](ats,company)
    n=crawl_search_page(r.url,company)
    if n: return True
    raise RuntimeError('no supported ATS or structured JobPosting data discovered')

def scrape(row):
    company=str(row.company).strip(); url=str(row.careers_url).strip(); platform=str(row.platform).strip().lower()
    try:
        fn={'greenhouse':greenhouse,'lever':lever,'ashby':ashby,'workday':workday,'smartrecruiters':smartrecruiters,'generic':generic,'auto':generic}.get(platform,generic)
        fn(url,company)
    except Exception as e: log(company,e)

def filename(): return f"{datetime.now().day}-{datetime.now().strftime('%B')}-Construction-Jobs.md"
def write_output(jobs):
    if not jobs: print('No new matching jobs.'); return
    jobs=sorted(jobs,key=lambda x:(x['company'].lower(),x['title'].lower())); f=filename(); today=datetime.now().strftime('%B %d, %Y'); ts=datetime.now().strftime('%Y-%m-%d %H:%M')
    table='| Company | Location | Role | Apply | Posted |\n|---|---|---|---|---|\n'+''.join(f"| **{j['company']}** | {j['location']} | {j['title']} | [Apply]({j['link']}) | {j['posted']} |\n" for j in jobs)
    old=Path(f).read_text(encoding='utf-8') if Path(f).exists() else ''; header=f'# Construction Entry-Level Jobs — {today}\n> US construction/civil roles; rejects explicit required minimum experience above 2 years.\n\n'; block=f'## Batch {ts} — {len(jobs)} new jobs\n\n{table}\n'
    Path(f).write_text(header+block+'\n'+old,encoding='utf-8'); Path('README.md').write_text(header+block,encoding='utf-8')
def telegram(jobs):
    token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat or not jobs:return
    msg=f"🏗️ *{len(jobs)} new construction jobs*\n0–2 YOE / entry-level / US\n\n"
    for j in jobs[:12]: msg+=f"*{j['company']}* — {j['title']}\n📍 {j['location']}\n[Apply]({j['link']})\n\n"
    SESSION.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':msg[:4000],'parse_mode':'Markdown','disable_web_page_preview':True},timeout=10)

if __name__=='__main__':
    p=Path('seen_links.csv')
    if p.exists():
        try: old_links.update(pd.read_csv(p)['link'].dropna().astype(str))
        except Exception: pass
    df=pd.read_csv('companies.csv').dropna(subset=['company','careers_url']).drop_duplicates(subset=['company','careers_url'])
    print(f'Scraping {len(df)} company sources for construction roles (0–2 YOE)...')
    with ThreadPoolExecutor(max_workers=5) as ex:
        fs=[ex.submit(scrape,r) for r in df.itertuples(index=False)]
        for f in as_completed(fs): f.result()
    jobs=list({j['link']:j for j in results}.values()); print(f'Found {len(jobs)} new matching jobs'); write_output(jobs)
    if jobs: pd.DataFrame({'link':[j['link'] for j in jobs]}).to_csv(p,mode='a',index=False,header=not p.exists())
    telegram(jobs)
    if errors:
        print(f'\n{len(errors)} source warnings (first 30):'); print('\n'.join(errors[:30]))
