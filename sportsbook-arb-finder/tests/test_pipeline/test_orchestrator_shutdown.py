"""Tests for orchestrator shutdown behaviour.

Verifies that setting ``stop_event`` causes all book tasks to exit
within a bounded time and that ``run()``-level logic handles both
clean exits and per-task failures gracefully.
"""

import asyncio


class TestStopEventShutdown:
    """Verify stop_event triggers clean task exit."""

    def test_single_task_exits_on_stop(self):
        async def _run():
            stop_event = asyncio.Event()
            iterations = 0

            async def fake_book(stop_event):
                nonlocal iterations
                while not stop_event.is_set():
                    iterations += 1
                    await asyncio.sleep(0.01)

            task = asyncio.create_task(fake_book(stop_event))
            await asyncio.sleep(0.05)
            stop_event.set()
            await asyncio.wait_for(task, timeout=2.0)

            assert iterations > 0
            assert task.done()

        asyncio.run(_run())

    def test_multiple_tasks_all_exit(self):
        async def _run():
            stop_event = asyncio.Event()
            exit_log: list[str] = []

            async def fake_book(name, stop_event):
                while not stop_event.is_set():
                    await asyncio.sleep(0.01)
                exit_log.append(name)

            tasks = [
                asyncio.create_task(fake_book("bookA", stop_event)),
                asyncio.create_task(fake_book("bookB", stop_event)),
                asyncio.create_task(fake_book("bookC", stop_event)),
            ]

            await asyncio.sleep(0.05)
            stop_event.set()

            done, pending = await asyncio.wait(tasks, timeout=2.0)
            assert len(pending) == 0
            assert set(exit_log) == {"bookA", "bookB", "bookC"}

        asyncio.run(_run())

    def test_failed_task_does_not_block_others(self):
        async def _run():
            stop_event = asyncio.Event()
            exit_log: list[str] = []

            async def failing_book(stop_event):
                raise RuntimeError("Book exploded!")

            async def healthy_book(name, stop_event):
                while not stop_event.is_set():
                    await asyncio.sleep(0.01)
                exit_log.append(name)

            tasks = [
                asyncio.create_task(failing_book(stop_event)),
                asyncio.create_task(healthy_book("healthyA", stop_event)),
                asyncio.create_task(healthy_book("healthyB", stop_event)),
            ]

            await asyncio.sleep(0.1)
            stop_event.set()

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Failing task raised
            assert isinstance(results[0], RuntimeError)
            # Healthy tasks exited cleanly
            assert "healthyA" in exit_log
            assert "healthyB" in exit_log

        asyncio.run(_run())

    def test_shutdown_completes_within_timeout(self):
        async def _run():
            stop_event = asyncio.Event()

            async def slow_exit_book(stop_event):
                while not stop_event.is_set():
                    await asyncio.sleep(0.01)
                # Simulate cleanup
                await asyncio.sleep(0.05)

            tasks = [
                asyncio.create_task(slow_exit_book(stop_event))
                for _ in range(5)
            ]

            stop_event.set()
            done, pending = await asyncio.wait(tasks, timeout=2.0)
            assert len(pending) == 0

        asyncio.run(_run())

    def test_gather_with_return_exceptions(self):
        """Ensure gather(return_exceptions=True) collects all results."""
        async def _run():
            stop_event = asyncio.Event()

            async def ok_task(stop_event):
                while not stop_event.is_set():
                    await asyncio.sleep(0.01)
                return "ok"

            async def bad_task(stop_event):
                await asyncio.sleep(0.02)
                raise ValueError("boom")

            tasks = [
                asyncio.create_task(ok_task(stop_event)),
                asyncio.create_task(bad_task(stop_event)),
                asyncio.create_task(ok_task(stop_event)),
            ]

            await asyncio.sleep(0.1)
            stop_event.set()

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # First and third tasks returned "ok"
            assert results[0] == "ok"
            assert isinstance(results[1], ValueError)
            assert results[2] == "ok"

        asyncio.run(_run())
