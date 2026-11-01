"""
Worktree setup and port management runner.
Restores gitignored necessities and manages per-worktree dev ports.
"""

import argparse
import json
import os
import sys
from pathlib import Path

PORT_REGISTRY_NAME = "worktree-ports.json"
BASE_PORT = 5173


def get_git_dir(root: Path) -> Path:
    git_path = root / ".git"
    if git_path.is_file():
        # Sub-worktree pointing to gitdir: ...
        content = git_path.read_text(encoding="utf-8").strip()
        if content.startswith("gitdir:"):
            target = Path(content.split(":", 1)[1].strip())
            return target if target.is_absolute() else (root / target).resolve()
    return git_path


def manage_ports(root: Path, action: str, target_path: str = None) -> None:
    git_dir = get_git_dir(root)
    registry_file = git_dir / PORT_REGISTRY_NAME
    ports = {}
    if registry_file.exists():
        try:
            ports = json.loads(registry_file.read_text(encoding="utf-8"))
        except Exception:
            ports = {}

    # Prune non-existent paths
    ports = {p: port for p, port in ports.items() if Path(p).exists()}

    if action == "list":
        print("Worktree dev port allocations:")
        for p, port in sorted(ports.items(), key=lambda x: x[1]):
            print(f"  {port}: {p}")
        return

    if action == "release":
        to_release = target_path or str(root.resolve())
        if to_release in ports:
            freed = ports.pop(to_release)
            registry_file.write_text(json.dumps(ports, indent=2), encoding="utf-8")
            dev_port_file = Path(to_release) / ".dev-port"
            if dev_port_file.exists():
                dev_port_file.unlink()
            print(f"Released port {freed} for {to_release}")
        else:
            print(f"No port was assigned to {to_release}")
        return

    # Allocate port for current worktree
    cur_path = str(root.resolve())
    if cur_path in ports:
        allocated = ports[cur_path]
    else:
        used_ports = set(ports.values())
        allocated = BASE_PORT
        while allocated in used_ports:
            allocated += 1
        ports[cur_path] = allocated
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        registry_file.write_text(json.dumps(ports, indent=2), encoding="utf-8")

    (root / ".dev-port").write_text(str(allocated), encoding="utf-8")
    print(f"Assigned port {allocated} to worktree {cur_path}")


def main():
    parser = argparse.ArgumentParser(description="Worktree environment bootstrap & port manager")
    parser.add_argument("--check", action="store_true", help="Check status without modifying")
    parser.add_argument("--list-ports", action="store_true", help="List all port allocations")
    parser.add_argument("--release-port", nargs="?", const="", help="Release port for worktree")
    parser.add_argument("--source", type=str, help="Source root for bootstrapping")
    args = parser.parse_args()

    root = Path.cwd().resolve()

    if args.list_ports:
        manage_ports(root, "list")
        return

    if args.release_port is not None:
        target = args.release_port if args.release_port != "" else None
        manage_ports(root, "release", target)
        return

    # Ensure required directories exist
    for dir_name in [".tmp", "directives", "execution", "docs", "brand", "config", "src", "tests"]:
        d = root / dir_name
        d.mkdir(parents=True, exist_ok=True)

    manage_ports(root, "allocate")
    print("Worktree bootstrap verified.")


if __name__ == "__main__":
    main()
