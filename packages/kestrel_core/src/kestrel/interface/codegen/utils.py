from itertools import groupby
from typing import List, Union
import polars as pl

from kestrel.compat import DataFrame


def variable_attributes_to_dataframe(attrs: Union[List[str], DataFrame]) -> DataFrame:
    # If attrs is a DataFrame, extract column names
    if isinstance(attrs, pl.DataFrame):
        attrs = list(attrs.columns)

    categories = []
    for k, g in groupby(sorted(attrs), lambda s: s.split(".")[0] if "." in s else ""):
        categories.append(", ".join(g))
    return pl.DataFrame({"attributes": categories})
