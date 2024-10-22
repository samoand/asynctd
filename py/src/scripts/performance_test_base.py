"""Test the performance of async task distributor under different conditions."""

from collections import defaultdict, namedtuple
from functools import reduce
import logging
import os
import time

from asynctd.task_distributor import run_distributively


Data = namedtuple('Data', ['valid_keys', 'words'])


def prepare_data():
    """
    Prepare test data.

    Build a list of strings
    'aaaa', 'aaab', ..., 'aaaz', ...., 'zzzz'
    """
    chars = [chr(c) for c in range(ord('a'), ord('z')+1)]

    result = reduce(
        lambda acc, el: acc+[el+c for el in el for c in reduce(
            lambda acc, el: acc+[el+c for el in el for c in reduce(
                lambda acc, el: acc+[el+c for el in el for c in chars],
                chars, [])],
            chars, [])], chars, [])
    return Data(valid_keys=set(result[:len(result)//2]), words=result)


def list_arg_divider(words):
    """Divide collection of arguments into chunks."""
    suggested_num_chunks = os.cpu_count() or 16
    suggested_chunk_size = len(words) // suggested_num_chunks
    return [words[i:i+suggested_chunk_size] for i
            in range(0, len(words), suggested_chunk_size)]


def occur_reducer(partials):
    """Reduce the results."""
    result = {}
    for partial in partials:
        result.update(partial)
    return result


async def calculate(valid_keys, words, simulate_activity_coef):
    """Perform an action on the given collection of words asynchronously."""
    async def simulate_activity_on_word(word):
        """Simulate CPU-intensive activity on the word by reversing it."""
        for _ in range(simulate_activity_coef):
            word = word[::-1]
        return word

    result = defaultdict(lambda: 0)
    for word in words:
        if await simulate_activity_on_word(word) in valid_keys:
            result[word] += 1
    return dict(result)  # Extract regular dict from defaultdict


@run_distributively('words', list_arg_divider, occur_reducer)
async def distribute_w_wide_step(
        valid_keys, words, simulate_activity_coef):
    """Run "calculate" with "run_distributively" decorator."""
    return await calculate(valid_keys, words, simulate_activity_coef)


@run_distributively(
    'words', lambda l: [[el] for el in l], occur_reducer)
async def distribute_w_small_step(
        valid_keys, words, simulate_activity_coef):
    """Run "calculate" with "run_distributively" decorator."""
    return await calculate(valid_keys, words, simulate_activity_coef)

@run_distributively(
    'words', lambda l: [[el] for el in l], occur_reducer, max_workers=16)
async def distribute_w_small_step_max_workers(
        valid_keys, words, simulate_activity_coef):
    """Run "calculate" with "run_distributively" decorator."""
    return await calculate(valid_keys, words, simulate_activity_coef)


async def distribute_undecorated(
        valid_keys, words, simulate_activity_coef):
    """Run "calculate" without "run_distributively" decorator."""
    return await calculate(valid_keys, words, simulate_activity_coef)


async def run_all_tests(repeat_times, simulate_activity_coef):
    """Run all async performance tests."""
    logger = logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)

    data = prepare_data()
    valid_keys = data.valid_keys
    words = data.words * repeat_times

    start_time = time.time()
    await distribute_w_wide_step(
        valid_keys, words, simulate_activity_coef)
    logger.info(
        'Time to run distribute_w_wide_step: %d seconds',
        time.time() - start_time)

    start_time = time.time()
    await distribute_w_small_step(
        valid_keys, words, simulate_activity_coef)
    logger.info(
        'Time to run distribute_w_small_step: '
        '%d seconds', time.time() - start_time)

    start_time = time.time()
    await distribute_w_small_step_max_workers(
        valid_keys, words, simulate_activity_coef)
    logger.info(
        'Time to run distribute_w_small_step_max_workers: '
        '%d seconds', time.time() - start_time)

    start_time = time.time()
    await distribute_undecorated(
        valid_keys, words, simulate_activity_coef)
    logger.info('Time to run distribute_undecorated: %d seconds',
                time.time() - start_time)
