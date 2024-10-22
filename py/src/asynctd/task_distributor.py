"""
Util to distributively run a function.

Assumption: the function signature contains
a large iterable argument either in args or kwargs.

This util divides the large argument, runs distributively
using async, builds the end result from partials.

Typically used as a decorator (as illustrated in unit tests).
Supported semantics:
  arg divider (controls minimum number of tasks)
  result reducer
  policy for exception handling
  maximum number of concurrent workers controlled via semaphore
"""

import asyncio
import inspect
import json
import logging
import os
import sys
import traceback
from copy import deepcopy
from enum import Enum
from typing import Any, Callable, Optional, Sequence

logger = logging.getLogger()

DEFAULT_NUM_WORKERS = 1000

class SuccessPolicy(Enum):
    """Define success status of all the worker runs."""

    EXPECT_ALL = 0  # most restrictive, success if all runs are successful
    EXPECT_ANY = 1  # success if one or more runs are successful
    SUPER_LAX = 2  # most permissive, success even if everything failed


class MappedException(Exception):
    """Support exceptions reported by multiple workers."""

    def __init__(self, orig_ex_descriptors):
        """
        Initialize.

        :param orig_ex_descriptors: list of error descriptors coming from all the
         workers that threw an exception
        """
        super().__init__(
            json.dumps(orig_ex_descriptors, indent=4) +
            f'\n{len(orig_ex_descriptors)} workers threw exception(s)')


def _per_worker_args(
        func:Callable, wrapped_args:tuple, wrapped_kwargs:dict,
        mapped_arg:Any, arg_value_divider:Optional[
            Callable[[Sequence], Optional[Sequence[Sequence]]]]):
    """Build args per worker from the original args."""
    func_arg_spec = inspect.getfullargspec(func)
    if arg_value_divider is None:
        arg_value_divider = lambda l: l  # Default to no splitting

    def build_function_args(divided_arg_subset, orig_args, orig_kwargs):
        """
        Build replacement *args, **kwargs.

        Use a subset in place of the original divisible arg
        """
        new_args = [orig_args[i] if func_arg_spec.args[i] !=
                    mapped_arg else divided_arg_subset
                    for i in range(len(func_arg_spec.args))]
        new_args.extend(orig_args[len(func_arg_spec.args):])
        new_kwargs = deepcopy(orig_kwargs)
        if mapped_arg in new_kwargs:
            new_kwargs[mapped_arg] = divided_arg_subset
        return new_args, new_kwargs

    premapped_arg_value = None
    if mapped_arg in func_arg_spec.args:
        premapped_arg_value = wrapped_args[
            func_arg_spec.args.index(mapped_arg)]
    elif mapped_arg in wrapped_kwargs:
        premapped_arg_value = wrapped_kwargs[mapped_arg]

    # Use arg_value_divider to control the minimum number of tasks
    arg_value_parts = arg_value_divider(
        premapped_arg_value) if premapped_arg_value else []

    mapped_arg_values = [
        build_function_args(
            arg_value_part, wrapped_args, wrapped_kwargs)
        for arg_value_part in arg_value_parts
    ] if arg_value_parts else [[wrapped_args, wrapped_kwargs]]

    return mapped_arg_values


async def run_worker(
        semaphore: Optional[asyncio.Semaphore],
        func:Callable,
        *args,
        **kwargs):
    """Run a single worker async."""
    async def run(func, *args, **kwargs):
        try:
            result = await func(*args, **kwargs)
        except Exception:  # pylint: disable=W0718
            ex_type, ex_value, t_back = sys.exc_info()
            ex_desc = {
                'type': str(ex_type),
                'value': str(ex_value),
                'tb': traceback.format_tb(t_back),
                'function': func.__name__,
                'function_inputs': {'args': args, 'kwargs': kwargs},
                'pid': os.getpid()
            }
            result = None
        else:
            ex_desc = None
        return {'result': result, 'ex': ex_desc}

        # Check if a semaphore is provided
    if semaphore:
        async with semaphore:
            return await run(func, *args, **kwargs)
    else:
        return await run(func, *args, **kwargs)

def run_distributively(
        mapped_arg:Optional[str]=None,
        arg_value_divider:Optional[
            Callable[[Sequence], Optional[Sequence[Sequence]]]]=None,
        result_reducer:Optional[Callable]=None,
        max_workers:Optional[int]=None,
        success_policy:SuccessPolicy=SuccessPolicy.EXPECT_ALL):
    """
    Run a function in multiple async tasks in parallel.

    :mapped_arg: argument that will be divided across tasks (list, etc.)
    :arg_value_divider: controls the minimum number of tasks,
      divides the mapped_arg
    :result_reducer: function to combine results from all tasks
    :num_workers: maximum number of concurrent workers
      (Semaphore controlled)
    :success_policy: defines the condition for considering
      the run successful
    """
    def wrapper(func):
        async def wrapped(*args, **kwargs):
            # Generate the args for each worker based on
            #  arg_value_divider
            per_worker_arg_chunks = _per_worker_args(
                func, args, kwargs, mapped_arg, arg_value_divider)

            logger.info(
                "Number of per worker arg chunks: %d",
                len(per_worker_arg_chunks))
            logger.info(
                "Max concurrent workers: %s",
                max_workers if max_workers is not None else 'unset')

            # Semaphore to control maximum concurrency
            semaphore = None if max_workers is None else \
                asyncio.Semaphore(max_workers)

            # Run all workers asynchronously
            tasks = [
                run_worker(
                    semaphore, func, *worker_args[0], **worker_args[1])
                for worker_args in per_worker_arg_chunks
            ]
            results = await asyncio.gather(*tasks)

            # Collect and reduce the results
            result_exceptions = [
                result['ex'] for result in results if result['ex']
            ]
            result_data = None if result_reducer is None \
                else result_reducer(
                [result['result'] for result in results
                 if result['result']])

            # Handle success policies
            if success_policy == SuccessPolicy.SUPER_LAX:
                return result_data
            if success_policy == SuccessPolicy.EXPECT_ANY and (
                    result_data or not result_exceptions):
                return result_data
            if success_policy == SuccessPolicy.EXPECT_ALL and (
                    not result_exceptions):
                return result_data
            raise MappedException(result_exceptions)

        return wrapped

    return wrapper
