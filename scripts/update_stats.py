"""Generate a local SVG from publicly visible, non-fork GitHub repositories."""
import os, json, urllib.request, collections, datetime
from html import escape
from pathlib import Path

USER = 'juannunes544costaa-cmd'
OUT = Path(__file__).resolve().parents[1] / 'assets' / 'telemetry.svg'

def fetch_repos():
    repos = []
    for page in range(1, 1001):
        url = f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}'
        # Intentionally unauthenticated: this endpoint only returns public data.
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'jarvis-profile-telemetry', 'X-GitHub-Api-Version': '2022-11-28'})
        with urllib.request.urlopen(req, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('Unexpected GitHub response')
        repos.extend(r for r in batch if not r.get('private') and not r.get('fork'))
        if len(batch) < 100:
            return repos
    raise RuntimeError('Pagination limit reached')

def render(repos=None):
    available = repos is not None
    repos = repos or []
    values = [len(repos), sum(r.get('stargazers_count', 0) for r in repos), sum(r.get('forks_count', 0) for r in repos)]
    langs = collections.Counter(r['language'] for r in repos if r.get('language'))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y %H:%M UTC') if available else 'Aguardando primeira execução'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 285" role="img" aria-label="Telemetria pública do GitHub">','<rect x="1" y="1" width="898" height="283" rx="14" fill="#091724" stroke="#2185a4"/>','<g font-family="monospace">','<text x="28" y="36" fill="#46dcf4" font-size="16" letter-spacing="2">// PUBLIC TELEMETRY</text>']
    for i, (label, value) in enumerate(zip(['REPOSITÓRIOS','ESTRELAS','FORKS RECEBIDOS'], values)):
        x = 28 + i*286
        parts += [f'<rect x="{x}" y="53" width="272" height="88" rx="7" fill="#10283a" stroke="#23546a"/>', f'<text x="{x+15}" y="76" fill="#9bc3d2" font-size="12">{label}</text>',f'<text x="{x+15}" y="120" fill="#e7fbff" font-size="37" font-weight="bold">{value if available else "—"}</text>']
    parts += ['<text x="28" y="169" fill="#46dcf4" font-size="14">LINGUAGEM PRINCIPAL / POR REPOSITÓRIO</text>']
    if langs:
        total = sum(langs.values()); top = langs.most_common(4); other = total - sum(n for _, n in top)
        if other: top.append(('Outras',other))
        x=28
        colors=['#46dcf4','#518ef8','#58c7a0','#b89cf8','#8ca0b1']
        for i,(lang,n) in enumerate(top):
            w=844*n/total
            parts.append(f'<rect x="{x:.2f}" y="185" width="{w:.2f}" height="13" fill="{colors[i]}"/>'); x+=w
        for i,(lang,n) in enumerate(top):
            x=28+i*169
            parts += [f'<circle cx="{x+5}" cy="221" r="4" fill="{colors[i]}"/>',f'<text x="{x+15}" y="225" font-size="12" fill="#c6dce5">{escape(lang[:17])} {n}</text>']
    else:
        parts.append('<text x="28" y="205" font-size="13" fill="#9bc3d2">Sem dados de linguagem disponíveis.</text>')
    parts += [f'<text x="28" y="260" font-size="12" fill="#9bc3d2">{escape(stamp)}</text>','<text x="872" y="260" font-size="12" text-anchor="end" fill="#46dcf4">GITHUB / PUBLIC DATA</text>','</g></svg>']
    return '\n'.join(parts)+'\n'


PROFILE = USER + '/' + USER
ROOT = OUT.parent
DAYS = 28

def public_projects(repos):
    return [r for r in repos if r.get('private') is False and not r.get('fork') and r.get('owner', {}).get('login') == USER]

