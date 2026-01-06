from session.repository import SessionRepository
from cli import console

def list_sessions_command(repository: SessionRepository):
    """
    Displays a formatted list of available sessions using the provided repository.

    Args:
        repository: An object that implements the SessionRepository protocol.
    """
    sessions = repository.list_sessions()
    if sessions:
        console.print_help("\n--- Dostępne zapisane sesje (ID, Tytuł) ---")
        for session in sessions:
            session_id = session.get('id')
            session_title = session.get('title', '(brak tytułu)')
            if session.get('error'):
                console.print_error(f"- ID: {session_id} | Tytuł: {session_title} ({session['error']})")
            else:
                console.print_help(f"- ID: {session_id} | Tytuł: {session_title} (Wiadomości: {session['messages_count']}, Ost. aktywność: {session['last_activity']})")
        console.print_help("------------------------------------")
    else:
        console.print_help("\nBrak zapisanych sesji.")