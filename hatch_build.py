"""Custom build hook for annextube to build the web frontend.

This is a simple custom build hook that runs `npm install` and `npm run build`
during package installation to compile the Svelte frontend.

MAINTENANCE NOTE:
If this becomes difficult to maintain or needs more features (separate dev/prod
builds, watch mode, better error handling, etc.), consider migrating to
hatch-jupyter-builder (https://github.com/jupyterlab/hatch-jupyter-builder),
which is a mature plugin designed specifically for integrating npm builds with
Python packages. See jupyterlab-git for a reference implementation.
"""
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    """Build hook that compiles the Svelte frontend during package build."""

    PLUGIN_NAME = "frontend-build"

    def initialize(self, version, build_data):
        """Run frontend build before packaging."""
        if self.target_name not in ("wheel", "sdist", "editable"):
            return

        project_root = Path(self.root)
        frontend_dir = project_root / "frontend"
        web_dir = project_root / "web"

        # Check if frontend directory exists
        if not frontend_dir.exists():
            print("Warning: frontend/ directory not found, skipping frontend build")
            return

        # Check if Node.js/npm is available
        try:
            subprocess.run(
                ["npm", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: npm not found, skipping frontend build")
            print("To build the frontend manually: cd frontend && npm install && npm run build")
            return

        print("Building web frontend...")

        # Install dependencies if needed
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("Installing frontend dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True,
            )

        # Build frontend (vite outputs directly to ../web)
        print("Compiling Svelte frontend...")
        subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            check=True,
        )

        # Verify build output
        if web_dir.exists() and (web_dir / "index.html").exists():
            print(f"Frontend build complete! Output: {web_dir}")
        else:
            print(f"Warning: Expected build output not found at {web_dir}")
