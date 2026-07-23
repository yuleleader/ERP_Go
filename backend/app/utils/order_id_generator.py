# -*- coding: utf-8 -*-
import random
import threading
import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor

class OrderIdGenerator:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._queue = deque()
        self._max_size = 1000
        self._min_size = 100
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock_inner = threading.RLock()
        self._initialize()

    def _initialize(self):
        for _ in range(self._max_size):
            self._queue.append(self._generate_random_number())

    def _generate_random_number(self) -> str:
        return str(random.randint(0, 999999)).zfill(6)

    def _refill_unsafe(self):
        """内部填充方法，调用者必须持有 _lock_inner"""
        needed = self._max_size - len(self._queue)
        for _ in range(needed):
            self._queue.append(self._generate_random_number())

    def _refill_if_needed(self):
        with self._lock_inner:
            if len(self._queue) <= self._min_size:
                self._refill_unsafe()

    def get_random_number(self) -> str:
        with self._lock_inner:
            if len(self._queue) == 0:
                self._refill_unsafe()
            result = self._queue.popleft()
            if len(self._queue) <= self._min_size:
                try:
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(self._executor, self._refill_if_needed)
                except RuntimeError:
                    # 不在异步上下文中，同步填充
                    self._refill_if_needed()
            return result

    def get_random_number_sync(self) -> str:
        with self._lock_inner:
            if len(self._queue) == 0:
                self._refill_unsafe()
            return self._queue.popleft()

order_id_generator = OrderIdGenerator()
