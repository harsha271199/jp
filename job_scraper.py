"""Construction job scraper V12: US entry-level / 0-2 YOE.
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
results=[]; old_links=set(); errors=[]; source_health=[]
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
NON_CONSTRUCTION_TITLE_EXCLUDES=['maintenance','facility maintenance','facilities maintenance','maintenance planner','maintenance scheduler','technician','mechanic','operations engineer','operations technician','data center technician','critical facilities technician','service engineer','sales engineer','customer engineer','solutions engineer','software engineer','field service engineer','field application engineer','field applications engineer']
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
    if any(k in t for k in NON_CONSTRUCTION_TITLE_EXCLUDES): return False
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
        if 'successfactors.com' in urlparse(u).netloc.lower(): return 'successfactors',u
    return None,None

def successfactors(url,company):
    """Scrape public SuccessFactors-style career sites conservatively.
    Only follows URLs whose path itself looks like a job detail page.
    """
    r=SESSION.get(url,timeout=25,allow_redirects=True); r.raise_for_status()
    found=jsonld_jobs(r.url,r.text,company)
    soup=BeautifulSoup(r.text,'html.parser')
    links=[]
    for a in soup.find_all('a',href=True):
        u=urljoin(r.url,a['href']); path=urlparse(u).path.lower()
        # Common SuccessFactors public job-detail URL shapes.
        if re.search(r'/job/[^/]+/.+?/\d+/?$',path) or re.search(r'/job/[^/]+/\d+/?$',path):
            links.append(u.split('#')[0])
    for u in list(dict.fromkeys(links))[:250]:
        try:
            d=SESSION.get(u,timeout=12,allow_redirects=True)
            if not d.ok: continue
            n=jsonld_jobs(d.url,d.text,company)
            if n: found+=n; continue
            # SuccessFactors pages often have no JSON-LD. Parse only a real /job/.../<numeric-id> page.
            ds=BeautifulSoup(d.text,'html.parser')
            h=ds.find(['h1','h2'])
            title=clean(h.get_text(' ',strip=True) if h else '')
            text=clean(ds.get_text(' ',strip=True))
            loc=''
            lm=re.search(r'(?:Location|Primary Location)\s*:?\s*([A-Za-z .-]+,\s*[A-Z]{2}(?:,\s*US)?)',text,re.I)
            if lm: loc=lm.group(1)
            if title: add(company,title,loc,d.url,'N/A',text)
        except Exception: pass
    if found or links: return True
    raise RuntimeError('no SuccessFactors job-detail links discovered')

def phenom(url,company):
    """Conservative adapter for Phenom-style career sites.
    Follows only URLs containing /job/ plus a requisition-like identifier.
    """
    r=SESSION.get(url,timeout=25,allow_redirects=True); r.raise_for_status()
    found=jsonld_jobs(r.url,r.text,company)
    soup=BeautifulSoup(r.text,'html.parser'); links=[]
    for a in soup.find_all('a',href=True):
        u=urljoin(r.url,a['href']); path=urlparse(u).path.lower()
        if '/job/' in path and (re.search(r'\d{4,}',path) or re.search(r'/(?:r|req|jr)[-_]?\d+',path,re.I)):
            links.append(u.split('#')[0])
    for u in list(dict.fromkeys(links))[:250]:
        try:
            d=SESSION.get(u,timeout=12,allow_redirects=True)
            if d.ok: found+=jsonld_jobs(d.url,d.text,company)
        except Exception: pass
    if found or links: return True
    raise RuntimeError('no Phenom job-detail links discovered')



def kiewit(url,company):
    """Kiewit adapter: scrape the official Entry Level SuccessFactors listing directly.
    This intentionally targets Kiewit's Entry Level board to reduce senior-role noise.
    """
    pages=[
        'https://kiewitcareers.kiewit.com/go/Kiewit_Interns-Entry-Level/8156300/',
        'https://kiewitcareers.kiewit.com/go/Kiewit_Interns-Entry-Level/8156300/25/',
        'https://kiewitcareers.kiewit.com/go/Kiewit_Interns-Entry-Level/8156300/50/',
    ]
    seen=set(); discovered=0
    for page in pages:
        r=SESSION.get(page,timeout=25,allow_redirects=True); r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        for a in soup.find_all('a',href=True):
            title=clean(a.get_text(' ',strip=True)); href=urljoin(r.url,a['href'])
            if not title or href in seen: continue
            path=urlparse(href).path
            # SAP SuccessFactors job detail pages normally end in a numeric requisition id.
            if '/job/' not in path.lower() or not re.search(r'/\d+/?$',path): continue
            seen.add(href); discovered+=1
            loc=''; desc=''; posted='N/A'
            try:
                d=SESSION.get(href,timeout=15,allow_redirects=True)
                if d.ok:
                    ds=BeautifulSoup(d.text,'html.parser'); txt=clean(ds.get_text(' ',strip=True)); desc=txt
                    lm=re.search(r'(?:Location|Primary Location)\s*:?\s*([^|]{2,80}?)(?:\s{2,}|Job Level|Department|Date)',txt,re.I)
                    if lm: loc=clean(lm.group(1))
                    dm=re.search(r'(?:Date|Posted)\s*:?\s*([A-Z][a-z]{2}\s+\d{1,2},\s+20\d{2})',txt)
                    if dm: posted=dm.group(1)
            except Exception: pass
            add(company,title,loc,href,posted,desc)
    if discovered: return True
    raise RuntimeError('Kiewit entry-level job links not discovered')


def dpr(url,company):
    """DPR adapter: parse actual job cards from DPR's official current-positions page.
    The page itself exposes title, location, description snippet and job-detail links.
    """
    r=SESSION.get(url,timeout=25,allow_redirects=True); r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser'); discovered=0; seen=set()
    for a in soup.find_all('a',href=True):
        title=clean(a.get_text(' ',strip=True)); href=urljoin(r.url,a['href'])
        if not title or href in seen: continue
        # Keep only links that sit in a job-card-like region and reject navigation/marketing links.
        low=title.lower()
        if not any(k in low for k in DIRECT_ROLES+CONTEXT_ROLES): continue
        parent=a
        for _ in range(5):
            if parent and parent.parent: parent=parent.parent
        block=clean(parent.get_text(' ',strip=True) if parent else '')
        if len(block)<40: continue
        seen.add(href); discovered+=1
        # Extract a US-looking location from the nearby card text when available.
        loc=''
        m=re.search(r'([A-Za-z .-]+,\s*[A-Z]{2})(?:\s*[•|]|\s{2,}|$)',block)
        if m: loc=m.group(1)
        desc=block
        # Detail page often contains a fuller description; use it when accessible.
        try:
            d=SESSION.get(href,timeout=12,allow_redirects=True)
            if d.ok:
                detail=clean(BeautifulSoup(d.text,'html.parser').get_text(' ',strip=True))
                if len(detail)>len(desc): desc=detail
        except Exception: pass
        add(company,title,loc,href,'N/A',desc)
    if discovered: return True
    raise RuntimeError('DPR job cards not discovered')


def verified_listing(url,company):
    """Safe adapter for verified career portals.
    It never treats marketing/service pages as jobs. A candidate must either expose
    JobPosting JSON-LD or have a job-like URL plus application/job-description evidence.
    """
    r=SESSION.get(url,timeout=25,allow_redirects=True)
    if r.status_code in (401,403,406,429):
        raise RuntimeError(f'verified career portal blocked ({r.status_code})')
    r.raise_for_status()
    # Prefer a real ATS linked from the official portal.
    plat,ats=ats_from_links(r.url,r.text)
    if plat:
        return {'greenhouse':greenhouse,'lever':lever,'ashby':ashby,'workday':workday,'smartrecruiters':smartrecruiters,'successfactors':successfactors}[plat](ats,company)
    found=jsonld_jobs(r.url,r.text,company)
    soup=BeautifulSoup(r.text,'html.parser')
    candidates=[]
    for a in soup.find_all('a',href=True):
        href=urljoin(r.url,a['href']).split('#')[0]
        label=clean(a.get_text(' ',strip=True))
        path=urlparse(href).path.lower()
        # Require a job/requisition-shaped URL. This deliberately rejects /construction/expertise/preconstruction.
        job_path=(re.search(r'/(?:jobs?|careers)/(?:[^/?#]+/)*[^/?#]+',path) and
                  (re.search(r'\d{4,}',path) or re.search(r'(?:req|jr|job|requisition)[-_]?\d+',path,re.I)))
        # Some verified portals use /jobs/<slug> without numeric IDs. Only accept when anchor text itself looks like a target role.
        slug_job=('/jobs/' in path and label and any(k in (' '+label.lower()+' ') for k in DIRECT_ROLES+CONTEXT_ROLES))
        if job_path or slug_job:
            candidates.append((href,label))
    for href,label in list(dict.fromkeys(candidates))[:350]:
        try:
            d=SESSION.get(href,timeout=15,allow_redirects=True)
            if not d.ok: continue
            n=jsonld_jobs(d.url,d.text,company)
            if n:
                found+=n; continue
            ds=BeautifulSoup(d.text,'html.parser')
            text=clean(ds.get_text(' ',strip=True))
            low=text.lower()
            # Strong evidence that this is a real vacancy, not a service/marketing page.
            evidence=sum(x in low for x in ['apply now','apply for this job','job description','job id','requisition','employment type','responsibilities','qualifications'])
            if evidence < 2: continue
            h=ds.find('h1') or ds.find('h2')
            title=clean(h.get_text(' ',strip=True) if h else label)
            if not title: title=label
            loc=''
            lm=re.search(r'(?:location|job location|primary location)\s*:?\s*([A-Za-z .-]+,\s*[A-Z]{2})(?:\b|\s)',text,re.I)
            if lm: loc=lm.group(1)
            add(company,title,loc,d.url,'N/A',text)
            found+=1
        except Exception:
            pass
    if found or candidates:
        return True
    raise RuntimeError('no verified job-detail records discovered')


def eightfold(url,company):
    """Eightfold public careers adapter. Tries the two public search shapes observed on live Eightfold sites."""
    p=urlparse(url); base=f'{p.scheme}://{p.netloc}'; domain=p.netloc.lower().removeprefix('careers.').removeprefix('www.')
    headers={'Referer':url,'Origin':base,'Accept':'application/json, text/plain, */*'}
    payloads=[]
    # Common Eightfold apply API.
    try:
        r=SESSION.get(base+'/api/apply/v2/jobs',params={'domain':domain,'start':0,'num':100,'sort_by':'hot'},headers=headers,timeout=25)
        if r.ok:
            data=r.json(); payloads.extend(data.get('positions') or data.get('jobs') or data.get('data') or [])
    except Exception: pass
    # Newer PCS search API used by some tenants.
    if not payloads:
        try:
            r=SESSION.get(base+'/api/pcsx/search',params={'domain':domain,'start':0,'num':100,'sort_by':'hot'},headers=headers,timeout=25)
            if r.ok:
                data=r.json(); payloads.extend(data.get('positions') or data.get('jobs') or data.get('data') or [])
        except Exception: pass
    if not payloads: raise RuntimeError('Eightfold public search returned no job records')
    for j in payloads:
        if not isinstance(j,dict): continue
        title=j.get('name') or j.get('title') or j.get('position_name') or ''
        loc=j.get('location') or j.get('locations') or j.get('location_name') or ''
        if isinstance(loc,list): loc='; '.join(clean(x.get('name') if isinstance(x,dict) else x) for x in loc)
        if isinstance(loc,dict): loc=loc.get('name') or ', '.join(str(loc.get(k,'')) for k in ('city','state','country') if loc.get(k))
        pid=j.get('id') or j.get('pid') or j.get('position_id')
        link=j.get('url') or j.get('job_url') or (f'{base}/careers?pid={pid}' if pid else '')
        desc=j.get('description') or j.get('job_description') or j.get('description_text') or ''
        add(company,title,loc,link,j.get('posted_date') or j.get('datePosted') or 'N/A',desc)
    return True


def nlx_jobsyn(url,company):
    """NLX/jobsyn adapter. Uses browser-like headers, small pages and retry/backoff.
    Some NLX tenants block datacenter IPs; those remain FAILED rather than bypassing controls.
    """
    base=f'{urlparse(url).scheme}://{urlparse(url).netloc}'
    headers={'Referer':url,'Origin':base,'Accept':'application/json, text/plain, */*','Sec-Fetch-Site':'cross-site'}
    discovered=0
    for page in range(1,81):
        r=None
        for attempt in range(3):
            try:
                r=SESSION.get('https://prod-search-api.jobsyn.org/api/v1/solr/search',params={'page':page,'num_items':15},headers=headers,timeout=30)
                if r.status_code in (502,503,504): time.sleep(2*(attempt+1)); continue
                break
            except requests.RequestException:
                time.sleep(2*(attempt+1))
        if r is None: raise RuntimeError('NLX/jobsyn request failed')
        if r.status_code in (401,403): raise RuntimeError(f'NLX/jobsyn blocked ({r.status_code})')
        r.raise_for_status(); data=r.json()
        posts=data.get('jobs') or data.get('results') or data.get('response',{}).get('docs') or data.get('data') or []
        if isinstance(posts,dict): posts=posts.get('jobs') or posts.get('results') or []
        if not posts: break
        for j in posts:
            if not isinstance(j,dict): continue
            link=j.get('url') or j.get('job_url') or j.get('apply_url') or j.get('seo_url') or ''
            cname=clean(j.get('company') or j.get('company_name') or j.get('employer') or '')
            host=urlparse(link).netloc.lower() if link else ''
            wanted=urlparse(url).netloc.lower()
            if host and host!=wanted and cname and clean(company).split(',')[0].lower() not in cname.lower(): continue
            title=j.get('title') or j.get('job_title') or j.get('name') or ''
            loc=j.get('location') or j.get('formatted_location') or j.get('city_state') or ''
            desc=j.get('description') or j.get('job_description') or j.get('snippet') or ''
            if link: discovered+=1; add(company,title,loc,link,j.get('date_posted') or j.get('posted') or 'N/A',desc)
        if len(posts)<15: break
    if not discovered: raise RuntimeError('NLX/jobsyn returned no verified records for company')
    return True


def oracle_hcm(url,company):
    """Oracle Recruiting Cloud Candidate Experience adapter."""
    p=urlparse(url); base=f'{p.scheme}://{p.netloc}'
    m=re.search(r'/sites/([^/]+)/jobs',p.path,re.I); site=(m.group(1) if m else 'CX')
    api=base+'/hcmRestApi/resources/latest/recruitingCEJobRequisitions'
    headers={'Referer':url,'Origin':base,'Accept':'application/json'}
    offset=0; discovered=0
    while offset<2000:
        params={'finder':f'findReqs;siteNumber={site}','limit':100,'offset':offset,'onlyData':'true'}
        r=SESSION.get(api,params=params,headers=headers,timeout=25)
        if not r.ok: raise RuntimeError(f'Oracle HCM {r.status_code} at {api}')
        data=r.json(); items=data.get('items') or []
        if not items: break
        for j in items:
            title=j.get('Title') or j.get('title') or j.get('JobTitle') or ''
            loc=j.get('PrimaryLocation') or j.get('primaryLocation') or j.get('Location') or ''
            rid=j.get('Id') or j.get('id') or j.get('RequisitionId') or j.get('requisitionId') or j.get('RequisitionNumber')
            link=j.get('ExternalURL') or j.get('externalURL') or (url.rstrip('/')+f'/{rid}' if rid else '')
            desc=j.get('ExternalDescriptionStr') or j.get('externalDescriptionStr') or j.get('Description') or ''
            if link: discovered+=1; add(company,title,loc,link,j.get('PostedDate') or j.get('postedDate') or 'N/A',desc)
        if not data.get('hasMore'): break
        offset+=len(items)
    if not discovered: raise RuntimeError('Oracle HCM returned no job records')
    return True


def dayforce(url,company):
    """Dayforce public job-board adapter."""
    p=urlparse(url); base=f'{p.scheme}://{p.netloc}'
    ns='balfourbeatty' if 'balfour' in company.lower() else ''
    board='CANDIDATEPORTALBUILDINGCIVILS' if 'balfour' in company.lower() else ''
    if not ns or not board: raise RuntimeError('Dayforce namespace/jobBoardCode not configured')
    api=f'{base}/api/geo/{ns}/jobposting/search'; start=0; discovered=0
    headers={'Referer':url,'Origin':base,'Accept':'application/json','Content-Type':'application/json'}
    while start<2000:
        body={'clientNamespace':ns,'jobBoardCode':board,'cultureCode':'en-US','distanceUnit':0,'paginationStart':start}
        r=SESSION.post(api,json=body,headers=headers,timeout=25); r.raise_for_status(); data=r.json()
        posts=data.get('Items') or data.get('items') or data.get('JobPostings') or data.get('jobPostings') or []
        if not posts: break
        for j in posts:
            title=j.get('Title') or j.get('title') or ''
            loc=j.get('Location') or j.get('location') or j.get('LocationDescription') or ''
            jid=j.get('JobPostingId') or j.get('jobPostingId') or j.get('Id') or j.get('id')
            link=j.get('Url') or j.get('url') or (f'{base}/{ns}/CandidatePortal/en-US/{board}/Posting/View/{jid}' if jid else '')
            desc=j.get('Description') or j.get('description') or ''
            if link: discovered+=1; add(company,title,loc,link,j.get('PostedDate') or 'N/A',desc)
        start+=len(posts)
        if len(posts)<20: break
    if not discovered: raise RuntimeError('Dayforce returned no job records')
    return True

def jibe_careers(url,company):
    """Safe adapter for Jibe-style careers sites (used by several large contractors).
    Enumerates only links under /jobs/ that resolve to pages with job evidence.
    """
    base=f'{urlparse(url).scheme}://{urlparse(url).netloc}'
    queue=[url.rstrip('/'), base+'/jobs', base+'/jobs/']
    seen_pages=set(); job_links=[]
    for page in queue:
        if page in seen_pages: continue
        seen_pages.add(page)
        try:
            r=SESSION.get(page,timeout=25,allow_redirects=True); r.raise_for_status()
        except Exception:
            continue
        soup=BeautifulSoup(r.text,'html.parser')
        for a in soup.find_all('a',href=True):
            u=urljoin(r.url,a['href']).split('#')[0]
            if urlparse(u).netloc.lower()!=urlparse(base).netloc.lower(): continue
            path=urlparse(u).path.lower().rstrip('/')
            # Job detail pages, not categories/locations/marketing pages.
            if re.search(r'/jobs/(?:[^/]+/)*\d{3,}(?:/[^/]+)?$',path) or re.search(r'/jobs/[^/]+-[a-z0-9_-]*\d{3,}$',path):
                job_links.append(u)
    discovered=0
    for u in list(dict.fromkeys(job_links))[:500]:
        try:
            r=SESSION.get(u,timeout=15,allow_redirects=True)
            if not r.ok: continue
            n=jsonld_jobs(r.url,r.text,company)
            if n: discovered+=n; continue
            soup=BeautifulSoup(r.text,'html.parser'); text=clean(soup.get_text(' ',strip=True))
            # Require strong job-page evidence before accepting HTML fallback.
            if not re.search(r'\b(apply(?: now)?|job id|requisition|job category|position type)\b',text,re.I): continue
            h=soup.find('h1') or soup.find('h2'); title=clean(h.get_text(' ',strip=True) if h else '')
            loc=''; lm=re.search(r'(?:Location|locations?)\s*:?\s*([A-Za-z .-]+,\s*[A-Z]{2})',text,re.I)
            if lm: loc=lm.group(1)
            if title:
                discovered+=1; add(company,title,loc,r.url,'N/A',text)
        except Exception: pass
    if not job_links: raise RuntimeError('no verified Jibe job-detail links discovered')
    return True


def csod(url,company):
    """Cornerstone/CSOD public career-site adapter.
    Uses public rendered requisition links; does not attempt to bypass session controls.
    """
    r=SESSION.get(url,timeout=25,allow_redirects=True); r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser'); links=[]
    for a in soup.find_all('a',href=True):
        u=urljoin(r.url,a['href']).split('#')[0]
        if re.search(r'/requisition/\d+',u,re.I): links.append(u)
    discovered=0
    for u in list(dict.fromkeys(links))[:400]:
        try:
            d=SESSION.get(u,timeout=15,allow_redirects=True)
            if not d.ok: continue
            n=jsonld_jobs(d.url,d.text,company)
            if n: discovered+=n; continue
            ds=BeautifulSoup(d.text,'html.parser'); text=clean(ds.get_text(' ',strip=True))
            if not re.search(r'\b(apply|requisition|job location|job details)\b',text,re.I): continue
            h=ds.find('h1') or ds.find('h2'); title=clean(h.get_text(' ',strip=True) if h else '')
            lm=re.search(r'(?:Location|Job Location)\s*:?\s*([A-Za-z .-]+,\s*[A-Z]{2})',text,re.I); loc=lm.group(1) if lm else ''
            if title: discovered+=1; add(company,title,loc,d.url,'N/A',text)
        except Exception: pass
    if not links: raise RuntimeError('no public CSOD requisition links discovered')
    return True

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
        return {'greenhouse':greenhouse,'lever':lever,'ashby':ashby,'workday':workday,'smartrecruiters':smartrecruiters,'successfactors':successfactors}[plat](ats,company)
    n=crawl_search_page(r.url,company)
    if n: return True
    raise RuntimeError('no supported ATS or structured JobPosting data discovered')

def scrape(row):
    company=str(row.company).strip(); url=str(row.careers_url).strip(); platform=str(row.platform).strip().lower()
    before=len(results)
    try:
        fn={'greenhouse':greenhouse,'lever':lever,'ashby':ashby,'workday':workday,'smartrecruiters':smartrecruiters,'successfactors':successfactors,'phenom':phenom,'kiewit':kiewit,'dpr':dpr,'verified_listing':verified_listing,'eightfold':eightfold,'nlx':nlx_jobsyn,'jobsyn':nlx_jobsyn,'oracle':oracle_hcm,'oracle_hcm':oracle_hcm,'dayforce':dayforce,'jibe':jibe_careers,'icims_jibe':jibe_careers,'csod':csod,'generic':generic,'auto':generic}.get(platform,generic)
        fn(url,company)
        source_health.append({'company':company,'platform':platform,'status':'WORKING','matches':max(0,len(results)-before),'detail':''})
    except Exception as e:
        msg=str(e)[:220]; log(company,msg)
        source_health.append({'company':company,'platform':platform,'status':'FAILED','matches':0,'detail':msg})

def write_health_report():
    if not source_health: return
    h=pd.DataFrame(source_health)
    # A company can have duplicate source rows. Count it working if at least one source succeeded.
    rows=[]
    for company,g in h.groupby('company',sort=True):
        ok=(g.status=='WORKING').any(); matches=int(g.matches.sum())
        failed=g[g.status=='FAILED']
        detail='; '.join(failed.detail.dropna().astype(str).unique()[:3]) if not ok else ''
        rows.append({'company':company,'status':'WORKING' if ok else 'FAILED','matches':matches,'detail':detail})
    c=pd.DataFrame(rows)
    total=len(c); working=int((c.status=='WORKING').sum()); failed=total-working
    with_matches=int(((c.status=='WORKING') & (c.matches>0)).sum()); zero=working-with_matches
    rate=(100.0*working/total) if total else 0
    print('\n========== SOURCE HEALTH ==========')
    print(f'Total unique companies:            {total}')
    print(f'Successfully queried:              {working}')
    print(f'  With matching construction jobs: {with_matches}')
    print(f'  Working but 0 new matches:       {zero}')
    print(f'Failed / unsupported:              {failed}')
    print(f'Source success rate:               {rate:.1f}%')
    print('===================================')
    c.to_csv('source_health.csv',index=False)
    failed_df=c[c.status=='FAILED'][['company','detail']]
    if len(failed_df):
        print('\nFAILED COMPANIES (first 40):')
        for r in failed_df.head(40).itertuples(index=False): print(f'[FAIL] {r.company}: {r.detail}')


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
    write_health_report()
    if errors:
        print(f'\n{len(errors)} source warnings (first 30):'); print('\n'.join(errors[:30]))
