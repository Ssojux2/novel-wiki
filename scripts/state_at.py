#!/usr/bin/env python3
"""장 시점별 상태 조회 (World Model 스냅샷).

사용:
  python3 state_at.py --project . --at ch10 --entity 한서윤
  python3 state_at.py --project . --at 10 --all            # 그 시점에 등장한 모든 인물
  python3 state_at.py --project . --at 10 --all --kind places
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bible_lib import STATEFUL_DIRS, ch_num, find_entity, format_state, load_bible, state_at  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--at", required=True, help="장 (예: ch10 또는 10). 그 장 '끝' 시점")
    ap.add_argument("--entity", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--kind", default="characters", choices=STATEFUL_DIRS)
    a = ap.parse_args()

    root = Path(a.project).resolve()
    n = ch_num(a.at)
    if n is None:
        sys.exit(f"장 번호를 해석할 수 없음: {a.at}")
    bible = load_bible(root)

    pages = []
    for name in a.entity:
        p = find_entity(bible, name)
        if p is None:
            print(f"- **{name}**: 바이블에 페이지 없음")
        else:
            pages.append(p)
    if a.all:
        pages += [p for p in bible[a.kind] if state_at(p, n)["present"] and p not in pages]

    if not pages and not a.entity:
        print("조회할 대상이 없습니다. --entity 또는 --all을 쓰세요.")
        return
    for p in pages:
        print(format_state(p, n))


if __name__ == "__main__":
    main()
