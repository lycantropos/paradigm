import inspect
import multiprocessing
import sys
import threading
import typing as t
from multiprocessing.queues import SimpleQueue


def is_main_process() -> bool:
    return multiprocessing.current_process().name == 'MainProcess'


def call_in_process(function: t.Callable[..., t.Any],
                    *args: t.Any,
                    **kwargs: t.Any) -> t.Any:
    with threading.Lock():
        caller_frame = inspect.stack()[1].frame
        caller_module = inspect.getmodule(caller_frame)
        assert caller_module is not None
        main_module = sys.modules.get('__main__')
        try:
            sys.modules['__main__'] = caller_module
            context = multiprocessing.get_context()
            queue = context.SimpleQueue()
            process = context.Process(
                    target=_put_result_in_queue,
                    name=(f'{call_in_process.__qualname__}_'
                          f'{function.__qualname__}'),
                    args=(queue, function, *args),
                    kwargs=kwargs
            )
            process.start()
            result, error = queue.get()
            process.join()
            if error is not None:
                raise error
            return result
        finally:
            if main_module is None:
                del sys.modules['__main__']
            else:
                sys.modules['__main__'] = main_module


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
