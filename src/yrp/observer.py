from typing import Any
from abc import ABC, abstractmethod

class Observable():
    def __init__(self) -> None:
        self._observers: list[Observer] = []

    def subscribe(self, observer: 'Observer') -> None:
        self._observers.append(observer)

    def notify_observers(self, *args: Any, **kwargs: Any) -> None:
        for observer in self._observers:
            observer.notify(self, *args, **kwargs)

    def unsubscribe(self, observer: 'Observer') -> None:
        self._observers.remove(observer)


class Observer(ABC):
    def __init__(self, observable: Observable) -> None:
        observable.subscribe(self)

    @abstractmethod
    def notify(
        self,
        observable: Observable,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        pass

