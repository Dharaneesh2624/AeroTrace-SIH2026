"""Reduced-order identities and an explicitly uncalibrated bench simulator."""
from dataclasses import asdict, dataclass
import math

@dataclass(frozen=True)
class EngineParameters:
    bore_m: float = .083
    stroke_m: float = .092
    cylinders: int = 4
    reduction_ratio: float = 1.69
    gas_constant_air: float = 287.05
    volumetric_efficiency: float = .85  # assumed, NOT an AE300 compressor/VE map
    ve_bounds: tuple = (.65, 1.0)

    @property
    def displacement_m3(self):
        return math.pi/4 * self.bore_m**2 * self.stroke_m * self.cylinders

def derived(values, parameters=None):
    p = parameters or EngineParameters()
    result = {}
    rpm = values.get("propeller_rpm")
    manifold = values.get("boost_pa")
    ambient = values.get("ambient_pa")
    intake = values.get("intake_c")
    if rpm is not None:
        crank = rpm * p.reduction_ratio
        result["crankshaft_rpm"] = {"value": crank, "unit": "rpm", "quality": "derived_ratio"}
        result["mean_piston_speed_m_s"] = {"value": 2*p.stroke_m*crank/60, "unit": "m/s", "quality": "derived_geometry"}
        result["firing_frequency_hz"] = {"value": crank/120*p.cylinders, "unit": "Hz", "quality": "kinematic_not_measured_vibration"}
    if manifold is not None and ambient is not None and ambient > 0:
        result["manifold_ambient_ratio"] = {"value": manifold/ambient, "unit": "1", "quality": "derived_absolute_pressures"}
        result["boost_gauge_pa"] = {"value": manifold-ambient, "unit": "Pa", "quality": "derived"}
    if manifold is not None and intake is not None:
        density = manifold/(p.gas_constant_air*(intake+273.15))
        result["intake_density_kg_m3"] = {"value": density, "unit": "kg/m3", "quality": "ideal_gas_estimate"}
        if rpm is not None:
            base = density*p.displacement_m3*rpm*p.reduction_ratio/120
            result["airflow_kg_s"] = {"value": base*p.volumetric_efficiency, "unit": "kg/s",
                "quality": "assumed_volumetric_efficiency", "assumption_range": [base*v for v in p.ve_bounds],
                "note": "Range is parameter sensitivity, not a statistical confidence interval"}
    # Load is NOT assumed to be torque or power. Missing channels remain unavailable.
    for name, why in {"shaft_power_kw": "Engine-load scale is not a verified power map",
                      "fuel_flow_l_h": "No measured fuel-flow channel in the base log",
                      "brake_efficiency": "Needs measured power and fuel mass flow",
                      "egt_c": "Not recorded", "cht_c": "Coolant is not cylinder-head temperature"}.items():
        result[name] = {"value": None, "quality": "unavailable", "reason": why}
    return result

@dataclass
class BenchParameters:
    # Illustrative constants, not fitted or validated against AE300.
    rated_power_kw: float = 123.5
    brake_efficiency: float = .34
    fuel_lhv_j_kg: float = 43e6
    fuel_density_kg_l: float = .80
    coolant_heat_fraction: float = .20
    oil_heat_fraction: float = .06
    coolant_capacity_j_k: float = 75000
    oil_capacity_j_k: float = 35000
    coolant_conductance_w_k: float = 1200
    oil_conductance_w_k: float = 420
    thermal_coupling_w_k: float = 100
    boost_time_constant_s: float = 2.5

def simulate_bench(segments, initial_c=25.0, parameters=None):
    """Open-loop illustrative two-node energy balance, not ECU/flight performance.

    User controls requested shaft power directly; no inferred throttle-power law.
    Integration uses <=0.25 s explicit steps and outputs at 1 Hz.
    """
    p = parameters or BenchParameters()
    coolant = oil = initial_c
    boost = 101325.0
    t = 0
    rows = []
    for segment in segments:
        duration = segment["duration_s"]
        power = segment["shaft_power_kw"]
        ambient = segment.get("ambient_c", 25.0)
        pressure = segment.get("ambient_pa", 101325.0)
        cooling = segment.get("cooling_factor", 1.0)
        if not isinstance(duration, int) or not 1 <= duration <= 3600:
            raise ValueError("Each bench segment needs integer duration 1..3600 seconds")
        if not 0 <= power <= p.rated_power_kw or not -30 <= ambient <= 55:
            raise ValueError("Requested bench power/temperature outside demonstration domain")
        if not 30000 <= pressure <= 110000 or not .2 <= cooling <= 1.5:
            raise ValueError("Bench pressure/cooling outside demonstration domain")
        if t + duration > 7200:
            raise ValueError("Maximum bench simulation is 7200 seconds")
        fuel_w = power*1000/p.brake_efficiency
        fuel_l_h = fuel_w/p.fuel_lhv_j_kg/p.fuel_density_kg_l*3600
        target_boost = pressure*(1 + 1.25*power/p.rated_power_kw)
        for _ in range(duration):
            for _ in range(4):
                coupling = p.thermal_coupling_w_k*(coolant-oil)
                dc = (p.coolant_heat_fraction*fuel_w - cooling*p.coolant_conductance_w_k*(coolant-ambient) - coupling)/p.coolant_capacity_j_k
                do = (p.oil_heat_fraction*fuel_w - cooling*p.oil_conductance_w_k*(oil-ambient) + coupling)/p.oil_capacity_j_k
                coolant += .25*dc
                oil += .25*do
                boost += .25*(target_boost-boost)/p.boost_time_constant_s
            t += 1
            rows.append({"time_s": t, "coolant_c": coolant, "oil_c": oil, "boost_pa": boost,
                         "assumed_shaft_power_kw": power, "synthetic_fuel_flow_l_h": fuel_l_h})
    return {"quality": "uncalibrated_synthetic_bench_only", "parameters": asdict(p), "samples": rows,
            "limitations": "No combustion solver, turbo map, airspeed cooling, altitude derating, safety envelope or reliability prediction"}

