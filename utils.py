"""Utility methods."""
from typing import TypeVar, Iterable

T = TypeVar('T')


def grouped(n: int, iter: Iterable[T]) -> Iterable[Iterable[T]]:
    """Group iterator into n-element chunks."""
    done = False

    def _slice():
        nonlocal done
        try:
            for _ in range(n):
                yield next(iter)
        except StopIteration:
            done = True
            return
    
    while not done:
        yield _slice()
