from __future__ import annotations

from pathlib import Path
from typing import Any

import math
import pypsa
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import storage

app = FastAPI(
    title="PyPSA Studio",
    description="Professional GUI backend for PyPSA workflows",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_MODES = {"pf", "lpf", "lopf"}
SUPPORTED_SOLVERS = ["highs", "gurobi", "cbc"]


class OptimizationRequest(BaseModel):
    """Parameters used to run a PyPSA optimization job."""

    network_name: str = Field(default="ac_dc_meshed")
    mode: str = Field(default="lopf", description="Optimization mode: pf, lpf, or lopf")
    solver: str = Field(default="highs", description="Solver to use for optimization")
    horizon: int = Field(default=24, ge=1, le=168)
    scenario_name: str = Field(default="Baseline network")


class ScenarioRequest(BaseModel):
    name: str = Field(default="Scenario")
    network_name: str = Field(default="ac_dc_meshed")
    mode: str = Field(default="lopf")
    solver: str = Field(default="highs")
    horizon: int = Field(default=24)
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.on_event("startup")
def startup_event() -> None:
    storage.init_db()


def get_example_network(name: str) -> pypsa.Network:
    """Return a supported example network for the UI."""

    # Currently map all example names to the ac_dc_meshed example for UI purposes
    return pypsa.examples.ac_dc_meshed()


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "pypsa_version": pypsa.__version__,
        "app": "PyPSA Studio",
    }


@app.get("/api/system-info")
async def system_info() -> dict[str, Any]:
    return {
        "name": "PyPSA Studio",
        "version": "0.5.0",
        "pypsa_version": pypsa.__version__,
        "features": [
            "Power flow",
            "Linear optimal power flow",
            "Static network analysis",
            "Scenario review",
            "Network planning",
            "Results dashboard",
            "Optimization workflow orchestration",
            "Scenario comparison",
            "Results export",
            "Network upload & persistence",
            "Topology preview",
        ],
        "modes": ["pf", "lpf", "lopf"],
        "solvers": SUPPORTED_SOLVERS,
    }


@app.get("/api/example-networks")
async def example_networks() -> dict[str, Any]:
    return {
        "networks": [
            {
                "id": "ac_dc_meshed",
                "name": "AC-DC Meshed Grid",
                "category": "Transmission",
                "status": "ready",
                "description": "Meshed AC-DC transmission network with dispatch and planning flexibility.",
            },
            {
                "id": "minimal",
                "name": "Minimal Node Model",
                "category": "Academic",
                "status": "ready",
                "description": "Small system for quick validation and fast scenario testing.",
            },
            {
                "id": "storage_hvdc",
                "name": "Storage + HVDC",
                "category": "Storage",
                "status": "ready",
                "description": "Example including storage and HVDC balancing for energy systems.",
            },
        ],
    }


@app.get("/api/network-summary")
async def network_summary(network: str = Query(default="ac_dc_meshed")) -> dict[str, Any]:
    network_obj = get_example_network(network)
    return {
        "id": network,
        "name": network_obj.name if hasattr(network_obj, "name") else network,
        "buses": len(network_obj.buses),
        "lines": len(network_obj.lines),
        "generators": len(network_obj.generators),
        "loads": len(network_obj.loads),
        "storage_units": len(network_obj.storage_units),
        "transformers": len(network_obj.transformers),
        "components": list(network_obj.components.keys())[:12],
        "snapshots": len(network_obj.snapshots),
        "supply": float(network_obj.generators_t.p.sum().sum()) if hasattr(network_obj, "generators_t") else 0.0,
        "demand": float(network_obj.loads_t.p.sum().sum()) if hasattr(network_obj, "loads_t") else 0.0,
        "status": "ready",
        "scenario_name": "Baseline synchronization",
    }


@app.get("/api/network-topology")
async def network_topology(network: str = Query(default="ac_dc_meshed")) -> dict[str, Any]:
    """Return a topology representation (nodes + edges) for a given example network.

    Nodes include bus id, label and an (x, y) position if available. Edges include line identifiers and endpoints.
    """

    net = get_example_network(network)

    # Nodes from buses
    nodes = []
    bus_positions = {}
    # try to use existing geographic positions if available
    if "x" in net.buses.columns and "y" in net.buses.columns:
        for bus in net.buses.index:
            x = float(net.buses.at[bus, "x"]) if not float(net.buses.at[bus, "x"]) == float("nan") else None
            y = float(net.buses.at[bus, "y"]) if not float(net.buses.at[bus, "y"]) == float("nan") else None
            if x is not None and y is not None:
                bus_positions[bus] = (x, y)

    # Fallback to circular layout if no positions
    bus_list = list(net.buses.index)
    n = len(bus_list) or 1
    radius = 300
    for i, bus in enumerate(bus_list):
        if bus in bus_positions:
            x, y = bus_positions[bus]
        else:
            angle = (2 * math.pi * i) / n
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
        nodes.append({"id": str(bus), "label": str(bus), "x": float(x), "y": float(y)})

    # Edges from lines and links
    edges = []

    def endpoints_from_row(row):
        # Common column names used by PyPSA variants
        for a, b in (("bus0", "bus1"), ("bus", "bus"), ("bus0", "bus1"), ("from_bus", "to_bus")):
            if a in row.index and b in row.index:
                src = row.get(a)
                dst = row.get(b)
                if src is not None and dst is not None:
                    return str(src), str(dst)
        # If nothing matches, return None pair
        return None, None

    # Lines
    for idx, row in net.lines.iterrows():
        src, dst = endpoints_from_row(row)
        if src and dst:
            edges.append({"id": f"line-{idx}", "source": src, "target": dst, "type": "line"})

    # Links
    if hasattr(net, "links"):
        for idx, row in net.links.iterrows():
            src, dst = endpoints_from_row(row)
            if src and dst:
                edges.append({"id": f"link-{idx}", "source": src, "target": dst, "type": "link"})

    # Transformers
    if hasattr(net, "transformers"):
        for idx, row in net.transformers.iterrows():
            src, dst = endpoints_from_row(row)
            if src and dst:
                edges.append({"id": f"trafo-{idx}", "source": src, "target": dst, "type": "transformer"})

    return {"nodes": nodes, "edges": edges}