def fetch_events():
    events = []
    for page in range(1, 4):
        url = f'https://api.github.com/users/{USER}/events/public?per_page=100&page={page}'
        req = urllib.request.Request(url, headers={'Accept':'application/vnd.github+json','User-Agent':'jarvis-public-activity','X-GitHub-Api-Version':'2022-11-28'})
        with urllib.request.urlopen(req, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('Unexpected public events response')
        events.extend(batch)
        if len(batch) < 100:
            break
    return events

def activity_data(repos, events, today):
    allowed = {r['full_name'] for r in public_projects(repos) if r['full_name'] != PROFILE}
    days = [today - datetime.timedelta(days=i) for i in range(DAYS-1,-1,-1)]
    counts = {d:0 for d in days}
    kinds = collections.Counter()
    seen = set()
    for event in events:
        if event.get('public') is not True or event.get('actor',{}).get('login') != USER or event.get('repo',{}).get('name') not in allowed:
            continue
        eid = event.get('id')
        if not eid or eid in seen:
            continue
        try:
            date = datetime.date.fromisoformat(event['created_at'][:10])
        except (ValueError, KeyError, TypeError):
            continue
        if date not in counts:
            continue
        seen.add(eid)
        counts[date] += 1
        kinds[event.get('type','Other')] += 1
    return counts, kinds

def base_svg(height, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 {height}" role="img" aria-label="{escape(title, quote=True)}">',f'<rect x="1" y="1" width="898" height="{height-2}" rx="14" fill="#091724" stroke="#2185a4"/>','<g font-family="monospace">']

def txt(x,y,value,size=15,color='#c6dce5'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(str(value))}</text>'

def radar(repos, today):
    projects = [r for r in public_projects(repos) if r['full_name'] != PROFILE]
    projects.sort(key=lambda r:r.get('pushed_at') or '',reverse=True)
    active = 0
    for r in projects:
        try:
            delta = (today-datetime.date.fromisoformat(r['pushed_at'][:10])).days
            active += int(0 <= delta < 30)
        except (KeyError, TypeError, ValueError):
            pass
    visible = projects[:6]
    height = 112 + max(1,len(visible))*68
    parts = base_svg(height,'Radar de projetos públicos')
    parts += [txt(28,34,'// PROJECT RADAR',18,'#46dcf4'),txt(28,61,f'{len(projects)} projetos públicos • {active} com push nos últimos 30 dias',15)]
    if not visible:
        parts.append(txt(28,100,'Nenhum projeto público elegível.'))
    for i,r in enumerate(visible):
        y=75+i*68
        parts += [f'<rect x="28" y="{y}" width="844" height="58" rx="6" fill="#10283a" stroke="#23546a"/>',txt(43,y+22,r['name'][:55],17,'#e7fbff'),txt(43,y+44,f"{r.get('language') or 'Sem linguagem'} | push: {(r.get('pushed_at') or 'N/D')[:10]} | estrelas: {r.get('stargazers_count',0)}",13)]
    parts += [txt(28,height-14,'Ordenado por último push • até 6 projetos • perfil excluído',12,'#79cde1'),'</g></svg>']
    return '\n'.join(parts)+'\n'

def activity(repos, events, today):
    counts,kinds=activity_data(repos,events,today)
    parts=base_svg(285,'Atividade pública observada nos últimos 28 dias')
    parts += [txt(28,34,'// ACTIVITY MATRIX / 28D',18,'#46dcf4')]
    for i,(label,n) in enumerate([('EVENTOS',sum(counts.values())),('PUSH EVENTS',kinds['PushEvent']),('PR EVENTS',kinds['PullRequestEvent']),('DIAS ATIVOS',sum(v>0 for v in counts.values()))]):
        x=28+i*214
        parts += [f'<rect x="{x}" y="49" width="202" height="62" rx="6" fill="#10283a" stroke="#23546a"/>',txt(x+12,68,label,12,'#79cde1'),txt(x+12,98,n,25,'#e7fbff')]
    for i,(day,n) in enumerate(counts.items()):
        x=28+i*30
        color='#163145' if n==0 else '#176c83' if n==1 else '#20a9c5' if n<4 else '#46dcf4'
        parts.append(f'<rect x="{x}" y="142" width="25" height="36" rx="3" fill="{color}"><title>{day}: {n} eventos observados</title></rect>')
    parts += ['<rect x="28" y="138" width="25" height="44" rx="4" fill="none" stroke="#e7fbff" stroke-width="1.4" opacity=".8"><animate attributeName="x" values="28;838;28" dur="8s" repeatCount="indefinite"/></rect>',txt(28,199,next(iter(counts)).isoformat(),12),txt(745,199,today.isoformat(),12),txt(28,228,'Matriz: um quadrado por dia • intensidade = eventos observados',13,'#79cde1'),txt(28,250,'Amostra de até 300 eventos públicos recentes; não equivale a commits/contribuições.',12),txt(28,269,'Somente eventos do titular em projetos públicos próprios; perfil excluído.',12),'</g></svg>']
    return '\n'.join(parts)+'\n'

def main():
    repos=public_projects(fetch_repos())
    events=fetch_events()
    today=datetime.datetime.now(datetime.timezone.utc).date()
    outputs={OUT:render(repos),ROOT/'radar.svg':radar(repos,today),ROOT/'activity.svg':activity(repos,events,today)}
    # Generate everything before modifying the published files.
    import xml.etree.ElementTree as ET
    for content in outputs.values():
        ET.fromstring(content)
    for path,content in outputs.items():
        path.write_text(content,encoding='utf-8')

if __name__ == '__main__':
    main()
