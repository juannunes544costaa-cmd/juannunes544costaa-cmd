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

if __name__ == '__main__':
    OUT.write_text(render(fetch_repos()), encoding='utf-8')
