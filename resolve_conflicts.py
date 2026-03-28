import os
import glob

def resolve_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    resolved_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("<<<<<<< HEAD"):
            # skip the marker
            i += 1
            # keep adding lines until =======
            while i < len(lines) and not lines[i].startswith("======="):
                resolved_lines.append(lines[i])
                i += 1
            
            # now we are at =======
            # skip until >>>>>>>
            while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                i += 1
            # now we are at >>>>>>>
            # skip the marker
            i += 1
        else:
            resolved_lines.append(line)
            i += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(resolved_lines)

agent_dir = r"d:\AMD-CUDAS\AMD-CUDAS\backend\app\agents"
for root, dirs, files in os.walk(agent_dir):
    for fl in files:
        if fl.endswith(".py"):
            filepath = os.path.join(root, fl)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if "<<<<<<< HEAD" in content:
                print(f"Resolving conflicts in {filepath}")
                resolve_file(filepath)
