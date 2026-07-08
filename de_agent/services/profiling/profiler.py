"""Dataset profiling.

Locally we profile the uploaded file with pandas (fast, no cluster). On Databricks
the same interface can be backed by a Spark ``DESCRIBE``/summary query; the domain
output (`DatasetProfile`) is identical, so nodes don't care which path ran.
"""

from __future__ import annotations

import io

from de_agent.domain.dataset import ColumnProfile, DatasetProfile


class DatasetProfiler:
    def profile_csv_bytes(self, data: bytes, *, sample_rows: int = 5) -> DatasetProfile:
        import pandas as pd

        df = pd.read_csv(io.BytesIO(data))
        row_count = int(len(df))
        columns: list[ColumnProfile] = []
        for name in df.columns:
            series = df[name]
            null_count = int(series.isna().sum())
            distinct = int(series.nunique(dropna=True))
            null_fraction = (null_count / row_count) if row_count else 0.0
            samples = [str(v) for v in series.dropna().unique()[:sample_rows]]
            columns.append(
                ColumnProfile(
                    name=str(name),
                    dtype=str(series.dtype),
                    null_count=null_count,
                    null_fraction=round(null_fraction, 4),
                    distinct_count=distinct,
                    sample_values=samples,
                    is_candidate_key=null_count == 0 and distinct == row_count and row_count > 0,
                )
            )
        return DatasetProfile(row_count=row_count, column_count=len(columns), columns=columns)
