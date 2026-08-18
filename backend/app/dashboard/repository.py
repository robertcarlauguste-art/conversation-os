from sqlalchemy.ext.asyncio import AsyncSession


class DashboardRepository:
    """
    Dashboard-specific data access.

    The dashboard currently aggregates data owned by other domain
    slices, so this repository stays intentionally thin until we
    introduce dashboard-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session