"""List the files read by the pipeline (from a discovery log) that are NOT tracked by git. Usage: python scripts/untracked_reads.py LOG"""
import collections, subprocess, sys
reads = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith('GLOB')]
tracked = set(subprocess.run(['git', 'ls-files'], capture_output=True, text=True).stdout.split('\n'))
unt = [r for r in reads if r not in tracked]
c = collections.Counter('/'.join(r.split('/')[:3]) for r in unt)
print(len(reads), 'files read;', len(unt), 'untracked'); print(dict(c))
for r in unt:
    if not r.startswith('data/raw/gamelogs'): print(' ', r)
