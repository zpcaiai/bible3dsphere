"""Keep slow connection creation outside psycopg2's pool bookkeeping mutex.

The same ThreadedConnectionPool API, transaction cleanup and close behavior are
retained. Pending creations reserve capacity and explicit keys under the lock;
only real libpq connection establishment happens without that global mutex.
"""
from concurrent.futures import Future

import psycopg2
from psycopg2.pool import PoolError, ThreadedConnectionPool

from readiness_diagnostics import stage


class ConcurrentConnectionPool(ThreadedConnectionPool):
    def __init__(self, minconn, maxconn, *args, **kwargs):
        self._pending_connections = {}
        super().__init__(minconn, maxconn, *args, **kwargs)

    def getconn(self, key=None):
        create = False
        with self._lock:
            if self.closed:
                raise PoolError('connection pool is closed')
            if key is None:
                key = self._getkey()
            if key in self._used:
                return self._used[key]
            pending = self._pending_connections.get(key)
            if pending is None:
                if self._pool:
                    conn = self._pool.pop()
                    self._used[key] = conn
                    self._rused[id(conn)] = key
                    return conn
                if len(self._used) + len(self._pending_connections) >= self.maxconn:
                    raise PoolError('connection pool exhausted')
                pending = Future()
                self._pending_connections[key] = pending
                create = True
        if not create:
            return pending.result()
        try:
            with stage('db.connect'):
                conn = psycopg2.connect(*self._args, **self._kwargs)
        except BaseException as exc:
            with self._lock:
                del self._pending_connections[key]
            pending.set_exception(exc)
            raise
        with self._lock:
            closed = self.closed
            if not closed:
                self._used[key] = conn
                self._rused[id(conn)] = key
            del self._pending_connections[key]
        if closed:
            error = PoolError('connection pool is closed')
            try:
                conn.close()
            finally:
                pending.set_exception(error)
            raise error
        pending.set_result(conn)
        return conn
