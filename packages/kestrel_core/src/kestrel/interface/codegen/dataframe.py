import functools
import inspect
import operator
import re
import sys
from typing import Callable

from kestrel.exceptions import (
    InvalidAttributes,
    InvalidOperatorInMultiColumnComparison,
    MismatchedFieldValueInMultiColumnComparison,
)
from kestrel.interface.codegen.utils import variable_attributes_to_dataframe
from kestrel.ir.filter import (
    AbsoluteTrue,
    BoolExp,
    ExpOp,
    FBasicComparison,
    FExpression,
    ListOp,
    MultiComp,
    NumCompOp,
    RefComparison,
    StrCompOp,
)
from kestrel.ir.instructions import (
    Construct,
    Filter,
    Information,
    Limit,
    ProjectAttrs,
    ProjectEntity,
    SourceInstruction,
    TransformingInstruction,
)
from kestrel.compat import DataFrame
import polars as pl
# TODO Phase 3: Refactor with Ibis when it replaces this codegen layer
# Currently being migrated from pandas to Polars
from typeguard import typechecked


@typechecked
def evaluate_source_instruction(instruction: SourceInstruction) -> DataFrame:
    eval_func = _select_eval_func(instruction.instruction)
    return eval_func(instruction)


@typechecked
def evaluate_transforming_instruction(
    instruction: TransformingInstruction, dataframe: DataFrame
) -> DataFrame:
    eval_func = _select_eval_func(instruction.instruction)
    return eval_func(instruction, dataframe)


@typechecked
def _select_eval_func(instruction_name: str) -> Callable:
    eval_funcs = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
    try:
        _funcs = filter(lambda x: x[0] == "_eval_" + instruction_name, eval_funcs)
        return next(_funcs)[1]
    except StopIteration:
        raise NotImplementedError(
            f"evaluation function for {instruction_name} in dataframe cache"
        )


@typechecked
def _eval_Construct(instruction: Construct) -> DataFrame:
    return DataFrame(instruction.data)


@typechecked
def _eval_Limit(instruction: Limit, dataframe: DataFrame) -> DataFrame:
    return dataframe.head(instruction.num)


@typechecked
def _eval_Information(instruction: Information, dataframe: DataFrame) -> DataFrame:
    return variable_attributes_to_dataframe(dataframe)


@typechecked
def _eval_ProjectAttrs(instruction: ProjectAttrs, dataframe: DataFrame) -> DataFrame:
    cols = set(dataframe.columns)
    invalid_attrs = set(instruction.attrs) - cols
    if invalid_attrs:
        raise InvalidAttributes(list(invalid_attrs))
    return dataframe.select(list(instruction.attrs))


@typechecked
def _eval_ProjectEntity(instruction: ProjectEntity, dataframe: DataFrame) -> DataFrame:
    if instruction.ocsf_field == "event":
        df = dataframe.unique()
    else:
        # No translation/mapping, assuming the data is already in OCSF (Kestrel extension)
        df = dataframe.select(
            [col for col in dataframe.columns if col.startswith(instruction.ocsf_field)]
        )
        # Rename columns by removing the prefix
        prefix_len = len(instruction.ocsf_field) + 1
        df = df.rename({col: col[prefix_len:] for col in df.columns})
        df = df.unique()
    return df


@typechecked
def _eval_Filter(instruction: Filter, dataframe: DataFrame) -> DataFrame:
    return dataframe.filter(_eval_Filter_exp(instruction.exp, dataframe))


@typechecked
def _eval_Filter_exp(exp: FExpression, dataframe: DataFrame) -> pl.Series:
    # return: a series of boolean, same length as dataframe
    if isinstance(exp, AbsoluteTrue):
        bs = pl.Series([True] * dataframe.height)
    elif isinstance(exp, BoolExp):
        bs = _eval_Filter_exp_BoolExp(exp, dataframe)
    elif isinstance(exp, MultiComp):
        bss = [xs for xs in _eval_Filter_exp(exp.comps, dataframe)]
        if exp.op == ExpOp.AND:
            bs = functools.reduce(lambda x, y: x & y, bss)
        elif exp.op == ExpOp.OR:
            bs = functools.reduce(lambda x, y: x | y, bss)
        else:
            raise NotImplementedError("unkown kestrel.ir.filter.ExpOp type")
    else:
        bs = _eval_Filter_exp_Comparison(exp, dataframe)
    return bs


