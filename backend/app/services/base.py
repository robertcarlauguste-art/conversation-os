"""
Base service (Rule 3: services contain business logic).

A service is the "front desk" of a domain: routes talk to it, it
talks to repositories, and it's the only layer allowed to make
domain decisions (validate a business rule, coordinate more than one
repository call, decide what happens next). Routes stay thin by
design — they hand the request to a service and shape the response.

This is a scaffold only. No domain service exists yet, since Sprint 0
has no business features (Rule: do not add business logic ahead of a
planned sprint). Domain services — e.g. a future
`app/conversation/service.py` — will subclass `BaseService` and live
inside their own domain package, not here.
"""

from app.repositories.base import BaseRepository


class BaseService[RepositoryType: BaseRepository]:
    """Generic base class every domain service will subclass, starting Sprint 1."""

    def __init__(self, repository: RepositoryType) -> None:
        self.repository = repository
