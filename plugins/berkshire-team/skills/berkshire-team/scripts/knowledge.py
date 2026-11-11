"""Local source registry and literal text search; no uploads or model training."""
import argparse
import hashlib
import json
from pathlib import Path
from research_run import save

SUPPORTED = {'.txt', '.md', '.pdf', '.epub', '.docx'}
TEXT = {'.txt', '.md'}
RECORDINGS = {'.wav', '.mp3', '.m4a', '.mp4', '.flac', '.ogg', '.opus', '.webm'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_library(library):
    path = Path(library) / 'manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'materials': []}


def register(library, file, title, kind, text_file=None, url=None):
    source = Path(file).resolve()
    formats = SUPPORTED | RECORDINGS if kind in {'audio', 'video'} else SUPPORTED
    if source.suffix.lower() not in formats or not source.is_file():
        raise ValueError('supply an existing supported document, or a recording with kind audio/video')
    text_path = Path(text_file).resolve() if text_file else source if source.suffix.lower() in TEXT else None
    if text_path and (text_path.suffix.lower() not in TEXT or not text_path.is_file()):
        raise ValueError('extracted text must be an existing UTF-8 TXT/MD file')
    if text_path:
        text_path.read_text(encoding='utf-8')  # validate encoding before mutation
    data = read_library(library)
    source_hash = sha(source)
    identifier = 'material-' + hashlib.sha256(str(source).encode()).hexdigest()[:16]
    prior = next((x for x in data['materials'] if x['id'] == identifier), None)
    row = {'id': identifier, 'title': title, 'kind': kind, 'source_path': str(source),
           'source_sha256': source_hash, 'source_url': url, 'text_path': str(text_path) if text_path else None,
           'text_sha256': sha(text_path) if text_path else None,
           'state': 'indexed' if text_path else 'registered', 'reviewed_sections': []}
    if prior and all(prior.get(k) == row.get(k) for k in ('source_sha256', 'text_path', 'text_sha256')):
        row['reviewed_sections'] = prior.get('reviewed_sections', [])
    data['materials'] = [x for x in data['materials'] if x['id'] != identifier] + [row]
    Path(library).mkdir(parents=True, exist_ok=True)
    save(Path(library) / 'manifest.json', data)
    return row


def integrity(row):
    for path_key, hash_key in [('source_path', 'source_sha256'), ('text_path', 'text_sha256')]:
        if row.get(path_key):
            path = Path(row[path_key])
            if not path.is_file() or sha(path) != row[hash_key]:
                return False
    return True


def search(library, query, limit=8):
    if not query.strip() or not 1 <= limit <= 30:
        raise ValueError('nonempty query and limit 1..30 required')
    matches, unavailable = [], []
    terms = [x.casefold() for x in query.split()]
    for row in read_library(library)['materials']:
        if not integrity(row):
            unavailable.append({'id': row['id'], 'reason': 'source changed/missing; re-register and review again'})
            continue
        if not row.get('text_path'):
            unavailable.append({'id': row['id'], 'reason': 'registered only; no searchable text'})
            continue
        for line, content in enumerate(Path(row['text_path']).read_text(encoding='utf-8').splitlines(), 1):
            if all(term in content.casefold() for term in terms):
                matches.append({'id': row['id'], 'title': row['title'], 'text_path': row['text_path'],
                                'line': line, 'excerpt': content[:800], 'state': row['state'],
                                'reviewed_sections': row['reviewed_sections']})
                if len(matches) >= limit:
                    return {'matches': matches, 'unavailable': unavailable, 'truncated': True}
    return {'matches': matches, 'unavailable': unavailable, 'truncated': False}


def review(library, identifier, locator, note):
    if not locator.strip() or not note.strip():
        raise ValueError('review requires actual section locator and reading note')
    data = read_library(library)
    row = next((r for r in data['materials'] if r['id'] == identifier), None)
    if row is None or not integrity(row):
        raise ValueError('unknown material or content changed; register again')
    row['reviewed_sections'].append({'locator': locator, 'note': note})
    # Reviewed sections are not a claim of having read the entire book.
    save(Path(library) / 'manifest.json', data)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    for key in ('file', 'title', 'kind'):
        add.add_argument('--' + key, required=True)
    add.add_argument('--text-file')
    add.add_argument('--url')
    commands.add_parser('list')
    find = commands.add_parser('search')
    find.add_argument('--query', required=True)
    find.add_argument('--limit', type=int, default=8)
    mark = commands.add_parser('review')
    for key in ('id', 'locator', 'note'):
        mark.add_argument('--' + key, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'add':
            result = register(args.library, args.file, args.title, args.kind, args.text_file, args.url)
        elif args.command == 'search':
            result = search(args.library, args.query, args.limit)
        elif args.command == 'review':
            result = review(args.library, args.id, args.locator, args.note)
        else:
            result = read_library(args.library)
            for row in result['materials']:
                row['integrity_ok'] = integrity(row)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