@typechecked
def _eval_Filter_exp_BoolExp(boolexp: BoolExp, dataframe: DataFrame) -> pl.Series:
    # return: a series of boolean, same length as dataframe
    if boolexp.op == ExpOp.AND:
        bs = _eval_Filter_exp(boolexp.lhs, dataframe) & _eval_Filter_exp(
            boolexp.rhs, dataframe
        )
    elif boolexp.op == ExpOp.OR:
        bs = _eval_Filter_exp(boolexp.lhs, dataframe) | _eval_Filter_exp(
            boolexp.rhs, dataframe
        )
    else:
        raise NotImplementedError("unkown kestrel.ir.filter.ExpOp type")
    return bs


@typechecked
def _eval_Filter_exp_Comparison(
    c: FBasicComparison,
    df: DataFrame,
) -> pl.Series:
    # return: a series of boolean, same length as dataframe
    comp2func = {
        NumCompOp.EQ: operator.eq,
        NumCompOp.NEQ: operator.ne,
        NumCompOp.LT: operator.gt,  # value first in functools.partial
        NumCompOp.LE: operator.ge,  # value first in functools.partial
        NumCompOp.GT: operator.lt,  # value first in functools.partial
        NumCompOp.GE: operator.le,  # value first in functools.partial
        StrCompOp.EQ: operator.eq,
        StrCompOp.NEQ: operator.ne,
        StrCompOp.LIKE: lambda w, x: bool(
            re.search(w.replace(".", r"\.").replace("%", ".*?"), x)
        ),
        StrCompOp.NLIKE: lambda w, x: not bool(
            re.search(w.replace(".", r"\.").replace("%", ".*?"), x)
        ),
        StrCompOp.MATCHES: lambda w, x: bool(re.search(w, x)),
        StrCompOp.NMATCHES: lambda w, x: not bool(re.search(w, x)),
        ListOp.IN: lambda w, x: x in w,
        ListOp.NIN: lambda w, x: x not in w,
    }

    # if c.value is from previous subquery evaluation,
    # turn it into Union[List[str], List[int], List[Tuple]]
    # TODO: may upgrade from List to Set for faster IN test
    if isinstance(c.value, DataFrame):
        if len(c.value.columns) == 1:
            c.value = c.value[c.value.columns[0]].to_list()
        else:
            c.value = [tuple(row) for row in c.value.iter_rows()]

    try:
        # RefComparison has .fields; others have .field
        if isinstance(c, RefComparison):
            if len(c.fields) == 1:
                bools = df[c.fields[0]].map_elements(
                    functools.partial(comp2func[c.op], c.value),
                    return_dtype=pl.Boolean
                )
            else:
                if not (
                    isinstance(c.value, list)
                    and isinstance(c.value[0], tuple)
                    and len(c.fields) == len(c.value[0])
                ):
                    raise MismatchedFieldValueInMultiColumnComparison(c)

                # only support ListOp.IN and ListOp.NIN
                if c.op not in (ListOp.IN, ListOp.NIN):
                    raise InvalidOperatorInMultiColumnComparison(c)

                # Multi-column IN/NIN: check if row tuples are in the list
                # Create a struct from the fields and check membership
                struct_col = pl.struct(c.fields)
                row_tuples = df.select(struct_col).to_series().map_elements(
                    lambda x: tuple(x.values()) if isinstance(x, dict) else tuple(x),
                    return_dtype=pl.Object
                )
                bools = row_tuples.map_elements(
                    lambda x: x in c.value if c.op == ListOp.IN else x not in c.value,
                    return_dtype=pl.Boolean
                )
        else:
            bools = df[c.field].map_elements(
                functools.partial(comp2func[c.op], c.value),
                return_dtype=pl.Boolean
            )
        return bools
    except KeyError as e:
        raise e
        raise NotImplementedError(f"unkown kestrel.ir.filter.*Op type: {c.op}")
