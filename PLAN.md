# Kanban Board Plan for j4ne

## Overview
Add a simple Kanban Board feature to the existing j4ne project using the existing Starlette-based web server (see `j4ne.py`). The Kanban board will have a backend REST API (Python/Starlette) and a simple frontend (HTML/JavaScript, served from `/static`).

## Data Model
- Maintain the Kanban board state as an in-memory Python dictionary (persisted to a JSON file).
- Board composed of columns (e.g., 'To Do', 'In Progress', 'Done'), each with cards (tasks).
- Example:
```python
kanban_board = {
    "columns": [
        {"id": "todo", "title": "To Do", "cards": [
            {"id": "1", "title": "Sample Task", "description": "Do this thing!"},
        ]},
        {"id": "inprogress", "title": "In Progress", "cards": []},
        {"id": "done", "title": "Done", "cards": []}
    ]
}
```

## API Endpoints
- `GET /api/kanban` — Get current board state
- `POST /api/card` — Add card
- `PUT /api/card/{card_id}` — Edit/move card
- `DELETE /api/card/{card_id}` — Delete card
- (Expand as needed)

## Backend: Python Handlers
- Place API handler logic in `api/kanban.py` (new file).
- Expose as Starlette routes for import/registration in `j4ne.py`.
- Access and persist kanban state from/to a JSON file between restarts.
- Register routes in `j4ne.py` using:
  ```python
  from api.kanban import routes as kanban_routes
  routes = [
      ...existing_routes,
      *kanban_routes,
  ]
  ```
- Keep route registration in `j4ne.py`, but all Kanban logic in `api/kanban.py` for modularity.

## Frontend
- Place assets in `/static/` (e.g., `index.html`, `kanban.js`, `style.css`).
- Build a minimal HTML/JS UI for interacting with the board via REST API.

## Example File Tree
```
j4ne.py
api/
  kanban.py   # <-- new: all kanban-related handlers and route definitions
static/
  index.html
  kanban.js
  style.css
kanban_data.json
PLAN.md
```

## Next Steps
1. Scaffold `api/kanban.py` with endpoints and state logic.
2. Update `j4ne.py` to import and register Kanban routes.
3. Build out `/static/` frontend mockup.
4. Implement JSON-based persistence for Kanban data.
