# server.py
# Microservicio de backtracking para coloreo de mapas.
# Ejecuta:  uvicorn server:app --reload --port 8000
# Reqs: pip install fastapi uvicorn pydantic[dotenv] python-multipart starlette-cors

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Tuple, Optional

app = FastAPI(title="Coloring API (Backtracking)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

# --------- Modelos ---------
class Edge(BaseModel):
    src: str
    dst: str

class SolveRequest(BaseModel):
    nodes: List[str]                 # ["A","B","C",...]
    edges: List[Edge]                # [{src:"A", dst:"B"}, ...]
    k_colors: int                    # 2..5
    order: Optional[str] = "degree"  # "degree" | "natural"

class Step(BaseModel):
    action: str   # try | assign | conflict | backtrack | done
    node: str
    color: Optional[int] = None
    partial: Optional[Dict[str, int]] = None

class SolveResponse(BaseModel):
    ok: bool
    colors: Dict[str, int]          # solución final (node -> colorId)
    steps: List[Step]               # trazas para animación
    message: str = ""

# --------- Backtracking ---------
def build_adj(nodes: List[str], edges: List[Edge]) -> Dict[str, List[str]]:
    adj = {u: [] for u in nodes}
    for e in edges:
        if e.src in adj and e.dst in adj and e.src != e.dst:
            if e.dst not in adj[e.src]:
                adj[e.src].append(e.dst)
            if e.src not in adj[e.dst]:
                adj[e.dst].append(e.src)
    return adj

def order_nodes(adj: Dict[str, List[str]], order: str) -> List[str]:
    if order == "degree":
        # mayor grado primero (heurística simple)
        return sorted(adj.keys(), key=lambda u: len(adj[u]), reverse=True)
    return list(adj.keys())

def compatible(u: str, color: int, colors: Dict[str, int], adj: Dict[str, List[str]]) -> bool:
    for v in adj[u]:
        if colors.get(v, -1) == color:
            return False
    return True

def color_graph_backtracking(adj: Dict[str, List[str]], k: int, order: str) -> Tuple[bool, Dict[str, int], List[Step]]:
    nodes = order_nodes(adj, order)
    colors: Dict[str, int] = {}
    steps: List[Step] = []

    def backtrack(i: int) -> bool:
        if i == len(nodes):
            steps.append(Step(action="done", node="", color=None, partial=colors.copy()))
            return True
        u = nodes[i]
        for c in range(k):
            steps.append(Step(action="try", node=u, color=c, partial=colors.copy()))
            if compatible(u, c, colors, adj):
                colors[u] = c
                steps.append(Step(action="assign", node=u, color=c, partial=colors.copy()))
                if backtrack(i + 1):
                    return True
                # deshacer
                steps.append(Step(action="backtrack", node=u, color=c, partial=colors.copy()))
                del colors[u]
            else:
                steps.append(Step(action="conflict", node=u, color=c, partial=colors.copy()))
        return False

    ok = backtrack(0)
    return ok, colors if ok else {}, steps

# --------- Endpoints ---------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/solve", response_model=SolveResponse)
def solve(req: SolveRequest):
    if not (2 <= req.k_colors <= 5):
        return SolveResponse(ok=False, colors={}, steps=[], message="k_colors debe estar entre 2 y 5.")
    if not req.nodes:
        return SolveResponse(ok=False, colors={}, steps=[], message="Debes enviar nodos.")
    adj = build_adj(req.nodes, req.edges)
    ok, colors, steps = color_graph_backtracking(adj, req.k_colors, req.order or "degree")
    msg = "Solución encontrada." if ok else "No existe coloreo con k colores."
    return SolveResponse(ok=ok, colors=colors, steps=steps, message=msg)
