"""
Repository Folder-Tree Analyzer.

Pure, deterministic analysis of a GitHub repository's file tree (as returned by
the Git Trees API). It classifies every file, detects the project type and
layout, verifies the claimed tech stack against real evidence (file types,
marker files and dependency manifests), flags red flags (vendored folders,
uploaded archives, leaked secrets, untouched templates, missing code) and
produces a 0-1 structure score with a readable breakdown.

No network access happens here — the caller supplies tree items and the text of
dependency manifests, which keeps this module fast and unit-testable.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Any

# ── Classification tables ─────────────────────────────────────────────────────

# Folders that hold third-party or generated code — never the student's work.
VENDORED_DIRS = {
    "node_modules", "bower_components", "vendor", "venv", ".venv", "env", "virtualenv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".tox", "site-packages",
    "dist", "build", "out", ".next", ".nuxt", ".svelte-kit", ".angular", ".parcel-cache",
    "target", "bin", "obj", ".gradle", ".dart_tool", "pods", "deriveddata",
    "coverage", ".nyc_output", ".idea", ".vscode", ".vs", ".git", ".cache", ".turbo",
}

SOURCE_EXT = {
    ".py": "Python", ".pyw": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala", ".groovy": "Groovy",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".hh": "C++",
    ".cs": "C#", ".fs": "F#", ".vb": "Visual Basic",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".m": "Objective-C", ".mm": "Objective-C", ".dart": "Dart", ".lua": "Lua",
    ".r": "R", ".jl": "Julia", ".pl": "Perl", ".sh": "Shell", ".bash": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".sol": "Solidity", ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".hs": "Haskell", ".clj": "Clojure", ".vue": "Vue", ".svelte": "Svelte",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "SCSS", ".less": "Less",
    ".ipynb": "Jupyter Notebook", ".asm": "Assembly", ".v": "Verilog", ".vhd": "VHDL", ".vhdl": "VHDL",
    ".ino": "Arduino", ".gd": "GDScript",
}
# Markup/style count as source, but "real code" excludes them for substance checks.
MARKUP_LANGS = {"HTML", "CSS", "SCSS", "Less"}

DOC_EXT = {".md", ".rst", ".txt", ".pdf", ".docx", ".doc", ".adoc"}
CONFIG_EXT = {".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".properties",
              ".gradle", ".lock", ".env", ".editorconfig", ".babelrc", ".eslintrc", ".prettierrc"}
ASSET_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp", ".mp4", ".mp3",
             ".wav", ".ogg", ".webm", ".ttf", ".otf", ".woff", ".woff2", ".eot", ".psd", ".fig"}
DATA_EXT = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".h5", ".hdf5", ".pkl", ".pickle",
            ".npy", ".npz", ".db", ".sqlite", ".sqlite3", ".pt", ".pth", ".onnx", ".joblib", ".tflite"}
ARCHIVE_BINARY_EXT = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".exe", ".dll", ".so",
                      ".dylib", ".apk", ".aab", ".ipa", ".jar", ".war", ".class", ".pyc", ".o", ".obj",
                      ".msi", ".dmg", ".iso", ".bin"}

# Files that must never be committed.
SECRET_FILE_PATTERNS = [
    re.compile(r"(^|/)\.env(\.(local|prod|production|dev|development))?$", re.I),
    re.compile(r"\.(pem|key|p12|pfx|keystore|jks)$", re.I),
    re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$", re.I),
    re.compile(r"(^|/)(credentials|service[-_]?account[-_\w]*|firebase[-_]?adminsdk[-_\w]*)\.json$", re.I),
]

# Dependency manifests whose text we parse for evidence.
MANIFEST_NAMES = {
    "package.json", "requirements.txt", "pyproject.toml", "pipfile", "setup.py", "environment.yml",
    "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "pubspec.yaml", "go.mod",
    "cargo.toml", "gemfile",
}

TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs", "testing", "e2e", "cypress"}
TEST_FILE_RE = re.compile(
    r"(^test_.+\.py$|.+_test\.(py|go|rb|dart)$|.+\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs)$|"
    r".+Tests?\.(java|kt|cs|swift)$|^test.+\.(java|kt)$)",
    re.I,
)

# Files every fresh framework template ships with — a repo made only of these
# (plus a README) is an untouched starter, not a project.
TEMPLATE_DEFAULTS = {
    # create-react-app
    "src/app.js", "src/app.css", "src/app.test.js", "src/index.js", "src/index.css", "src/logo.svg",
    "src/reportwebvitals.js", "src/setuptests.js", "public/index.html", "public/favicon.ico",
    "public/logo192.png", "public/logo512.png", "public/manifest.json", "public/robots.txt",
    # vite react
    "src/app.jsx", "src/main.jsx", "src/assets/react.svg", "public/vite.svg", "index.html",
    "vite.config.js", "eslint.config.js", ".eslintrc.cjs",
    # common
    "package.json", "package-lock.json", "yarn.lock", ".gitignore", "readme.md",
}

# Claimed tech → evidence rules. Keys are canonical names.
#   ext:   file extensions that prove it
#   files: marker file names (lower-case basename, or path suffix)
#   deps:  dependency names found in any manifest (lower-case)
TECH_RULES: dict[str, dict[str, list[str]]] = {
    "python": {"ext": [".py", ".ipynb"], "files": ["requirements.txt", "pyproject.toml", "setup.py"]},
    "javascript": {"ext": [".js", ".jsx", ".mjs", ".cjs"]},
    "typescript": {"ext": [".ts", ".tsx"], "files": ["tsconfig.json"], "deps": ["typescript"]},
    "java": {"ext": [".java"], "files": ["pom.xml", "build.gradle"]},
    "kotlin": {"ext": [".kt", ".kts"]},
    "c": {"ext": [".c", ".h"]},
    "c++": {"ext": [".cpp", ".cc", ".cxx", ".hpp", ".hh"], "files": ["cmakelists.txt"]},
    "c#": {"ext": [".cs"], "files": [".csproj", ".sln"]},
    ".net": {"ext": [".cs"], "files": [".csproj", ".sln"]},
    "go": {"ext": [".go"], "files": ["go.mod"]},
    "rust": {"ext": [".rs"], "files": ["cargo.toml"]},
    "php": {"ext": [".php"], "files": ["composer.json"]},
    "ruby": {"ext": [".rb"], "files": ["gemfile"]},
    "swift": {"ext": [".swift"]},
    "dart": {"ext": [".dart"], "files": ["pubspec.yaml"]},
    "flutter": {"files": ["pubspec.yaml"], "deps": ["flutter"]},
    "r": {"ext": [".r", ".rmd"]},
    "solidity": {"ext": [".sol"], "files": ["hardhat.config.js", "truffle-config.js"]},
    "html": {"ext": [".html", ".htm"]},
    "css": {"ext": [".css", ".scss", ".sass", ".less"]},
    "sass": {"ext": [".scss", ".sass"], "deps": ["sass", "node-sass"]},
    "sql": {"ext": [".sql"]},
    "jupyter": {"ext": [".ipynb"]},
    "react": {"ext": [".jsx", ".tsx"], "deps": ["react", "react-dom"]},
    "react native": {"deps": ["react-native", "expo"], "files": ["app.json"]},
    "next.js": {"deps": ["next"], "files": ["next.config.js", "next.config.mjs", "next.config.ts"]},
    "vue": {"ext": [".vue"], "deps": ["vue", "nuxt"]},
    "angular": {"deps": ["@angular/core"], "files": ["angular.json"]},
    "svelte": {"ext": [".svelte"], "deps": ["svelte", "@sveltejs/kit"]},
    "node.js": {"files": ["package.json"]},
    "express": {"deps": ["express"]},
    "nestjs": {"deps": ["@nestjs/core"]},
    "vite": {"deps": ["vite"], "files": ["vite.config.js", "vite.config.ts", "vite.config.mjs"]},
    "tailwind": {"deps": ["tailwindcss"], "files": ["tailwind.config.js", "tailwind.config.ts", "tailwind.config.cjs"]},
    "bootstrap": {"deps": ["bootstrap", "react-bootstrap"]},
    "material ui": {"deps": ["@mui/material", "@material-ui/core"]},
    "redux": {"deps": ["redux", "@reduxjs/toolkit", "react-redux"]},
    "graphql": {"ext": [".graphql", ".gql"], "deps": ["graphql", "apollo-server", "@apollo/client", "graphene"]},
    "socket.io": {"deps": ["socket.io", "socket.io-client", "python-socketio"]},
    "django": {"deps": ["django", "djangorestframework"], "files": ["manage.py"]},
    "flask": {"deps": ["flask"]},
    "fastapi": {"deps": ["fastapi"]},
    "streamlit": {"deps": ["streamlit"]},
    "spring": {"deps": ["spring-boot-starter", "spring-boot-starter-web", "spring-core", "spring-boot-starter-parent"]},
    "laravel": {"deps": ["laravel/framework"], "files": ["artisan"]},
    "mongodb": {"deps": ["mongoose", "mongodb", "pymongo", "motor", "spring-boot-starter-data-mongodb"]},
    "mysql": {"deps": ["mysql", "mysql2", "pymysql", "mysqlclient", "mysql-connector-python", "mysql-connector-java"]},
    "postgresql": {"deps": ["pg", "postgres", "psycopg2", "psycopg2-binary", "psycopg", "asyncpg", "postgresql"]},
    "sqlite": {"ext": [".sqlite", ".sqlite3", ".db"], "deps": ["sqlite3", "better-sqlite3", "sqlite"]},
    "redis": {"deps": ["redis", "ioredis", "aioredis"]},
    "firebase": {"deps": ["firebase", "firebase-admin", "@react-native-firebase/app"], "files": ["firebase.json"]},
    "supabase": {"deps": ["@supabase/supabase-js", "supabase"]},
    "prisma": {"deps": ["prisma", "@prisma/client"], "files": ["schema.prisma"]},
    "sqlalchemy": {"deps": ["sqlalchemy", "flask-sqlalchemy"]},
    "docker": {"files": ["dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"]},
    "kubernetes": {"files": ["deployment.yaml", "k8s", "helm", "chart.yaml"]},
    "aws": {"deps": ["boto3", "aws-sdk", "@aws-sdk/client-s3", "aws-cdk-lib"]},
    "tensorflow": {"deps": ["tensorflow", "tensorflow-cpu", "tensorflow-gpu", "@tensorflow/tfjs", "tf-keras"]},
    "keras": {"deps": ["keras", "tensorflow", "tf-keras"]},
    "pytorch": {"deps": ["torch", "torchvision", "pytorch-lightning", "lightning"]},
    "scikit-learn": {"deps": ["scikit-learn", "sklearn"]},
    "pandas": {"deps": ["pandas"]},
    "numpy": {"deps": ["numpy"]},
    "matplotlib": {"deps": ["matplotlib", "seaborn"]},
    "opencv": {"deps": ["opencv-python", "opencv-contrib-python", "opencv-python-headless"]},
    "nltk": {"deps": ["nltk"]},
    "transformers": {"deps": ["transformers", "sentence-transformers"]},
    "langchain": {"deps": ["langchain", "langchain-core", "langchain-community", "langchain-openai"]},
    "openai": {"deps": ["openai"]},
    "machine learning": {"ext": [".ipynb"], "deps": ["scikit-learn", "tensorflow", "torch", "keras", "xgboost", "lightgbm"]},
    "android": {"files": ["androidmanifest.xml"], "deps": ["com.android.application"]},
    "arduino": {"ext": [".ino"]},
    "jest": {"deps": ["jest", "@testing-library/react"]},
    "pytest": {"deps": ["pytest"]},
    "git": {"files": [".gitignore"]},
}

TECH_ALIASES = {
    "js": "javascript", "es6": "javascript", "vanilla js": "javascript", "ts": "typescript",
    "py": "python", "python3": "python",
    "reactjs": "react", "react.js": "react", "react js": "react",
    "nextjs": "next.js", "next": "next.js", "vuejs": "vue", "vue.js": "vue",
    "angularjs": "angular", "sveltekit": "svelte",
    "node": "node.js", "nodejs": "node.js", "node js": "node.js",
    "expressjs": "express", "express.js": "express", "nest.js": "nestjs",
    "tailwindcss": "tailwind", "tailwind css": "tailwind", "mui": "material ui",
    "html5": "html", "css3": "css", "scss": "sass",
    "cpp": "c++", "csharp": "c#", "dotnet": ".net", "asp.net": ".net", "golang": "go",
    "postgres": "postgresql", "psql": "postgresql", "mongo": "mongodb", "mongoose": "mongodb",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn", "torch": "pytorch", "tf": "tensorflow",
    "cv2": "opencv", "open cv": "opencv", "ml": "machine learning", "deep learning": "machine learning",
    "ai": "machine learning", "ai/ml": "machine learning", "ipynb": "jupyter", "jupyter notebook": "jupyter",
    "spring boot": "spring", "springboot": "spring", "k8s": "kubernetes", "amazon web services": "aws",
    "rest api": None, "api": None, "restful": None, "github": "git",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ext(name: str) -> str:
    name = name.lower()
    if name.endswith(".tar.gz"):
        return ".gz"
    dot = name.rfind(".")
    return name[dot:] if dot > 0 else ""


def _norm_scope(sub_path: str | None) -> str:
    return (sub_path or "").strip().strip("/")


def _in_scope(path: str, scope: str) -> bool:
    """Exact folder-boundary match: 'backend' matches 'backend/x', not 'backend-old/x'."""
    return not scope or path == scope or path.startswith(scope + "/")


def parse_manifest_dependencies(name: str, text: str) -> set[str]:
    """Extract lower-case dependency names from a manifest's text."""
    name = name.lower()
    deps: set[str] = set()
    try:
        if name == "package.json" or name == "composer.json":
            data = json.loads(text)
            for key in ("dependencies", "devDependencies", "peerDependencies", "require", "require-dev"):
                deps.update(k.lower() for k in (data.get(key) or {}))
        elif name in ("requirements.txt", "pipfile", "environment.yml"):
            for line in text.splitlines():
                line = line.split("#")[0].strip().lstrip("- ").strip()
                m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._\-\[\]]*)", line)
                if m and not line.startswith(("[", "python", "pip ")):
                    deps.add(re.sub(r"\[.*\]", "", m.group(1)).lower())
        elif name in ("pyproject.toml", "setup.py", "cargo.toml", "gemfile"):
            for m in re.finditer(r"""["']([A-Za-z0-9][A-Za-z0-9._\-]*)(?:\[[^\]]*\])?\s*(?:[<>=~!^][^"']*)?["']""", text):
                deps.add(m.group(1).lower())
            for m in re.finditer(r"^\s*([A-Za-z0-9_\-]+)\s*=", text, re.M):
                deps.add(m.group(1).lower())
        elif name == "pom.xml":
            deps.update(a.lower() for a in re.findall(r"<artifactId>\s*([^<\s]+)\s*</artifactId>", text))
        elif name in ("build.gradle", "build.gradle.kts"):
            for m in re.finditer(r"""["']([\w.\-]+):([\w.\-]+)(?::[^"']*)?["']""", text):
                deps.add(m.group(2).lower())
            deps.update(p.lower() for p in re.findall(r"""id\s*\(?\s*["']([\w.\-]+)["']""", text))
        elif name == "pubspec.yaml":
            deps.update(k.lower() for k in re.findall(r"^\s{2}([a-z_][a-z0-9_]*)\s*:", text, re.M))
        elif name == "go.mod":
            deps.update(m.lower() for m in re.findall(r"^\s*(?:require\s+)?([\w.\-]+/[\w.\-/]+)\s+v", text, re.M))
    except Exception:
        pass
    return {d for d in deps if d and len(d) < 80}


