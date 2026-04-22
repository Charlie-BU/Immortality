import argparse
import asyncio
import time

from src.services.figure_and_relation import syncFeedsToFRCore


def _parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync fine-grained feeds to FigureAndRelation core fields."
    )
    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="User ID",
    )
    parser.add_argument(
        "--fr-id",
        type=int,
        required=True,
        help="FigureAndRelation ID",
    )
    return parser.parse_args()


if __name__ == "__main__":
    start = time.perf_counter()
    args = _parseArgs()
    res = asyncio.run(syncFeedsToFRCore(user_id=args.user_id, fr_id=args.fr_id))
    print(res)
    print(f"Time cost: {time.perf_counter() - start:.4f} seconds")
