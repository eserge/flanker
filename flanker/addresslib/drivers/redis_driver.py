import collections
import os
from logging import getLogger

import redis

log = getLogger(__name__)


class RedisCache(collections.MutableMapping):
    """
    RedisCache has the same interface as a dict, but talks to a redis server.
    """

    def __init__(
        self,
        host=None,
        port=None,
        prefix='mxr:',
        ttl=604800,
        password=None,
        redis_connection=None,
    ):
        self.prefix = prefix
        self.ttl = ttl

        if redis_connection:
            self.r = redis_connection
            return

        host = host or os.environ.get('REDIS_HOST', 'localhost')
        port = port or os.environ.get('REDIS_PORT', 6379)
        db = os.environ.get('REDIS_DB', 0)
        password = password or os.environ.get('REDIS_PASSWORD', 0)
        self.r = redis.StrictRedis(
            host=host, port=port, db=db, password=password,
            decode_responses=True
        )

    def __getitem__(self, key):
        try:
            return self.r.get(self.__keytransform__(key))
        except redis.RedisError:
            log.exception('Redis is unavailable')
            return None

    def __setitem__(self, key, value):
        try:
            return self.r.setex(self.__keytransform__(key), self.ttl, value)
        except redis.RedisError:
            log.exception('Redis is unavailable')
            return None

    def __delitem__(self, key):
        try:
            self.r.delete(self.__keytransform__(key))
        except redis.RedisError:
            log.exception('Redis is unavailable')

    def __iter__(self):
        try:
            return self.__value_generator__(self.r.keys(self.prefix + '*'))
        except redis.RedisError:
            log.exception('Redis is unavailable')
            return iter([])

    def __len__(self):
        try:
            return len(self.r.keys(self.__keytransform__('*')))
        except redis.RedisError:
            log.exception('Redis is unavailable')
            return 0

    def __keytransform__(self, key):
        return ''.join([self.prefix, str(key)])

    def __value_generator__(self, keys):
        for key in keys:
            yield self.r.get(key)
