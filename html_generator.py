import os
import json

def generate_git_tree_html(commits, git_url, output_path="git_tree.html"):
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Git Tree Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/@gitgraph/js"></script>
    <style>
        body {{
            font-family: 'Consolas', 'Microsoft YaHei', 'Source Han Sans SC', sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
        }}
        #graph-container {{
            background: #ffffff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: auto;
            min-height: 1200px;
        }}
        h1 {{ 
            color: #2c3e50; 
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.2em;
            font-weight: 300;
        }}
    </style>
</head>
<body>
    <h1>Git Repository History - {git_url}</h1>
    <div id="graph-container"></div>

    <script>
        const commitsData = {json.dumps(commits)};
        const container = document.getElementById("graph-container");
        const gitgraph = GitgraphJS.createGitgraph(container, {{
            orientation: "vertical-reverse",
            template: GitgraphJS.templateExtend("metro", {{
                colors: ["#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4", "#FF5722", "#607D8B", "#8BC34A", "#FFC107"],
                branch: {{
                    lineWidth: 4,
                    spacing: 40,
                }},
                commit: {{
                    spacing: 45,
                    dot: {{
                        size: 10,
                        strokeWidth: 2,
                    }},
                    message: {{
                        displayHash: true,
                        displayAuthor: true,
                        font: "normal 10pt 'Consolas', 'Microsoft YaHei', 'Source Han Sans SC', sans-serif",
                    }},
                }},
            }})
        }});

        const branches = {{}};
        const commitToBranch = {{}};
        const branchToLastCommit = new Map();

        const main = gitgraph.branch({{
            name: "main",
            style: {{ label: {{ display: true }} }}
        }});
        branches["main"] = main;
        branchToLastCommit.set(main, null);

        commitsData.forEach(c => {{
            let targetBranch;
            const firstParentHash = c.parents.length > 0 ? c.parents[0] : null;
            
            if (!firstParentHash) {{
                targetBranch = branches["main"];
            }} else {{
                let parentBranch = commitToBranch[firstParentHash] || branches["main"];
                
                if (branchToLastCommit.get(parentBranch) === firstParentHash) {{
                    targetBranch = parentBranch;
                }} else {{
                    targetBranch = parentBranch.branch({{
                        name: `diverge-${{c.hash}}`,
                        style: {{ label: {{ display: false }} }}
                    }});
                }}
            }}

            c.refs.forEach(ref => {{
                if (ref.startsWith('refs/heads/') || (ref.startsWith('origin/') && !ref.includes('HEAD'))) {{
                    const bName = ref.replace('refs/heads/', '').replace('origin/', '');
                    if (!branches[bName]) {{
                        branches[bName] = targetBranch.branch({{
                            name: bName,
                            style: {{ label: {{ display: true }} }}
                        }});
                    }}
                    targetBranch = branches[bName];
                }}
            }});

            const commitOptions = {{
                hash: c.hash,
                subject: c.message,
                author: `${{c.author}} <${{c.date}}>`
            }};

            if (c.parents.length > 1) {{
                let mergedSomething = false;
                for (let i = 1; i < c.parents.length; i++) {{
                    const otherBranch = commitToBranch[c.parents[i]];
                    if (otherBranch && otherBranch !== targetBranch) {{
                        targetBranch.merge({{
                            branch: otherBranch,
                            commitOptions: commitOptions
                        }});
                        mergedSomething = true;
                        break; 
                    }}
                }}

                if (mergedSomething) {{
                    commitToBranch[c.hashFull] = targetBranch;
                    branchToLastCommit.set(targetBranch, c.hashFull);
                    return;
                }}
            }}

            targetBranch.commit(commitOptions);
            commitToBranch[c.hashFull] = targetBranch;
            branchToLastCommit.set(targetBranch, c.hashFull);
        }});
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML generated: {os.path.abspath(output_path)}")
