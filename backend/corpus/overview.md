# Forge

Forge routes a goal through a planner, a worker, and a critic.
The worker calls MCP tool servers and retrieves cited chunks from Postgres.
Citations in an answer have to come back from a tool or from this corpus.
