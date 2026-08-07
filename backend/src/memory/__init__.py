"""EvoResearch Phase 3 - Research Memory system.

Clean, modular memory abstraction inspired by the MemCube concept:

    MemoryManager
        |-- MemoryExtractor     (turn a finished research run into Memories)
        |-- MySQLStore         (structured / canonical persistent memory)
        |-- ChromaStore        (semantic / vector retrieval layer)
        `-- EmbeddingService   (pluggable, env-configurable embedder)

The rest of the application talks ONLY to MemoryManager. MySQL is the source
of truth for structured metadata; ChromaDB is a retrieval index. Every layer
degrades gracefully so a memory failure never crashes the research pipeline.
"""

from src.memory.manager import MemoryManager, memory_manager

__all__ = ["MemoryManager", "memory_manager"]