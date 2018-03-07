# -*- coding: utf-8 -*-
from shipit_pulse_listener.monitoring import Monitoring
import pytest


@pytest.mark.asyncio
async def test_monitoring(QueueMock, NotifyMock):
    monitoring = Monitoring(1)
    monitoring.emails = ['pinco@pallino']
    await monitoring.add_task('Group1', 'Hook1', 'Task-invalid')
    await monitoring.add_task('Group1', 'Hook1', 'Task-pending')
    await monitoring.add_task('Group1', 'Hook1', 'Task1-completed')
    await monitoring.add_task('Group1', 'Hook1', 'Task2-completed')
    await monitoring.add_task('Group1', 'Hook2', 'Task-exception')
    await monitoring.add_task('Group2', 'Hook1', 'Task-failed')
    assert monitoring.tasks.qsize() == 6

    with pytest.raises(Exception):
        await monitoring.check_task()

    with pytest.raises(Exception):
        monitoring.send_report()

    monitoring.queue = QueueMock
    monitoring.notify = NotifyMock

    # No report sent, since we haven't collected any stats yet.
    monitoring.send_report()
    assert NotifyMock.email_obj == {}

    # Queue throws exception, remove task from queue.
    await monitoring.check_task()
    assert monitoring.tasks.qsize() == 5

    # Task is pending, put it back in the queue.
    await monitoring.check_task()
    assert monitoring.tasks.qsize() == 5

    # No report sent, since we haven't collected any stats yet.
    monitoring.send_report()
    assert NotifyMock.email_obj == {}

    # Task is completed.
    await monitoring.check_task()
    assert monitoring.stats['Hook1']['completed'] == ['Task1-completed']
    assert monitoring.tasks.qsize() == 4

    # Another task is completed.
    await monitoring.check_task()
    assert monitoring.stats['Hook1']['completed'] == ['Task1-completed', 'Task2-completed']
    assert monitoring.tasks.qsize() == 3

    # Task exception.
    await monitoring.check_task()
    assert monitoring.stats['Hook1']['exception'] == []
    assert monitoring.stats['Hook2']['exception'] == ['Task-exception']
    assert monitoring.tasks.qsize() == 2

    # Task failed.
    await monitoring.check_task()
    assert monitoring.stats['Hook1']['failed'] == ['Task-failed']
    assert monitoring.tasks.qsize() == 1

    # Task is pending, put it back in the queue.
    await monitoring.check_task()
    assert monitoring.tasks.qsize() == 1

    content = '''# Hook2 tasks for the last period


## exception

100.00% of all tasks (1/1)

* [Task-exception](https://tools.taskcluster.net/task-inspector/#Task-exception)

## completed

0.00% of all tasks (0/1)



## failed

0.00% of all tasks (0/1)

# Hook1 tasks for the last period


## exception

0.00% of all tasks (0/3)



## completed

66.67% of all tasks (2/3)

* [Task1-completed](https://tools.taskcluster.net/task-inspector/#Task1-completed)
* [Task2-completed](https://tools.taskcluster.net/task-inspector/#Task2-completed)

## failed

33.33% of all tasks (1/3)

* [Task-failed](https://tools.taskcluster.net/task-inspector/#Task-failed)'''

    monitoring.send_report()
    assert NotifyMock.email_obj['address'] == 'pinco@pallino'
    assert NotifyMock.email_obj['subject'] == 'Pulse listener tasks'
    assert NotifyMock.email_obj['content'] == content
    assert NotifyMock.email_obj['template'] == 'fullscreen'
    assert monitoring.stats == {}


@pytest.mark.asyncio
async def test_report_all_completed(QueueMock, NotifyMock):
    monitoring = Monitoring(1)
    monitoring.emails = ['pinco@pallino']
    await monitoring.add_task('Group1', 'Hook1', 'Task1-completed')
    await monitoring.add_task('Group1', 'Hook1', 'Task2-completed')
    assert monitoring.tasks.qsize() == 2

    monitoring.queue = QueueMock
    monitoring.notify = NotifyMock

    await monitoring.check_task()
    await monitoring.check_task()

    # No email sent, since all tasks were successful.
    monitoring.send_report()
    assert NotifyMock.email_obj == {}
    assert monitoring.stats == {}
