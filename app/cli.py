import argparse
import json
import sys

from pathlib import Path

from app import database as db
from app.agent_query import answer_question
from app.agents.orchestrator import run_full_pipeline
from app.pipeline import ingest_pdf_path


def main() -> None:
    db.init_db()
    p = argparse.ArgumentParser(prog="env-table-agent")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="Ingest a PDF and print document_id")
    pi.add_argument("pdf", type=str)

    pq = sub.add_parser("query", help="Query stored readings")
    pq.add_argument("--doc", required=True)
    pq.add_argument("--month", required=True)
    pq.add_argument("--area", required=True)
    pq.add_argument("--reference", default="Executed BMRs")

    pa = sub.add_parser("ask", help="Natural-language query (demo parser)")
    pa.add_argument("--doc", required=True)
    pa.add_argument("question", nargs=argparse.REMAINDER)

    pp = sub.add_parser("pipeline", help="Run extract → validate → analyze on a PDF")
    pp.add_argument("pdf", type=str)
    pp.add_argument("--reference", default="Executed BMRs")

    args = p.parse_args()
    if args.cmd == "ingest":
        r = ingest_pdf_path(Path(args.pdf))
        print(json.dumps(r.model_dump(), indent=2))
    elif args.cmd == "pipeline":
        data = Path(args.pdf).read_bytes()
        r = run_full_pipeline(data, Path(args.pdf).name, reference_document=args.reference)
        print(json.dumps(r.model_dump(), indent=2))
    elif args.cmd == "query":
        row = db.fetch_reading(args.doc, args.month, args.area, args.reference)
        if row is None:
            print("Not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(row.model_dump(), indent=2))
    else:
        q = " ".join(args.question).strip()
        if not q:
            p.error("question text required")
        ans = answer_question(args.doc, q)
        print(json.dumps(ans.model_dump(), indent=2))


if __name__ == "__main__":
    main()