def _normalize_tech(item: str) -> str | None:
    t = item.strip().lower().strip(".,;:()")
    if not t:
        return None
    if t in TECH_ALIASES:
        return TECH_ALIASES[t]
    return t


def split_tech_stack(tech_stack: str | None) -> list[str]:
    if not tech_stack:
        return []
    parts = re.split(r"[,/|;+\n]|\band\b|&", tech_stack, flags=re.I)
    seen: list[str] = []
    for p in parts:
        p = p.strip()
        if p and p.lower() not in (s.lower() for s in seen):
            seen.append(p)
    return seen[:25]


# ── Main entry point ──────────────────────────────────────────────────────────


def analyze_tree(
    items: list[dict[str, Any]],
    *,
    sub_path: str | None = None,
    manifests: dict[str, str] | None = None,
    claimed_tech_stack: str | None = None,
    truncated: bool = False,
    branch: str | None = None,
) -> dict[str, Any]:
    """
    Analyze Git Trees API items (``{"path", "type": "blob"|"tree", "size"}``).

    ``manifests`` maps manifest path → file text (fetched by the caller).
    """
    scope = _norm_scope(sub_path)
    manifests = manifests or {}

    files: list[dict[str, Any]] = []
    dirs: list[str] = []
    vendored = Counter()
    for it in items:
        path = (it.get("path") or "").strip("/")
        if not path or not _in_scope(path, scope):
            continue
        rel = path[len(scope) + 1:] if scope and path != scope else ("" if scope else path)
        if not rel:
            continue
        parts = rel.split("/")
        vend = next((p for p in parts[:-1] if p.lower() in VENDORED_DIRS), None)
        if it.get("type") == "tree":
            if parts[-1].lower() in VENDORED_DIRS and vend is None:
                vendored.setdefault(parts[-1], 0)
            if vend is None and parts[-1].lower() not in VENDORED_DIRS:
                dirs.append(rel)
            continue
        if vend is not None:
            vendored[vend] += 1
            continue
        files.append({"path": rel, "full": path, "name": parts[-1], "depth": len(parts),
                      "size": int(it.get("size") or 0)})

    result: dict[str, Any] = {
        "scope": scope or "/",
        "branch": branch,
        "truncated": truncated,
        "scope_found": True,
    }

    if scope and not files and not dirs:
        result.update({
            "scope_found": False,
            "total_files": 0,
            "directories": [],
            "structure_score": 0.0,
            "red_flags": [f"Folder '{scope}' was not found in the repository"],
            "strengths": [],
            "recommendations": [f"Check the folder path in the link — '{scope}' does not exist on branch '{branch}'"],
            "key_markers": {},
            "full_tree": {},
        })
        return result

    # ── Classify files ────────────────────────────────────────────────────
    cats = Counter()
    lang_files = Counter()
    lang_bytes = Counter()
    test_files: list[str] = []
    secrets: list[str] = []
    binaries: list[str] = []
    ext_set: set[str] = set()
    basenames: set[str] = set()
    rel_lower: set[str] = set()

    for f in files:
        name, rel = f["name"], f["path"]
        low = name.lower()
        ext = _ext(name)
        ext_set.add(ext)
        basenames.add(low)
        rel_lower.add(rel.lower())
        parts_low = [p.lower() for p in rel.split("/")]

        if any(p.search(rel) for p in SECRET_FILE_PATTERNS) and not low.endswith((".example", ".sample", ".template")):
            secrets.append(rel)

        is_test = bool(TEST_FILE_RE.match(name)) or any(p in TEST_DIR_NAMES for p in parts_low[:-1])
        if ext in ARCHIVE_BINARY_EXT:
            cats["binary"] += 1
            binaries.append(rel)
        elif ext in SOURCE_EXT:
            lang = SOURCE_EXT[ext]
            lang_files[lang] += 1
            lang_bytes[lang] += f["size"]
            if is_test:
                cats["test"] += 1
                test_files.append(rel)
            else:
                cats["source"] += 1
        elif ext in DOC_EXT or low.startswith(("readme", "license", "changelog", "contributing")):
            cats["docs"] += 1
        elif ext in ASSET_EXT:
            cats["asset"] += 1
        elif ext in DATA_EXT:
            cats["data"] += 1
        elif ext in CONFIG_EXT or low.startswith(".") or low in ("dockerfile", "makefile", "procfile", "gemfile"):
            cats["config"] += 1
        else:
            cats["other"] += 1

    source_files = cats["source"] + cats["test"]
    code_files = sum(n for lang, n in lang_files.items() if lang not in MARKUP_LANGS)
    max_depth = max((f["depth"] for f in files), default=0)

    # ── Markers ───────────────────────────────────────────────────────────
    top_dirs = {d.split("/")[0].lower() for d in dirs}
    has = {
        "has_readme": any(n.startswith("readme") for n in basenames),
        "has_license": any(n.startswith(("license", "licence")) for n in basenames),
        "has_gitignore": ".gitignore" in basenames,
        "has_package_json": "package.json" in basenames,
        "has_requirements": bool(basenames & {"requirements.txt", "pipfile", "pyproject.toml", "setup.py", "environment.yml"}),
        "has_manifest": bool(basenames & MANIFEST_NAMES),
        "has_src_dir": bool(top_dirs & {"src", "source", "app", "lib", "core"}),
        "has_frontend_dir": bool(top_dirs & {"frontend", "client", "web", "ui"}),
        "has_backend_dir": bool(top_dirs & {"backend", "server", "api"}),
        "has_tests": cats["test"] > 0,
        "has_docker": bool(basenames & {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"}),
        "has_ci": any(r.startswith((".github/workflows/", ".gitlab-ci", ".circleci/")) or r == ".travis.yml" for r in rel_lower),
        "has_env_example": any(n.startswith(".env.") and n.endswith(("example", "sample", "template")) for n in basenames),
        "has_lint_config": any(n.startswith((".eslintrc", "eslint.config", ".prettierrc", ".flake8", "ruff.toml", ".pylintrc")) for n in basenames),
        "has_notebooks": lang_files["Jupyter Notebook"] > 0,
    }
    has["has_config_files"] = has["has_docker"] or has["has_env_example"] or has["has_ci"] or has["has_lint_config"]

    # ── Dependencies & project type ───────────────────────────────────────
    deps_by_manifest: dict[str, list[str]] = {}
    all_deps: set[str] = set()
    for mpath, text in manifests.items():
        # Manifests inside the analyzed folder, plus repository-root manifests,
        # which still describe the stack of a linked sub-folder.
        if not _in_scope(mpath.strip("/"), scope) and "/" in mpath.strip("/"):
            continue
        d = parse_manifest_dependencies(mpath.rsplit("/", 1)[-1], text)
        if d:
            rel = mpath[len(scope) + 1:] if scope else mpath
            deps_by_manifest[rel] = sorted(d)[:60]
            all_deps |= d

    project_types = _detect_project_types(basenames, rel_lower, ext_set, all_deps, lang_files)

    # ── Tech-stack verification against evidence ──────────────────────────
    tech_check = _check_tech_stack(claimed_tech_stack, ext_set, basenames, rel_lower, all_deps)

    # ── Red flags & strengths ─────────────────────────────────────────────
    red_flags: list[str] = []
    strengths: list[str] = []
    recs: list[str] = []

    if vendored:
        top = ", ".join(f"{k}/ ({v} files)" if v else f"{k}/" for k, v in vendored.most_common(4))
        red_flags.append(f"Generated or third-party folders committed: {top}")
        recs.append("Add node_modules/, venv/, build/ and similar folders to .gitignore and remove them from the repo")
    if binaries:
        sample = ", ".join(binaries[:3])
        if code_files < 5:
            red_flags.append(f"Code appears to be uploaded as archives/binaries instead of source files ({sample})")
            recs.append("Push the actual source files instead of zip/exe/jar uploads so the code can be reviewed")
        else:
            red_flags.append(f"Binary or archive files committed ({len(binaries)}), e.g. {sample}")
    if secrets:
        red_flags.append(f"Possible secrets committed: {', '.join(secrets[:3])}")
        recs.append("Remove secret files (.env, keys, service-account JSON) from the repo, rotate those credentials and commit a .env.example instead")
    if code_files == 0:
        if source_files > 0:
            red_flags.append("Only markup/style files found — no application logic")
        else:
            red_flags.append("No source code files found in the repository")
        recs.append("Push the project's source code")
    elif code_files < 3:
        red_flags.append(f"Very little code ({code_files} source file{'s' if code_files != 1 else ''})")
        recs.append("Push the complete project so reviewers can see the full implementation")

    non_template = {r for r in rel_lower if r not in TEMPLATE_DEFAULTS and not r.startswith(("public/", ".github/"))
                    and _ext(r) not in DOC_EXT and not r.endswith(".lock")}
    looks_like_template = bool(files) and len(non_template) <= 1 and (
        has["has_package_json"] and any(r in rel_lower for r in ("src/app.js", "src/app.jsx", "src/app.tsx")))
    if looks_like_template:
        red_flags.append("Repository looks like an unmodified framework starter template")
        recs.append("Build out the actual features — the repo currently contains only starter-template files")

    if cats["asset"] > 0 and cats["asset"] > 3 * max(1, code_files) and code_files < 5:
        red_flags.append("Mostly images/media with very little code")

    if has["has_readme"]:
        strengths.append("README documentation")
    else:
        recs.append("Add a README with the project overview, setup steps and screenshots")
    if has["has_manifest"]:
        strengths.append("Dependency manifest (" + ", ".join(sorted(set(m.rsplit('/', 1)[-1] for m in deps_by_manifest)) or ["present"]) + ")")
    elif code_files >= 3:
        recs.append("Add a dependency file (requirements.txt / package.json / pom.xml) so the project can be set up")
    if has["has_tests"]:
        strengths.append(f"Automated tests ({cats['test']} test file{'s' if cats['test'] != 1 else ''})")
    elif code_files >= 8:
        recs.append("Add automated tests to demonstrate code quality")
    if has["has_ci"]:
        strengths.append("CI workflow configured")
    if has["has_docker"]:
        strengths.append("Containerized with Docker")
    if lang_files["TypeScript"]:
        strengths.append("Typed code (TypeScript)")
    if has["has_frontend_dir"] and has["has_backend_dir"]:
        strengths.append("Clear frontend/backend separation")
    if has["has_gitignore"] and not vendored:
        strengths.append("Clean repo (.gitignore, no vendored folders)")

    # ── Score ─────────────────────────────────────────────────────────────
    substance = min(1.0, math.log2(1 + code_files) / math.log2(1 + 40))
    code_dirs = {f["path"].rsplit("/", 1)[0] for f in files if "/" in f["path"] and _ext(f["name"]) in SOURCE_EXT}
    organization = 0.0
    if max_depth >= 2:
        organization += 0.35
    if len(code_dirs) >= 3:
        organization += 0.35
    elif len(code_dirs) >= 1:
        organization += 0.15
    if has["has_src_dir"] or has["has_frontend_dir"] or has["has_backend_dir"] or project_types:
        organization += 0.30
    completeness = (0.30 * has["has_readme"] + 0.30 * has["has_manifest"] + 0.20 * has["has_tests"]
                    + 0.20 * (has["has_config_files"] or has["has_gitignore"]))
    hygiene = 1.0 - 0.35 * bool(vendored) - 0.30 * bool(binaries) - 0.35 * bool(secrets)
    score = 0.40 * substance + 0.20 * min(1.0, organization) + 0.25 * completeness + 0.15 * max(0.0, hygiene)
    if code_files == 0:
        score = min(score, 0.15)
    elif looks_like_template:
        score = min(score, 0.30)

    result.update({
        "total_files": len(files),
        "total_dirs": len(dirs),
        "max_depth": max_depth,
        "source_files": source_files,
        "code_files": code_files,
        "file_categories": dict(cats),
        "languages_by_files": dict(lang_files.most_common()),
        "languages_by_bytes": dict(lang_bytes.most_common()),
        "primary_language": lang_files.most_common(1)[0][0] if lang_files else None,
        "test_files": test_files[:20],
        "vendored_dirs": dict(vendored),
        "binary_files": binaries[:20],
        "secret_files": secrets[:10],
        "project_types": project_types,
        "dependencies": deps_by_manifest,
        "tech_stack_check": tech_check,
        "key_markers": has,
        "red_flags": red_flags,
        "strengths": strengths,
        "recommendations": recs,
        "looks_like_template": looks_like_template,
        "structure_score": round(max(0.0, min(1.0, score)), 4),
        "score_breakdown": {
            "substance": round(substance, 3),
            "organization": round(min(1.0, organization), 3),
            "completeness": round(completeness, 3),
            "hygiene": round(max(0.0, hygiene), 3),
        },
        "top_level": _top_level(files, dirs),
        "directories": sorted(dirs)[:300],
        "full_tree": _nested_tree(files, vendored),
    })
    return result


def _detect_project_types(basenames: set[str], rel_lower: set[str], ext_set: set[str],
                          deps: set[str], lang_files: Counter) -> list[str]:
    types: list[str] = []

    def add(label: str) -> None:
        if label not in types:
            types.append(label)

    if "next" in deps:
        add("Next.js web app")
    elif "react-native" in deps or "expo" in deps:
        add("React Native mobile app")
    elif "react" in deps:
        add("React frontend" + (" (Vite)" if "vite" in deps else ""))
    if "vue" in deps or ".vue" in ext_set:
        add("Vue frontend")
    if "@angular/core" in deps:
        add("Angular frontend")
    if "express" in deps or "@nestjs/core" in deps or "fastify" in deps:
        add("Node.js API server")
    if "django" in deps or "manage.py" in basenames:
        add("Django web app")
    if "fastapi" in deps:
        add("FastAPI backend")
    if "flask" in deps:
        add("Flask backend")
    if "streamlit" in deps:
        add("Streamlit app")
    if any(d.startswith("spring-boot") for d in deps):
        add("Spring Boot backend")
    if "androidmanifest.xml" in basenames:
        add("Android app")
    if "pubspec.yaml" in basenames:
        add("Flutter app")
    if "laravel/framework" in deps or "artisan" in basenames:
        add("Laravel web app")
    if deps & {"tensorflow", "torch", "scikit-learn", "keras", "xgboost"} or lang_files["Jupyter Notebook"] >= 1:
        add("Machine learning / data science")
    if ".sol" in ext_set:
        add("Smart contracts")
    if ".ino" in ext_set:
        add("Arduino / embedded")
    if not types and "index.html" in basenames and lang_files and set(lang_files) <= {"HTML", "CSS", "SCSS", "JavaScript"}:
        add("Static website")
    return types


def _check_tech_stack(tech_stack: str | None, ext_set: set[str], basenames: set[str],
                      rel_lower: set[str], deps: set[str]) -> dict[str, Any]:
    claimed = split_tech_stack(tech_stack)
    verified: list[dict[str, str]] = []
    missing: list[str] = []
    unknown: list[str] = []

    for raw in claimed:
        canon = _normalize_tech(raw)
        if canon is None:
            continue  # generic words like "REST API"
        rule = TECH_RULES.get(canon)
        if rule is None:
            unknown.append(raw)
            continue
        evidence = None
        for d in rule.get("deps", []):
            if d in deps:
                evidence = f"dependency '{d}'"
                break
        if not evidence:
            for fname in rule.get("files", []):
                if fname in basenames or any(r.endswith(fname) for r in rel_lower):
                    evidence = f"file '{fname}'"
                    break
        if not evidence:
            for e in rule.get("ext", []):
                if e in ext_set:
                    evidence = f"{e} files"
                    break
        if evidence:
            verified.append({"tech": raw, "evidence": evidence})
        else:
            missing.append(raw)

    checkable = len(verified) + len(missing)
    score = (len(verified) / checkable) if checkable else None
    return {
        "claimed": claimed,
        "verified": verified,
        "missing": missing,
        "unverifiable": unknown,
        "score": round(score, 3) if score is not None else None,
    }


def _top_level(files: list[dict[str, Any]], dirs: list[str]) -> list[dict[str, Any]]:
    counts = Counter()
    for f in files:
        if "/" in f["path"]:
            counts[f["path"].split("/", 1)[0]] += 1
    entries = [{"name": d, "type": "dir", "files": counts.get(d, 0)} for d in sorted({d.split("/")[0] for d in dirs})]
    entries += [{"name": f["path"], "type": "file"} for f in files if "/" not in f["path"]]
    return entries[:40]


def _nested_tree(files: list[dict[str, Any]], vendored: Counter, limit: int = 1500) -> dict[str, Any]:
    """Nested dict for display. Vendored folders are collapsed to a note."""
    root: dict[str, Any] = {}
    for f in files[:limit]:
        node = root
        parts = f["path"].split("/")
        for p in parts[:-1]:
            nxt = node.get(p)
            if not isinstance(nxt, dict):
                nxt = node[p] = {}
            node = nxt
        node[parts[-1]] = "file"
    for name, n in vendored.items():
        root.setdefault(name, f"(excluded: generated/third-party, {n} files)")
    if len(files) > limit:
        root["…"] = f"({len(files) - limit} more files not shown)"
    return root
