from datetime import timedelta

from ecs.workflow import Activity, register
from ecs.workflow.models import Foo

register(Foo)


class A(Activity):
    deadline = timedelta(seconds=0)
    
    class Meta:
        model = Foo


class B(Activity):
    class Meta:
        model = Foo


class C(Activity):
    class Meta:
        model = Foo
