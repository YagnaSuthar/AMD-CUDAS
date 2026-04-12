import os

def resolve_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        resolved_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("<<<<<<< HEAD"):
                i += 1
                # Skip HEAD lines until =======
                while i < len(lines) and not lines[i].strip().startswith("======="):
                    i += 1
                # Skip the ======= 
                if i < len(lines):
                    i += 1
                # Keep incoming lines until >>>>>>>
                while i < len(lines) and not lines[i].strip().startswith(">>>>>>>"):
                    resolved_lines.append(lines[i])
                    i += 1
                # Skip the >>>>>>> marker itself
                if i < len(lines):
                    i += 1
            else:
                resolved_lines.append(line)
                i += 1

        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(resolved_lines)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

# Scan entire project
project_dir = r"c:\Users\rlintern67\Desktop\CUDAS\AMD-CUDAS"
count = 0
for root, dirs, files in os.walk(project_dir):
    # Skip irrelevant directories
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', 'venv', 'env', '__pycache__', '.next')]
    for fl in files:
        if fl.endswith((".py", ".jsx", ".js", ".css", ".html", ".json", ".md")):
            filepath = os.path.join(root, fl)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if "<<<<<<< HEAD" in content:
                    print(f"Resolving: {os.path.relpath(filepath, project_dir)}")
                    resolve_file(filepath)
                    count += 1
            except Exception:
                pass

print(f"\nDone! Resolved {count} files.")
