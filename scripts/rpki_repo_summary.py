"""
Compute summary statistics on a download of RPKI data.
In kartograf, this folder is under `data/{UNIX_TS}/rpki`.
This folder must be passed as the argument to this script.
"""

from argparse import ArgumentParser
from pathlib import Path
from collections import defaultdict

def count_rpki_files(path: Path) -> dict:
    file_counts = defaultdict(int)
    # Walk through all files in the directory
    for file in path.rglob('*'):
        if file.suffix in ['.roa', '.mft', '.crl', '.cer']:
            file_counts[file.suffix[1:]] += 1
    return file_counts

def analyze_rpki_repos(base_path: Path) -> dict:
    cache_path = base_path / "rpki" / "cache"
    results = {}

    for repo in cache_path.iterdir():
        if repo.is_dir() and repo.name != "ta":
            results[repo.name] = count_rpki_files(repo)

    return results

def main():
    parser = ArgumentParser(description='Analyze RPKI repositories and count file types.')
    parser.add_argument('base_path', help='Base path containing the RPKI data (e.g., "data/1742505040")')
    args = parser.parse_args()

    full_path = Path.cwd() / args.base_path
    results = analyze_rpki_repos(full_path)

    print("\nRPKI Repository Analysis:")
    print("-" * 60)
    print(f"{'Repository':<40} {'CER':>5} {'ROA':>5} {'MFT':>5} {'CRL':>5}")
    print("-" * 60)

    sorted_repos = sorted(results.items(), key=lambda x: x[1]['roa'], reverse=True)
    for repo, counts in sorted_repos:
        print(f"{repo:<40} {counts['cer']:>5} {counts['roa']:>5} {counts['mft']:>5} {counts['crl']:>5}")

if __name__ == "__main__":
    main()
