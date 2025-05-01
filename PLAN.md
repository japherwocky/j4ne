# Kanban Project Plan

## Completed

- Backend persists kanban state in './kanban.json'.
- API endpoints for getting board state, adding, moving, and deleting cards implemented.
- Minimal frontend in static/index.html:
    - Fetches board from /api/kanban
    - Displays columns: todo, doing, done
    - Allows adding cards
    - Allows moving cards between columns (buttons & drag-and-drop)
    - Allows deleting cards
- Static file serving from /static
- / now redirects to Kanban board

## Next Steps

- Polish UI/UX if desired
- Add more robust error and edge-case handling

## Optional/Future Work

- Add authentication
- Further improve UI/UX (animations, enhanced drag-and-drop, etc.)
- Concurrency/real-time board updates
- Additional features (card details, attachments, etc.)
