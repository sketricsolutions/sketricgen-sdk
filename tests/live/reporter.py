"""Per-operation reporting for the live probe.

Each probe records what the SDK returned and what DynamoDB observed, plus
whether they agreed. The collected rows are printed in the pytest terminal
summary (see ``conftest.pytest_terminal_summary``) so a mismatch is visible at a
glance, followed by a reminder to revoke the temporary keys.
"""

from dataclasses import dataclass, field


@dataclass
class ProbeRow:
    operation: str
    sdk: str
    observed: str
    match: bool


@dataclass
class ProbeReporter:
    rows: list[ProbeRow] = field(default_factory=list)

    def record(self, operation: str, sdk: str, observed: str, match: bool) -> None:
        self.rows.append(ProbeRow(operation, sdk, observed, match))

    def render(self) -> str:
        if not self.rows:
            return ""
        op_w = max(len("operation"), *(len(r.operation) for r in self.rows))
        sdk_w = max(len("sdk"), *(len(r.sdk) for r in self.rows))
        obs_w = max(len("observed"), *(len(r.observed) for r in self.rows))
        lines = [
            "Live probe — SDK vs DynamoDB:",
            f"  {'':2}{'operation':<{op_w}}  {'sdk':<{sdk_w}}  "
            f"{'observed':<{obs_w}}",
        ]
        for r in self.rows:
            mark = "OK " if r.match else "XX "
            lines.append(
                f"  {mark}{r.operation:<{op_w}}  {r.sdk:<{sdk_w}}  "
                f"{r.observed:<{obs_w}}"
            )
        mismatches = [r for r in self.rows if not r.match]
        if mismatches:
            lines.append(
                f"  {len(mismatches)} MISMATCH(es) — investigate the XX rows above."
            )
        return "\n".join(lines)
