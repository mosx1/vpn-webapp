# Project Rules

## Database Access

- All database queries must be executed only through repository methods.
- Repository usage must always be wrapped in a context manager (`with ...Repository() as repo:`).
- Direct SQL execution from routers, threads, methods, and other layers is not allowed.
