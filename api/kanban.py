import json
import os
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request

KANBAN_PATH = "./kanban.json"

# --- Persistence Helpers ---
def load_kanban():
    if os.path.exists(KANBAN_PATH):
        try:
            with open(KANBAN_PATH, "r") as f:
                data = json.load(f)
            # Ensure all columns exist
            for col in ["todo", "doing", "done"]:
                if col not in data:
                    data[col] = []
            return data
        except Exception:
            pass  # Fall through and re-init if JSON is bad
    return {"todo": [], "doing": [], "done": []}

def save_kanban(board):
    with open(KANBAN_PATH, "w") as f:
        json.dump(board, f, indent=2)

# --- In-memory state (auto-loaded) ---
KANBAN_BOARD = load_kanban()

# --- API Handlers ---
async def get_kanban(request: Request):
    """Return the current state of the Kanban board."""
    return JSONResponse({"columns": KANBAN_BOARD})

async def add_card(request: Request):
    """Add a new card to a specified column."""
    data = await request.json()
    column = data.get("column")
    card = data.get("card")
    if column not in KANBAN_BOARD or not card:
        return JSONResponse({"error": "Invalid column or card."}, status_code=400)
    KANBAN_BOARD[column].append(card)
    save_kanban(KANBAN_BOARD)
    return JSONResponse({"columns": KANBAN_BOARD})

async def move_card(request: Request):
    """Move a card from one column to another."""
    data = await request.json()
    from_column = data.get("from")
    to_column = data.get("to")
    card = data.get("card")
    if from_column not in KANBAN_BOARD or to_column not in KANBAN_BOARD or not card:
        return JSONResponse({"error": "Invalid column or card."}, status_code=400)
    try:
        KANBAN_BOARD[from_column].remove(card)
        KANBAN_BOARD[to_column].append(card)
        save_kanban(KANBAN_BOARD)
    except ValueError:
        return JSONResponse({"error": "Card not found in from column."}, status_code=404)
    return JSONResponse({"columns": KANBAN_BOARD})

async def delete_card(request: Request):
    """Delete a card from a specified column."""
    data = await request.json()
    column = data.get("column")
    card = data.get("card")
    if column not in KANBAN_BOARD or not card:
        return JSONResponse({"error": "Invalid column or card."}, status_code=400)
    try:
        KANBAN_BOARD[column].remove(card)
        save_kanban(KANBAN_BOARD)
    except ValueError:
        return JSONResponse({"error": "Card not found."}, status_code=404)
    return JSONResponse({"columns": KANBAN_BOARD})

# --- Kanban API Route List ---
routes = [
    Route("/api/kanban", endpoint=get_kanban),
    Route("/api/kanban/add", endpoint=add_card, methods=["POST"]),
    Route("/api/kanban/move", endpoint=move_card, methods=["POST"]),
    Route("/api/kanban/delete", endpoint=delete_card, methods=["POST"]),
]
