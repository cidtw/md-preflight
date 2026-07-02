from collections import OrderedDict

from app.schemas.report import PreflightReport


class RunStore:
    def __init__(self, max_items: int = 128) -> None:
        self._max_items: int = max_items
        self._items: OrderedDict[str, PreflightReport] = OrderedDict()

    def save(self, report: PreflightReport) -> None:
        self._items[report.run_id] = report
        self._items.move_to_end(report.run_id)
        while len(self._items) > self._max_items:
            _ = self._items.popitem(last=False)

    def get(self, run_id: str) -> PreflightReport | None:
        return self._items.get(run_id)


RUN_STORE = RunStore()
