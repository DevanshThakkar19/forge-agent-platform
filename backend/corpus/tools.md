# MCP tools

web_search returns fixture snippets from a local index.
sql_query runs one read-only SELECT against the Postgres orders, docs, or cases table.
file_store reads and writes UTF-8 text inside a sandbox directory.
http_api serves stub routes such as /orders/1001 and /docs/overview.
None of these tools send a live network request in this slice.
