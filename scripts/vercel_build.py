"""Run Vercel build-time Django tasks with useful, secret-safe logging."""

import os
import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sms.settings")


def run() -> None:
    import django
    from django.core.management import call_command

    print("[vercel-build] Loading Django...", flush=True)
    django.setup()

    print("[vercel-build] Running system checks...", flush=True)
    call_command("check", verbosity=2)

    print("[vercel-build] Applying database migrations...", flush=True)
    call_command("migrate", interactive=False, verbosity=2)

    print("[vercel-build] Collecting static files...", flush=True)
    call_command("collectstatic", interactive=False, verbosity=2)
    print("[vercel-build] Completed successfully.", flush=True)


if __name__ == "__main__":
    try:
        run()
    except BaseException as exc:
        print(
            f"[vercel-build] FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc()
        raise
