"""Remove all posts ingested via the twitter-file connector.

These rows correspond to data loaded from the JSONL path used by
``TwitterFileConnector`` (typically ``backend/data/twitter_posts.jsonl``).

Usage (from ``backend/`` directory, with ``DATABASE_URL`` set, e.g. via ``.env``):

  python scripts/delete_twitter_file_dataset.py --dry-run
  python scripts/delete_twitter_file_dataset.py --execute

``--dry-run`` (default) only prints counts. ``--execute`` performs the deletes
in one transaction: ``processed_posts`` first, then ``raw_posts``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow ``python scripts/...`` from the backend directory
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import delete, func, select  # noqa: E402

from app.db.session import async_session_maker  # noqa: E402
from app.models.processed_post import ProcessedPost  # noqa: E402
from app.models.raw_post import RawPost  # noqa: E402

SOURCE = "twitter-file"


async def _counts() -> tuple[int, int]:
    async with async_session_maker() as session:
        raw_n = await session.scalar(
            select(func.count()).select_from(RawPost).where(RawPost.source == SOURCE)
        )
        proc_n = await session.scalar(
            select(func.count())
            .select_from(ProcessedPost)
            .join(RawPost, ProcessedPost.raw_post_id == RawPost.id)
            .where(RawPost.source == SOURCE)
        )
    return int(raw_n or 0), int(proc_n or 0))


async def _delete_all() -> tuple[int, int]:
    """Return (deleted_processed, deleted_raw)."""
    async with async_session_maker() as session:
        raw_ids = select(RawPost.id).where(RawPost.source == SOURCE)

        res_proc = await session.execute(
            delete(ProcessedPost).where(ProcessedPost.raw_post_id.in_(raw_ids))
        )
        deleted_proc = res_proc.rowcount or 0

        res_raw = await session.execute(delete(RawPost).where(RawPost.source == SOURCE))
        deleted_raw = res_raw.rowcount or 0

        await session.commit()
    return deleted_proc, deleted_raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete rows (default: print counts only, no writes)",
    )
    args = parser.parse_args()
    dry_run = not args.execute

    raw_count, proc_count = asyncio.run(_counts())
    print(f"raw_posts where source={SOURCE!r}: {raw_count}")
    print(f"processed_posts linked to those raw rows: {proc_count}")

    if dry_run:
        print("Dry-run: no changes. Pass --execute to delete.")
        return

    deleted_proc, deleted_raw = asyncio.run(_delete_all())
    print(f"Deleted processed_posts: {deleted_proc}")
    print(f"Deleted raw_posts: {deleted_raw}")


if __name__ == "__main__":
    main()
