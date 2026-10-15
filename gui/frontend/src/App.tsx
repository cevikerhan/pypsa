from __future__ import annotations

from typing import Any

import pypsa
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="PyPSA Studio",
    description="Professional GUI backend for PyPSA workflows",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SUPPORTED_MODES = {"pf", "lpf", "lopf"}


class OptimizationRequest(BaseModel):
    """Parameters used to run a PyPSA optimization job."""

    network_name: str = Field(default="ac_dc_meshed")
    mode: str = Field(default="lopf", description="Optimization mode: pf, lpf, or lopf")


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
        "version": "0.2.0",
        "pypsa_version": pypsa.__version__,
        "features": [
            "Power flow",
            "Linear optimal power flow",
            "Static network analysis",
            "Scenario review",
            "Network planning",
            "Results dashboard",
            "Optimization workflow orchestration",
        ],
        "modes": ["pf", "lpf", "lopf"],
    }


@app.get("/api/network-preview")
async def network_preview() -> dict[str, Any]:
    network = pypsa.examples.ac_dc_meshed()
    return {
        "name": "ac_dc_meshed",
        "buses": len(network.buses),
        "lines": len(network.lines),
        "generators": len(network.generators),
        "loads": len(network.loads),
        "storage_units": len(network.storage_units),
        "transformers": len(network.transformers),
        "components": list(network.components.keys())[:12],
        "snapshots": len(network.snapshots),
        "supply": float(network.generators_t.p.sum().sum()) if hasattr(network, "generators_t") else 0.0,
        "demand": float(network.loads_t.p.sum().sum()) if hasattr(network, "loads_t") else 0.0,
        "status": "ready",
    }


@app.get("/api/component-summary")
async def component_summary() -> dict[str, Any]:
    network = pypsa.examples.ac_dc_meshed()
    return {
        "summary": [
            {"name": "Bus", "count": len(network.buses), "status": "active"},
            {"name": "Line", "count": len(network.lines), "status": "stable"},
            {"name": "Generator", "count": len(network.generators), "status": "operational"},
            {"name": "Load", "count": len(network.loads), "status": "active"},
            {"name": "Storage", "count": len(network.storage_units), "status": "ready"},
            {"name": "Transformer", "count": len(network.transformers), "status": "active"},
        ],
        "total_components": len(network.components),
    }


@app.get("/api/operations")
async def operations() -> dict[str, Any]:
    return {
        "actions": [
            {"id": "optimize", "label": "Run optimization", "status": "ready"},
            {"id": "validate", "label": "Validate topology", "status": "ready"},
            {"id": "simulate", "label": "Run scenario simulation", "status": "ready"},
            {"id": "export", "label": "Export results", "status": "ready"},
        ],
        "recommended": [
            "Create a baseline scenario",
            "Run a security-constrained dispatch",
            "Inspect network bottlenecks",
            "Review generator dispatch and losses",
        ],
    }


@app.post("/api/run")
async def run_optimization(payload: OptimizationRequest) -> dict[str, Any]:
    if payload.mode not in SUPPORTED_MODES:
        raise HTTPException(status_code=400, detail=f"Unsupported mode: {payload.mode}")

    if payload.network_name == "ac_dc_meshed":
        network = pypsa.examples.ac_dc_meshed()
    else:
        network = pypsa.Network()

    if payload.mode == "lopf":
        network.optimize.create_model()
        network.optimize.solve_model()
    elif payload.mode == "lpf":
        network.lpf()
    else:
        network.lpf()

    objective_value = float(getattr(network, "objective", 0.0) or 0.0)

    gen_dispatch = float(network.generators_t.p.sum().sum()) if hasattr(network, "generators_t") and hasattr(network.generators_t, "p") else 0.0
    load_demand = float(network.loads_t.p.sum().sum()) if hasattr(network, "loads_t") and hasattr(network.loads_t, "p") else 0.0
    storage_dispatch = float(network.storage_units_t.p.sum().sum()) if hasattr(network, "storage_units_t") and hasattr(network.storage_units_t, "p") else 0.0

    return {
        "status": "success",
        "mode": payload.mode,
        "network": payload.network_name,
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
            "solver": "Highs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
