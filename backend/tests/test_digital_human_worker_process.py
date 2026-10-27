"""Actual SDK handler serialization and forkserver transfer; no provider fixtures."""
import inspect
import multiprocessing
import os
import pickle

from digital_human.agent_worker import create_server


def _inspect_registered_handler(handler, pipe):
    pipe.send((os.getpid(), handler.__module__, handler.__qualname__, inspect.iscoroutinefunction(handler)))
    pipe.close()


def test_registered_handler_survives_real_forkserver_process():
    handler = create_server()._entrypoint_fnc
    assert pickle.loads(pickle.dumps(handler)) is handler
    context = multiprocessing.get_context("forkserver")
    parent, child_pipe = context.Pipe(duplex=False)
    child = context.Process(target=_inspect_registered_handler, args=(handler, child_pipe))
    child.start()
    child_pipe.close()
    try:
        assert parent.poll(5), "Forkserver did not receive the actual registered SDK callback"
        pid, module, name, is_async = parent.recv()
        child.join(5)
        assert child.exitcode == 0
        assert pid == child.pid and pid > 0 and pid != os.getpid()
        assert module == handler.__module__ and name == handler.__qualname__ and is_async
        print(f"actual_forkserver_child_pid={pid} exit_code={child.exitcode} handler={module}.{name}")
    finally:
        parent.close()
