"""Storage abstraction. The agent depends on these interfaces, not on the engine.

Local default: in-memory (``app.repositories.memory``). Production: Postgres with
RLS (``app.repositories.sql``). Selected by ``STORE_BACKEND`` via :mod:`app.deps`.
"""
