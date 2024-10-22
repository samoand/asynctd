"""Test workload_distributor in async environment."""
# pylint: disable=R0801

import logging
import unittest
import re
import os
import asyncio

from asynctd.task_distributor import (
    MappedException,
    run_distributively,
)

logger = logging.getLogger()


# Utility functions

def text_mapper(text):
    """
    Split text by lines.

    Parameters:
        text (string): text to be split.
    """
    return text.split('\n') if text else None


def num_mapper(nums):
    """
    Split a collection numbers into chunks.

    Parameters:
        nums: list of nums to be split.
    """
    suggested_num_chunks = os.cpu_count() or 16
    chunk_size = max(len(nums) // suggested_num_chunks, 1)
    return [nums[i:i+chunk_size] for i in range(0, len(nums), chunk_size)]


def total_reducer(partials):
    """
    Reduce (i.e. sum up) a list of numbers representing partial results.
    """
    return sum(partials)


def count_words(text):
    """Count number of words in text."""
    count = len(re.findall(r'\w+', text))
    logger.info('Returning %d from process %s. '
                'This process works with text "%s"\n',
                count, os.getpid(), text)
    return count


def count_substrings(text, substr):
    """Count number of substrings in text."""
    count = text.count(substr)
    logger.info('Returning %d from process %s. '
                'This process works with text "%s"\n',
                count, os.getpid(), text)
    return count


class UnitTestCase(unittest.TestCase):
    """Base test case with test data setup."""

    def setUp(self):
        """Initialize the environment."""
        self.long_text = """this is what could
be a very
long text.
It contains
multiple lines
this
is by design
just because
it looks cool
and awesome"""
        self.long_text_as_list = ['this is what could',
                                  'be a very',
                                  'long text.',
                                  'It contains',
                                  'multiple lines',
                                  'this',
                                  'is by design',
                                  'just because',
                                  'it looks cool',
                                  'and awesome']
        self.short_text = 'Plain'
        self.no_text = ''

        self.nums = range(10000)


# Async test cases rewritten for async-based task distributor

@run_distributively(
    'text', text_mapper, total_reducer)
async def count_num_words(text):
    """Count number of words."""
    return count_words(text)


@run_distributively(
    'text', None, total_reducer)
async def count_num_words_no_mapper(text):
    """Count number of words, no mapper."""
    return count_words(text)


@run_distributively(
    'text', text_mapper, total_reducer)
async def count_num_substr_occurrences(text, substr):
    """Count number of substring occurrences."""
    return count_substrings(text, substr)


@run_distributively(
    'sum_me_up', num_mapper, total_reducer)
async def distributed_sum(sum_me_up):
    """Sum up the numbers."""
    return sum(sum_me_up)


def async_test(f):
    """Decorator to run async test functions."""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


class TestAsync(UnitTestCase):
    """Run tests."""

    @async_test
    async def test_count_num_words_long(self):
        """Test count_num_words with long text."""
        result = await count_num_words(self.long_text)
        self.assertEqual(result, 24)

    @async_test
    async def test_count_num_words_long_no_mapper(self):
        """Test count_num_words, don't use a mapper."""
        result = await count_num_words_no_mapper(self.long_text_as_list)
        self.assertEqual(result, 24)

    @async_test
    async def test_count_num_words_short(self):
        """Test count_num_words with short text."""
        result = await count_num_words(self.short_text)
        self.assertEqual(result, 1)

    @async_test
    async def test_count_num_words_empty(self):
        """Test count_num_words without any text, expect 0."""
        result = await count_num_words(self.no_text)
        self.assertEqual(result, 0)

    @async_test
    async def test_count_num_words_none(self):
        """Test count_num_words with None for text."""
        with self.assertRaises(MappedException) as context:
            await count_num_words(None)
        logger.info(context.exception)

    @async_test
    async def test_count_num_substr_occurrences_long(self):
        """Test count_num_substr_occurrences in long text."""
        result = await count_num_substr_occurrences(self.long_text, 'a')
        self.assertEqual(result, 6)

    @async_test
    async def test_count_num_substr_occurrences_short(self):
        """Test count_num_substr_occurrences in short text."""
        result = await count_num_substr_occurrences(self.short_text, 'a')
        self.assertEqual(result, 1)

    @async_test
    async def test_count_num_substr_occurrences_empty(self):
        """Test count_num_substr_occurrences in empty text."""
        result = await count_num_substr_occurrences(self.no_text, 'a')
        self.assertEqual(result, 0)

    @async_test
    async def test_count_num_substr_occurrences_none(self):
        """Test count_num_substr_occurrences with None for text."""
        with self.assertRaises(MappedException) as context:
            await count_num_substr_occurrences(None, 'a')
        logger.info(context.exception)

    @async_test
    async def test_count_sum(self):
        """
        Test sum of numbers as an invariant.

        Verify that sum([1..1000]) is equal to sum of sums
        of subdivided components calculated distributively.
        """
        result = await distributed_sum(self.nums)
        self.assertEqual(sum(self.nums), result)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()
