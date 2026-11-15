"""Run reproducible walk-forward evaluations without blocking Flask requests."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import config
from app.exceptions import FortuneLabException
from app.services.evaluation import evaluate_walk_forward
from app.storage import read_json, validate_filename, write_json

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--filename",
        action="append",
        required=True,
        help="Result JSON basename; repeat for separate game reports",
    )
    parser.add_argument(
        "--draws", type=int, default=50, help="Latest held-out draws (minimum 2)"
    )
    parser.add_argument(
        "--min-training", type=int, default=50, help="Minimum earlier draws (minimum 2)"
    )
    parser.add_argument(
        "--tickets",
        type=int,
        default=5,
        help="Equal unique tickets per algorithm and draw (1-100)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        help="evaluation_*.json basename inside the configured analysis directory",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        if args.output and not args.output.startswith("evaluation_"):
            parser.error(
                "--output must start with evaluation_ to keep evaluations separate from analysis snapshots"
            )
        output_name = (
            args.output or f"evaluation_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        )
        output_path = validate_filename(output_name, config.ANALYSIS_PATH)
        evaluations = []
        for filename in args.filename:
            if not filename.startswith("result_"):
                parser.error("--filename must refer to a result_*.json dataset")
            input_path = validate_filename(filename, config.DATA_PATH)
            logger.info("Evaluating %s", filename)
            report = evaluate_walk_forward(
                read_json(input_path),
                evaluation_draws=args.draws,
                min_training_draws=args.min_training,
                tickets=args.tickets,
                seed=args.seed,
            )
            evaluations.append({"source_file": filename, **report})
        write_json(
            output_path,
            {"generated_at": datetime.now().isoformat(), "evaluations": evaluations},
        )
        print(f"Saved historical walk-forward evaluation: {output_path}")
        print(
            "Historical simulation only; results do not establish improved winning odds."
        )
        return 0
    except (FortuneLabException, OSError, ValueError) as exc:
        logger.error("Evaluation failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
