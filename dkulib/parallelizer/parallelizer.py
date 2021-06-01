# -*- coding: utf-8 -*-
"""Apply a function to a pandas DataFrame with parallelization, error logging and progress tracking"""

import logging
import inspect
import math

from typing import Callable, AnyStr, Any, List, Tuple, NamedTuple, Dict, Union, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from time import perf_counter
from collections import OrderedDict, namedtuple
from enum import Enum

import pandas as pd
from more_itertools import chunked, flatten
from tqdm.auto import tqdm as tqdm_auto

from dkulib.io_utils.plugin_io_utils import generate_unique


class ErrorHandling(Enum):
    """Enum class to identify how to handle API errors"""

    LOG = "Log"
    FAIL = "Fail"


class BatchError(ValueError):
    """Custom exception raised if the Batch function fails"""


class DataFrameParallelizer:
    """Apply a function to a pandas DataFrame with parallelization, error logging and progress tracking.

    This class is particularly well-suited for synchronous functions calling an API, either row-by-row or by batch.

    Attributes:
        function: Any function taking a dict as input (row-by-row mode) or a list of dict (batch mode),
            and returning a response with additional information, typically a JSON string.
            In batch mode, the response from the function should be parsable by the `batch_response_parser` attribute.
        error_handling: If ErrorHandling.LOG (default), log the error from the function as a warning,
            and add additional columns to the dataframe with the error message and error type.
            If ErrorHandling.FAIL, the function will fail is there is any error.
        exceptions_to_catch: Tuple of Exception classes to catch. Mandatory if ErrorHandling.LOG (default).
        parallel_workers: Number of concurrent threads to parallelize the function. Default is 4.
        batch_support: If True, send batches of row (list of dict) to the `function`
            Else (default) send rows as dict to the function
        batch_size: Number of rows to include in each batch. Default is 10.
            Taken into account if `batch_support` is True.
        batch_response_parser: Function used to parse the raw response (list of dict) from the batch function
            and assign the actual responses and errors back to the original batch (also list of dict).
            This is often required for batch API
        output_column_prefix: Column prefix to add to the output columns for the `function` responses and errors.
            Default is "output".
        verbose: If True, log additional information on errors
            Else (default) log the error message and the error type

    """

    DEFAULT_PARALLEL_WORKERS = 4
    DEFAULT_BATCH_SIZE = 10
    DEFAULT_BATCH_SUPPORT = False
    DEFAULT_VERBOSE = False
    DEFAULT_OUTPUT_COLUMN_PREFIX = "output"
    OUTPUT_COLUMN_NAME_DESCRIPTIONS = OrderedDict(
        [
            ("response", "Raw response in JSON format"),
            ("error_message", "Error message"),
            ("error_type", "Error type or code"),
            ("error_raw", "Raw error"),
        ]
    )
    """Default dictionary of output column names (key) and their descriptions (value)"""

    def __init__(
        self,
        function: Callable[[Union[Dict, List[Dict]]], Union[Dict, List[Dict]]],
        error_handling: ErrorHandling = ErrorHandling.LOG,
        exceptions_to_catch: Tuple[Exception] = (),
        parallel_workers: int = DEFAULT_PARALLEL_WORKERS,
        batch_support: bool = DEFAULT_BATCH_SUPPORT,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_response_parser: Optional[Callable[[List[Dict], Any, NamedTuple], List[Dict]]] = None,
        output_column_prefix: AnyStr = DEFAULT_OUTPUT_COLUMN_PREFIX,
        verbose: bool = DEFAULT_VERBOSE,
    ):
        self.function = function
        self.error_handling = error_handling
        self.exceptions_to_catch = exceptions_to_catch
        if error_handling == ErrorHandling.LOG and not exceptions_to_catch:
            raise ValueError("Please set at least one exception in exceptions_to_catch")
        self.parallel_workers = parallel_workers
        self.batch_support = batch_support
        self.batch_size = batch_size
        self.batch_response_parser = batch_response_parser
        if batch_support and not batch_response_parser:
            raise ValueError("Please provide a valid batch_response_parser function")
        self.output_column_prefix = output_column_prefix
        self.verbose = verbose

    def _get_unique_output_column_names(self, existing_names: List[AnyStr]) -> NamedTuple:
        """Return a named tuple with prefixed column names and their descriptions"""
        OutputColumnNameTuple = namedtuple("OutputColumnNameTuple", self.OUTPUT_COLUMN_NAME_DESCRIPTIONS.keys())
        return OutputColumnNameTuple(
            *[
                generate_unique(name=column_name, existing_names=existing_names, prefix=self.output_column_prefix)
                for column_name in OutputColumnNameTuple._fields
            ]
        )

    def _apply_function_and_parse_response(
        self, output_column_names: NamedTuple, row: Dict = None, batch: List[Dict] = None, **function_kwargs,
    ) -> Union[Dict, List[Dict]]:  # sourcery skip: or-if-exp-identity
        """Wrap a row-by-row or batch function with error handling and response parsing

        It applies `self.function` and and:
        - If batch, parse the response to extract results and errors using the `self.batch_response_parser` function
        - handles errors from the function with two methods:
            * (default) log the error message as a warning and return the row with error keys
            * fail if there is an error

        """
        if row and batch:
            raise (ValueError("Please use either row or batch as arguments, but not both"))
        output = deepcopy(row) if row else deepcopy(batch)
        for output_column in output_column_names:
            if row:
                output[output_column] = ""
            else:
                for output_row in output:
                    output_row[output_column] = ""
        try:
            response = (
                self.function(row=row, **function_kwargs) if row else self.function(batch=batch, **function_kwargs)
            )
            if row:
                output[output_column_names.response] = response
            else:
                output = self.batch_response_parser(
                    batch=batch, response=response, output_column_names=output_column_names
                )
                errors = [
                    row[output_column_names.error_message] for row in output if row[output_column_names.error_message]
                ]
                if errors:
                    raise BatchError(str(errors))
        except self.exceptions_to_catch + (BatchError,) as error:
            if self.error_handling == ErrorHandling.FAIL:
                raise error
            logging.warning(
                f"Function {self.function.__name__} failed on: {row if row else batch} because of error: {error}"
            )
            error_type = str(type(error).__qualname__)
            module = inspect.getmodule(error)
            if module:
                error_type = f"{module.__name__}.{error_type}"
            if row:
                output[output_column_names.error_message] = str(error)
                output[output_column_names.error_type] = error_type
                output[output_column_names.error_raw] = str(error.args)
            else:
                for output_row in output:
                    output_row[output_column_names.error_message] = str(error)
                    output_row[output_column_names.error_type] = error_type
                    output_row[output_column_names.error_raw] = str(error.args)
        return output

    def _convert_results_to_df(
        self, df: pd.DataFrame, results: List[Dict], output_column_names: NamedTuple,
    ) -> pd.DataFrame:
        """Combine results from the function with the input dataframe"""
        output_schema = {**{column_name: str for column_name in output_column_names}, **dict(df.dtypes)}
        output_df = (
            pd.DataFrame.from_records(results)
            .reindex(columns=list(df.columns) + list(output_column_names))
            .astype(output_schema)
        )
        if not self.verbose:
            output_df.drop(labels=output_column_names.error_raw, axis=1, inplace=True)
        if self.error_handling == ErrorHandling.FAIL:
            error_columns = [
                output_column_names.error_message,
                output_column_names.error_type,
                output_column_names.error_raw,
            ]
            output_df.drop(labels=error_columns, axis=1, inplace=True, errors="ignore")
        return output_df

    def run(self, df: pd.DataFrame, **function_kwargs,) -> pd.DataFrame:
        """Apply a function to a pandas.DataFrame with parallelization, error logging and progress tracking

        The DataFrame is iterated on and fed to the function as dictionaries, row-by-row or by batches of rows.
        This process is accelerated by the use of concurrent threads and is tracked with a progress bar.
        Errors are catched if they match the `self.exceptions_to_catch` attribute and automatically logged.
        Once the whole DataFrame has been iterated on, results and errors are added as additional columns.

        Args:
            df: Input dataframe on which the function will be applied
            **function_kwargs: Arbitrary keyword arguments passed to the `function`

        Returns:
            Input dataframe with additional columns:
            - response from the `function`
            - error message if any
            - error type if any

        """
        # First, we create a generator expression to yield each row of the input dataframe.
        # Each row will be represented as a dictionary like {"column_name_1": "foo", "column_name_2": 42}
        df_row_generator = (index_series_pair[1].to_dict() for index_series_pair in df.iterrows())
        df_num_rows = len(df.index)
        start = perf_counter()
        if self.batch_support:
            logging.info(
                f"Applying function {self.function.__name__} in parallel to {df_num_rows} row(s)"
                + f" using batch size of {self.batch_size}..."
            )
            df_row_batch_generator = chunked(df_row_generator, self.batch_size)
            len_generator = math.ceil(df_num_rows / self.batch_size)
        else:
            logging.info(f"Applying function {self.function.__name__} in parallel to {df_num_rows} row(s)...")
            len_generator = df_num_rows
        output_column_names = self._get_unique_output_column_names(existing_names=df.columns)
        pool_kwargs = {**{"output_column_names": output_column_names}, **function_kwargs.copy()}
        for kwarg in ["function", "row", "batch"]:  # Reserved pool keyword arguments
            pool_kwargs.pop(kwarg, None)
        if not self.batch_support and "batch_response_parser" in pool_kwargs:
            pool_kwargs.pop("batch_response_parser", None)
        results = []
        with ThreadPoolExecutor(max_workers=self.parallel_workers) as pool:
            if self.batch_support:
                futures = [
                    pool.submit(self._apply_function_and_parse_response, batch=batch, **pool_kwargs)
                    for batch in df_row_batch_generator
                ]
            else:
                futures = [
                    pool.submit(self._apply_function_and_parse_response, row=row, **pool_kwargs)
                    for row in df_row_generator
                ]
            for future in tqdm_auto(as_completed(futures), total=len_generator, miniters=1, mininterval=1.0):
                results.append(future.result())
        results = flatten(results) if self.batch_support else results
        output_df = self._convert_results_to_df(df, results, output_column_names)
        num_error = sum(output_df[output_column_names.response] == "")
        num_success = len(df.index) - num_error
        logging.info(
            (
                f"Applied function in parallel: {num_success} row(s) succeeded, {num_error} failed "
                f"in {(perf_counter() - start):.2f} seconds."
            )
        )
        return output_df
