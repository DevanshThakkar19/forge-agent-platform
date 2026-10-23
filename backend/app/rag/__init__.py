"""Hybrid retrieval: chunk, hash-embed, fuse vector and keyword hits, cite.

Postgres stores the vectors. The worker depends on Retriever, not on SQL.
"""
