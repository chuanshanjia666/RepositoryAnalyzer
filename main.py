import os
import json
import git
from datetime import datetime
from html_generator import generate_git_tree_html

GIT_URL = "https://github.com/Neutree/COMTool.git"
REPO_PATH = "./repo"

def clone_repo(url, path):
    if not os.path.exists(path):
        print(f"Cloning {url} to {path}...")
        git.Repo.clone_from(url, path)
    else:
        print(f"Repo already exists at {path}")
    return git.Repo(path)

def get_git_history(repo, limit=100):
    commits = []
    for commit in repo.iter_commits('--all', max_count=limit, topo_order=True):
        commits.append({
            "hash": commit.hexsha[:7],
            "hashFull": commit.hexsha,
            "author": commit.author.name,
            "date": datetime.fromtimestamp(commit.authored_date).strftime('%Y-%m-%d %H:%M'),
            "message": commit.message.strip().split('\n')[0],
            "parents": [p.hexsha for p in commit.parents],
            "refs": [ref.name for ref in repo.refs if hasattr(ref, 'commit') and ref.commit == commit]
        })
    return commits[::-1]

if __name__ == "__main__":
    repo = clone_repo(GIT_URL, REPO_PATH)
    commits = get_git_history(repo, 300)
    generate_git_tree_html(commits, GIT_URL)
