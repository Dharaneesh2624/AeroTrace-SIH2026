import argparse
import json
from pathlib import Path
from .ingest import load_directory, read_session, split_sessions
from .model import train, save, load
from .evaluate import evaluate
from .monitor import process, empty_state
from .trends import trend_summary

ROOT = Path(__file__).resolve().parents[1]

def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")

def train_command(data, out):
    sessions, audit = load_directory(data)
    split, manifest = split_sessions(sessions)
    fitted = train(split["train"], split["calibration"], manifest)
    write_json(out/"data_audit.json", {"sessions": audit, "total_rows": sum(len(s) for s in sessions),
                                     "split_strategy": "chronological disjoint day/interval groups; no row shuffle"})
    write_json(out/"split.json", manifest)
    provenance = Path(data)/"provenance.json"
    if provenance.exists():
        write_json(out/"data_provenance.json", json.loads(provenance.read_text()))
    save(fitted, out/"model.json")
    report = evaluate(fitted, split["test"])
    report["trends"] = trend_summary(report["sessions"])
    write_json(out/"evaluation.json", report)
    lines = ["# AE300 backend validation report", "", f"Model: `{fitted['model_id']}`", "",
             f"Input: {len(sessions)} sessions / {sum(len(s) for s in sessions):,} rows.",
             "Labels: unavailable. Reference health: unverified. No supervised fault classifier or validated RUL model.", "",
             "## Held-out results", "", "```json", json.dumps(report['held_out'], indent=2), "```", "",
             "These are unlabelled anomaly counts, not false positives or fault accuracy.", "",
             "## Synthetic perturbation checks", "",
             "| Perturbation | Windows | Persistent detection | Data quality detection | Median delay, s |",
             "|---|---:|---:|---:|---:|"]
    for label, r in report["synthetic_tests"].items():
        lines.append(f"| {label} | {r['windows']} | {r['persistent_anomaly_detections']} | {r['data_quality_detections']} | {r['median_delay_s']} |")
    lines += ["", "Perturbations are deliberately large synthetic demonstrations, not naturally occurring labelled failures.",
              "Missing temperature data can invalidate the oil-pressure model: dropout must produce abstention, not a healthy score.",
              "", "## Limits", "", "- Day grouping keeps overlapping recordings out of different splits. Original engine/ECU identities are unverified.",
              "- Only two held-out calendar days; not a fleet or independent-engine validation.",
              "- Empirical thermal models predict one-step temperature change, not absolute combustion temperature.",
              "- No calibrated failure probability, remaining life, mission reliability or airworthiness assessment.",
              "- Model is frozen after training; inference never updates its baseline.", "",
              "Inference timings (in-process only, excluding database/network): `"+json.dumps(report['inference_latency_ms'])+"`."]
    (out/"VALIDATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"model_id": fitted["model_id"], "output": str(out), **report["held_out"]}, indent=2))

def main():
    parser = argparse.ArgumentParser(description="AE300 research backend; not operational safety software")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("train")
    p.add_argument("--data", type=Path, default=ROOT/"data/public_examples")
    p.add_argument("--out", type=Path, default=ROOT/"artifacts")
    p = sub.add_parser("replay")
    p.add_argument("csv", type=Path)
    p.add_argument("--model", type=Path, default=ROOT/"artifacts/model.json")
    p.add_argument("--output", type=Path, default=ROOT/"artifacts/replay.jsonl")
    p.add_argument("--limit", type=int, default=300)
    p.add_argument("--engine", default="public-example-unknown-engine")
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "train":
        train_command(args.data, args.out)
    elif args.command == "replay":
        if not 1 <= args.limit <= 100000:
            parser.error("Replay limit must be 1..100000")
        model = load(args.model)
        records, _ = read_session(args.csv, args.engine)
        state = empty_state()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as stream:
            for record in records[:args.limit]:
                result, state = process(record, model, state)
                stream.write(json.dumps(result, allow_nan=False)+"\n")
        print(f"Wrote {min(len(records), args.limit)} causal replay records: {args.output}")
    else:
        import uvicorn
        uvicorn.run("aerotrace.api:create_app", factory=True, host="127.0.0.1", port=args.port, workers=1)

if __name__ == "__main__":
    main()
