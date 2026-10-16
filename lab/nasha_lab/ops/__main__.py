"""python -m nasha_lab.ops <command>   (SYNTHETIC / SIMULATED / OFFLINE)
  trace [--list | RUN_ID]      inspect a run's trace and approval state
  dashboard                    render results/ops/dashboard.html from the metrics/incident JSON
  evaluate control|faults|regression|gaps|fleet|all
  gate [candidate]             run the regression gate for a planner (default rule-model)
  versions register|drift|drill"""
import sys

if __name__ == "__main__":
    cmd, rest = (sys.argv[1] if len(sys.argv) > 1 else "help"), sys.argv[2:]
    if cmd == "trace": from .trace_view import main; sys.exit(main(rest))
    elif cmd == "dashboard": from .dashboard import main; main(rest)
    elif cmd == "evaluate": from .evaluate_ops import main; main(rest)
    elif cmd == "gate": from .gate import main; main(rest)
    elif cmd == "versions": from .versions import main; main(rest)
    else: print(__doc__)
