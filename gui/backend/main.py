from __future__ import annotations

from typing import Any

import pypsa
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="PyPSA Studio",
    description="Professional GUI backend for PyPSA workflows",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OptimizationRequest(BaseModel):
    """Parameters used to run a PyPSA optimization job."""

    network_name: str = Field(default="ac_dc_meshed")
    mode: str = Field(default="lopf", description="Optimization mode: lpf, lopf, or pf")


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
        "version": "0.1.0",
        "pypsa_version": pypsa.__version__,
        "features": [
            "Power flow",
            "Linear optimal power flow",
            "Static network analysis",
            "Scenario review",
            "Network planning",
            "Results dashboard",
        ],
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
    }


@app.post("/api/run")
async def run_optimization(payload: OptimizationRequest) -> dict[str, Any]:
    if payload.network_name == "ac_dc_meshed":
        network = pypsa.examples.ac_dc_meshed()
    else:
        network = pypsa.Network()

    if payload.mode == "lopf":
        network.optimize.create_model()
        network.optimize.solve_model()
    elif payload.mode == "pf":
        network.lpf()
    else:
        network.lpf()

    objective_value = float(getattr(network, "objective", 0.0) or 0.0)

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
            {"label": "Load", "value": round(float(network.loads_t.p.sum().sum()), 2)},
            {"label": "Generation", "value": round(float(network.generators_t.p.sum().sum()), 2)},
            {"label": "Objective", "value": round(objective_value, 4)},
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
