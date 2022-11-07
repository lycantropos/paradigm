import sys
import typing as t
from multiprocessing import get_context
from multiprocessing.queues import SimpleQueue
from pathlib import Path


def try_in_process(function: t.Callable[..., t.Any],
                   *args: t.Any,
                   **kwargs: t.Any) -> t.Any:
    if (getattr(sys, 'ps1', None) is None
            and Path(
                    getattr(sys.modules.get('__main__'), '__file__', __file__)
            ).exists()):
        context = get_context()
        queue = context.SimpleQueue()
        process = context.Process(target=_put_result_in_queue,
                                  name=function.__qualname__,
                                  args=(queue, function, *args),
                                  kwargs=kwargs)
        process.start()
        result, error = queue.get()
        process.join()
        if error is not None:
            raise error
        return result
    else:
        return function(*args, **kwargs)


def _put_result_in_queue(queue: SimpleQueue,
                         function: t.Callable[..., t.Any],
                         *args: t.Any,
                         **kwargs: t.Any) -> None:
    try:
        result = function(*args, **kwargs)
    except Exception as error:
        queue.put((None, error))
        raise error
    else:
        queue.put((result, None))