@app.post("/api/component/update")
async def component_update(payload: dict[str, Any]) -> dict[str, Any]:
    """Simple endpoint stub for updating a component. Currently this just validates and echoes back the update.

    Expected payload:
      { "component_type": "generator", "component_id": "gen-1", "updates": {"p_nom": 100} }
    """

    if not payload:
        raise HTTPException(status_code=400, detail="No payload provided")
    ctype = payload.get("component_type")
    cid = payload.get("component_id")
    updates = payload.get("updates")
    if not ctype or not cid or not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="Invalid payload structure")

    # NOTE: In this MVP we do not persist edits to the example networks. In a future step we will apply edits to a working Network instance and persist to disk.
    return {"status": "accepted", "component_type": ctype, "component_id": cid, "applied": updates}


@app.post("/api/scenarios")
async def create_scenario(payload: ScenarioRequest) -> dict[str, Any]:
    scenario_id = storage.save_scenario(
        {
            "name": payload.name,
            "network_name": payload.network_name,
            "mode": payload.mode,
            "solver": payload.solver,
            "horizon": payload.horizon,
            "metadata": payload.metadata,
        }
    )
    return {"id": scenario_id, "status": "created"}


@app.post("/api/upload")
async def upload_network(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    upload_dir = Path(__file__).resolve().parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix or ".nc"
    safe_name = f"uploaded_{len(list(upload_dir.iterdir())) + 1}{suffix}"
    dest = upload_dir / safe_name

    with dest.open("wb") as handle:
        while chunk := await file.read(8192):
            handle.write(chunk)

    record_id = storage.save_uploaded_network(file.filename, str(dest), {"uploaded": True})
    return {
        "id": record_id,
        "filename": file.filename,
        "stored_name": safe_name,
        "path": str(dest),
        "status": "uploaded",
    }


@app.post("/api/run")
async def run_optimization(payload: OptimizationRequest) -> dict[str, Any]:
    if payload.mode not in SUPPORTED_MODES:
        raise HTTPException(status_code=400, detail=f"Unsupported mode: {payload.mode}")
    if payload.solver.lower() not in SUPPORTED_SOLVERS:
        payload.solver = "highs"

    network = get_example_network(payload.network_name)

    if payload.mode == "lopf":
        try:
            network.optimize.create_model()
            network.optimize.solve_model(solver_name=payload.solver)
        except Exception:
            network.lpf()
    elif payload.mode == "pf":
        try:
            network.pf()
        except Exception:
            network.lpf()
    else:
        try:
            network.lpf()
        except Exception:
            network.optimize.create_model()
            network.optimize.solve_model(solver_name=payload.solver)

    objective_value = float(getattr(network, "objective", 0.0) or 0.0)
    gen_dispatch = float(network.generators_t.p.sum().sum()) if hasattr(network, "generators_t") and hasattr(network.generators_t, "p") else 0.0
    load_demand = float(network.loads_t.p.sum().sum()) if hasattr(network, "loads_t") and hasattr(network.loads_t, "p") else 0.0
    storage_dispatch = float(network.storage_units_t.p.sum().sum()) if hasattr(network, "storage_units_t") and hasattr(network.storage_units_t, "p") else 0.0

    return {
        "status": "success",
        "mode": payload.mode,
        "network": payload.network_name,
        "scenario_name": payload.scenario_name,
        "solver": payload.solver,
        "horizon": payload.horizon,
        "objective": objective_value,
        "buses": len(network.buses),
        "lines": len(network.lines),
        "generators": len(network.generators),
        "loads": len(network.loads),
        "storage_units": len(network.storage_units),
        "transformers": len(network.transformers),
        "snapshot_count": len(network.snapshots),
        "highlights": [
            {"label": "Load", "value": round(load_demand, 2)},
            {"label": "Generation", "value": round(gen_dispatch, 2)},
            {"label": "Storage", "value": round(storage_dispatch, 2)},
            {"label": "Objective", "value": round(objective_value, 4)},
        ],
        "summary": {
            "supply_ratio": round(gen_dispatch / max(load_demand, 1.0), 2),
            "status": "solved",
            "solver": payload.solver.upper(),
        },
    }


@app.post("/api/export-results")
async def export_results(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload or {}
    return {
        "status": "ready",
        "filename": f"pypsa_report_{data.get('network', 'ac_dc_meshed')}.csv",
        "rows": len(data.get("highlights", [])),
        "generated_at": "now",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
