from .chat_session import ChatSession
from .session_manager import SessionManager
from .repository import SessionRepository
from persistence.filesystem_repository import FileSystemSessionRepository

# Global instances, managed here as the Composition Root
_repository: SessionRepository | None = None
_session_manager: SessionManager | None = None

def _initialize_dependencies():
    """Initializes and wires up all dependencies."""
    global _repository, _session_manager
    if _repository is None:
        _repository = FileSystemSessionRepository()

    if _session_manager is None:
        _session_manager = SessionManager(_repository)

def get_session_manager() -> SessionManager:
    """Returns the global session manager instance."""
    _initialize_dependencies()
    return _session_manager

def get_repository() -> SessionRepository:
    """Returns the global repository instance."""
    _initialize_dependencies()
    return _repository

# Export public classes and functions
__all__ = ['ChatSession', 'SessionManager', 'get_session_manager', 'get_repository']
