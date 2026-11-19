import json
import math
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# CAREER VENTURE LAB: NUR-2 (Precalculus | Nurse-led Health Education Simulation)
# Stage 1 Deliverable: Inputs, Math Panel, Dated Ledger, Save/Load JSON & Fixtures
# ==============================================================================

st.set_page_config(
    page_title="Career Venture Lab | NUR-2 Precalculus Simulator",
    layout="wide",
)

CENT = Decimal("0.01")


def money(val) -> Decimal:
    """Convert numeric input to exact 2-decimal USD using Decimal."""
    return Decimal(str(val)).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt_usd(val: Decimal) -> str:
    return f"${money(val):,.2f}"


# ------------------------------------------------------------------------------
# DETERMINISTIC NUR-2 SIMULATION & PRECALCULUS ENGINE
# ------------------------------------------------------------------------------


def compute_nur_month(
    *,
    requested: int,
    base_price: Decimal,
    staff_hours: Decimal,
    hours_per_unit: Decimal,
    venue_seats: int,
    no_show_rate: Decimal,
    var_cost_per_unit: Decimal,
    fixed_cost_total: Decimal,
    marketing_cost: Decimal,
    opening_cash: Decimal,
    refund_amount: Decimal = Decimal("0.00"),
    loan_cash: Decimal = Decimal("0.00"),
    loan_principal: Decimal = Decimal("0.00"),
    interest: Decimal = Decimal("0.00"),
    additional_capex: Decimal = Decimal("0.00"),
    new_owner_cash: Decimal = Decimal("0.00"),
    capacity_override: int | None = None,
) -> dict:
    """
    Deterministic monthly algorithm for NUR package (Handbook p. 84):
      booked = min(requested, floor(staff_hours / hours_per_unit), venue_seats)
      attended = floor(booked * (1 - no_show_rate))
      sold = attended
    In Fixture-Test Mode, capacity_override replaces derived capacity.
    """
    if capacity_override is not None:
        derived_capacity = int(capacity_override)
    else:
        staff_cap = int(math.floor(staff_hours / hours_per_unit)) if hours_per_unit > 0 else 0
        derived_capacity = max(0, min(staff_cap, int(venue_seats)))

    booked = max(0, min(int(requested), derived_capacity))
    attended = int(math.floor(Decimal(booked) * (Decimal("1.0") - no_show_rate)))
    sold = attended
    unserved_demand = max(0, int(requested) - booked)
    no_show_count = max(0, booked - attended)

    revenue = money(Decimal(sold) * base_price - refund_amount)
    variable_expense = money(Decimal(sold) * var_cost_per_unit)
    fixed_expense = money(fixed_cost_total)
    marketing_expense = money(marketing_cost)

    operating_profit = money(revenue - variable_expense - fixed_expense - marketing_expense)
    net_profit = money(operating_profit - interest)
    total_expense = money(variable_expense + fixed_expense + marketing_expense + interest)

    ending_cash = money(
        opening_cash
        + revenue
        - variable_expense
        - fixed_expense
        - marketing_expense
        - interest
        - loan_principal
        - additional_capex
        + new_owner_cash
        + loan_cash
    )

    educator_hours_used = (Decimal(attended) * hours_per_unit).quantize(Decimal("0.01"))
    educator_utilization = (
        float((educator_hours_used / staff_hours) * 100) if staff_hours > 0 else 0.0
    )

    return {
        "derived_capacity": derived_capacity,
        "requested": int(requested),
        "booked": booked,
        "attended": attended,
        "sold": sold,
        "unserved_demand": unserved_demand,
        "no_show_count": no_show_count,
        "revenue": revenue,
        "variable_expense": variable_expense,
        "fixed_expense": fixed_expense,
        "marketing_expense": marketing_expense,
        "interest": money(interest),
        "total_expense": total_expense,
        "operating_profit": operating_profit,
        "net_profit": net_profit,
        "opening_cash": money(opening_cash),
        "ending_cash": ending_cash,
        "educator_hours_used": educator_hours_used,
        "educator_utilization_pct": round(educator_utilization, 2),
    }


def precalc_demand(price: float, d0: float = 80.0, p0: float = 25.0) -> float:
    """q(p) = max(0, 2*D0 - (D0/p0)*p) -> max(0, 160 - 3.2p) at baseline."""
    slope = d0 / p0
    return max(0.0, 2.0 * d0 - slope * price)


def precalc_seasonal_demand(month_t: int, d0: float = 80.0) -> float:
    """
    Precalculus Advanced Extension (Handbook p. 69):
    D(t) = D0 * (1 + 0.20 * sin(2*pi*(t - 1)/12))
    Peak at t = 4 (1.20 * D0 = 96), minimum at t = 10 (0.80 * D0 = 64).
    """
    return d0 * (1.0 + 0.20 * math.sin(2.0 * math.pi * (month_t - 1) / 12.0))


# ------------------------------------------------------------------------------
# STATE INITIALIZATION & SNAPSHOT CONTRACT (Handbook p. 58 & p. 83)
# ------------------------------------------------------------------------------


def default_state() -> dict:
    return {
        "team_id": "TEAM-NUR2",
        "course": "Precalculus",
        "pathway_id": "NUR-2",
        "business_name": "Nurse-led Health Education Simulation",
        "selected_level": "Advanced",
        "teacher_approved_skills": [
            "Rational Average Cost & Asymptotes",
            "Function Composition & Domain Clipping",
            "Seasonal Trigonometric Demand Modeling",
        ],
        "snapshot_id": "SNAP-0001",
        "state_version": 1,
        "simulation_date": "2027-01-31",
        "base_period": "Monthly",
        "working_days": 20,
        "currency": "USD",
        "run_mode": "Normal Mode",
        "random_seed": 2027,
        # Startup financing & opening balances (Handbook p. 83)
        "startup": {
            "owner_contribution": "6000.00",
            "equipment_assets": "1500.00",
            "pre_opening_expense": "500.00",
            "opening_inventory": "0.00",
            "post_startup_cash": "4000.00",
            "retained_earnings": "-500.00",
        },
        # Editable baseline inputs (Handbook p. 83)
        "inputs": {
            "base_price": "25.00",
            "D0": 80,
            "requested": 80,
            "staff_hours": "30.0",
            "hours_per_unit": "0.5",
            "venue_seats": 60,
            "no_show_rate": "0.00",
            "satisfaction_mean": "4.0",
            "opening_cash": "4000.00",
            "marketing_ad_cost": "0.00",
            "refund_amount": "0.00",
            "loan_cash": "0.00",
            "loan_principal": "0.00",
            "interest": "0.00",
            "additional_capex": "0.00",
        },
        # Editable cost lines (Handbook p. 83)
        "cost_lines": {
            "variable": {
                "educator_delivery": "2.00",
                "materials": "2.00",
                "cleaning_consumables": "1.00",
            },
            "fixed": {
                "venue": "250.00",
                "scheduling_software": "100.00",
                "accessibility_support": "200.00",
                "admin_insurance_assumption": "150.00",
            },
        },
        "offerings": [
            {
                "offering_id": "OFF-01",
                "name": "General wellness education workshop",
                "unit": "workshop seat",
                "price": "25.00",
                "primary": True,
            },
            {
                "offering_id": "OFF-02",
                "name": "Caregiver information session",
                "unit": "session seat",
                "price": "25.00",
                "primary": False,
            },
            {
                "offering_id": "OFF-03",
                "name": "First-aid awareness demonstration",
                "unit": "demo seat",
                "price": "25.00",
                "primary": False,
            },
        ],
        "executed_run_ids": [],
        "ledger": [],
        "decisions": [],
        "pending_recommendations": [],
        "cross_course_notes": [
            {
                "subject": "Health / English",
                "concept": "Source Evaluation & Plain-Language Flyer",
                "evidence": "Evaluated official health-education source; nonclinical education only.",
            },
            {
                "subject": "Computer Science",
                "concept": "Idempotent Ledger & Schema Validation",
                "evidence": "Duplicate run_id guard and strict state_version JSON import checks.",
            },
        ],
    }


if "sim_state" not in st.session_state:
    st.session_state.sim_state = default_state()

state = st.session_state.sim_state


def reset_to_opening_state():
    current_team = state["team_id"]
    current_level = state["selected_level"]
    fresh = default_state()
    fresh["team_id"] = current_team
    fresh["selected_level"] = current_level
    st.session_state.sim_state = fresh


# ------------------------------------------------------------------------------
# SIDEBAR: GOVERNANCE, MODE SWITCH, SAVE / LOAD JSON & DUPLICATE PROTECTION
# ------------------------------------------------------------------------------

with st.sidebar:
    st.title("NUR-2 Control Panel")
    st.caption("Simulation only: fictional education business, no clinical diagnosis or patient data.")

    state["team_id"] = st.text_input("Team ID", value=state["team_id"])
    st.text_input("Course & Pathway", value=f"{state['course']} | {state['pathway_id']}", disabled=True)

    # Challenge Level Switcher (Handbook p. 6: requires teacher approval)
    new_level = st.selectbox(
        "Challenge Level (Teacher Approved)",
        options=["Foundation", "Applied", "Advanced"],
        index=["Foundation", "Applied", "Advanced"].index(state["selected_level"]),
    )
    if new_level != state["selected_level"]:
        st.warning(
            f"Level preview changed from {state['selected_level']} to {new_level}. "
            "Confirm teacher approval before saving."
        )
        if st.button("Confirm Teacher Approval & Save Level"):
            state["selected_level"] = new_level
            state["state_version"] += 1
            state["snapshot_id"] = f"SNAP-{state['state_version']:04d}"
            st.rerun()

    st.divider()

    # Normal Mode vs. Fixture-Test Mode (Handbook p. 87)
    mode = st.radio(
        "Simulation Mode",
        options=["Normal Mode", "Fixture-Test Mode"],
        index=0 if state["run_mode"] == "Normal Mode" else 1,
    )
    state["run_mode"] = mode
    if mode == "Fixture-Test Mode":
        st.warning(
            "FIXTURE-TEST MODE ACTIVE: Uses capacity_override from monthly_fixture.csv. "
            "Do not mix fixture runs with normal ledger runs."
        )

    st.markdown(f"**Snapshot ID:** `{state['snapshot_id']}`")
    st.markdown(f"**State Version:** `v{state['state_version']}`")
    st.markdown(f"**Current Cash:** `{fmt_usd(money(state['inputs']['opening_cash']))}`")

    if st.button("Reset to Opening State ($4,000 Cash)", use_container_width=True):
        reset_to_opening_state()
        st.rerun()

    st.divider()
    st.subheader("Save / Restore JSON State")
    snapshot_json = json.dumps(state, indent=2)
    st.download_button(
        label="Export Snapshot JSON",
        data=snapshot_json,
        file_name=f"{state['team_id']}_{state['pathway_id']}_v{state['state_version']}.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded_json = st.file_uploader("Import Snapshot / Recommendation JSON", type=["json"])
    if uploaded_json is not None:
        try:
            incoming = json.loads(uploaded_json.read().decode("utf-8"))
            if incoming.get("team_id") != state["team_id"]:
                st.error(
                    f"IMPORT REJECTED: Team ID mismatch (expected `{state['team_id']}`, "
                    f"got `{incoming.get('team_id')}`)."
                )
            elif incoming.get("pathway_id") != state["pathway_id"]:
                st.error(
                    f"IMPORT REJECTED: Pathway mismatch (expected `{state['pathway_id']}`, "
                    f"got `{incoming.get('pathway_id')}`)."
                )
            elif int(incoming.get("state_version", -1)) < int(state["state_version"]):
                st.error(
                    f"IMPORT REJECTED: Stale state version `v{incoming.get('state_version')}` "
                    f"cannot overwrite current `v{state['state_version']}`."
                )
            else:
                if st.button("Approve & Restore Imported JSON", use_container_width=True):
                    st.session_state.sim_state = incoming
                    st.success("Snapshot restored and verified.")
                    st.rerun()
        except Exception as exc:
            st.error(f"Invalid JSON file: {exc}")


# ------------------------------------------------------------------------------
# HELPER: CALCULATE CURRENT PREVIEW FROM INPUTS
# ------------------------------------------------------------------------------

inp = state["inputs"]
var_total = sum(money(v) for v in state["cost_lines"]["variable"].values())
fix_total = sum(money(v) for v in state["cost_lines"]["fixed"].values())

preview = compute_nur_month(
    requested=int(inp["requested"]),
    base_price=money(inp["base_price"]),
    staff_hours=Decimal(str(inp["staff_hours"])),
    hours_per_unit=Decimal(str(inp["hours_per_unit"])),
    venue_seats=int(inp["venue_seats"]),
    no_show_rate=Decimal(str(inp["no_show_rate"])),
    var_cost_per_unit=var_total,
    fixed_cost_total=fix_total,
    marketing_cost=money(inp["marketing_ad_cost"]),
    opening_cash=money(inp["opening_cash"]),
    refund_amount=money(inp["refund_amount"]),
    loan_cash=money(inp["loan_cash"]),
    loan_principal=money(inp["loan_principal"]),
    interest=money(inp["interest"]),
    additional_capex=money(inp["additional_capex"]),
)


# ------------------------------------------------------------------------------
# MAIN NAVIGATION TABS (STAGE 1 CORE MODULES + STAGE 2/3 PLACEHOLDERS)
# ------------------------------------------------------------------------------

tabs = st.tabs(
    [
        "Overview",
        "Inputs & Funding",
        "Math Skills & Levels (Precalculus)",
        "Operations & Customers",
        "Finance & Dated Ledger",
        "Fixture & Acceptance Tests",
        "Stage 2-4 Modules (Status)",
    ]
)

# ==============================================================================
# TAB 1: OVERVIEW
# ==============================================================================
with tabs[0]:
    st.header("Overview — Nurse-led Health Education Simulation (NUR-2)")
    st.info(
        "**Nonclinical Education Scope:** This simulation models fictional general wellness workshops, "
        "caregiver information sessions, and first-aid awareness demonstrations. It does not diagnose, "
        "treat, collect real patient data, or infer clinical health outcomes from attendance."
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Monthly Capacity", f"{preview['derived_capacity']} seats")
    k2.metric("Projected Attended (Sold)", f"{preview['attended']} seats", f"Booked: {preview['booked']}")
    k3.metric("Projected Revenue", fmt_usd(preview["revenue"]))
    k4.metric("Operating Profit", fmt_usd(preview["operating_profit"]))
    k5.metric("Ending Cash (Preview)", fmt_usd(preview["ending_cash"]))

    st.divider()
    st.subheader("Persistent Math Panel Summary")
    m1, m2 = st.columns([2, 1])
    with m1:
        st.markdown(
            f"""
            - **Selected Course & Level:** `{state['course']}` — **`{state['selected_level']}`**
            - **Primary Offering:** General wellness education workshop (`$25.00 / seat`)
            - **Core Rational Cost Model:** $A(q) = \frac{{{fix_total} + {var_total}q}}{{q}}$ on $0 < q \le {preview['derived_capacity']}$
            - **Linear Demand Model:** $q(p) = \max(0, 160 - 3.2p)$ with capacity cap $s(p) = \min({preview['derived_capacity']}, q(p))$
            - **Advanced Extension:** $D(t) = {inp['D0']}\left(1 + 0.20\sin\left(\frac{{2\pi(t-1)}}{{12}}\right)\right)$ for month $t \in [1, 12]$
            """
        )
    with m2:
        st.markdown("**System Operating Loop**")
        st.markdown(
            "1. Save snapshot version\n"
            "2. Run deterministic model\n"
            "3. Export JSON to AI specialists\n"
            "4. Reviewer & student check math\n"
            "5. Approve & advance ledger once"
        )

    st.subheader("System Dependency Map")
    st.code(
        "[Marketing Studio (Costed Campaign)] ---> [Requested Demand q(p) / D(t)]\n"
        "                                                  |\n"
        "                                                  v\n"
        "[Inputs: Staff Hours & Venue Seats] ---> [Operations Capacity & No-Show Filter]\n"
        "                                                  |
"
        "                                                  v\n"
        "[Finance Ledger: Revenue, Costs, Cash] <--- [Attended Seats (Sold)]\n"
        "         |\n"
        "         +---> [Independent Reviewer & Human Approval Gate] ---> [Next State Version]",
        language="text",
    )

# ==============================================================================
# TAB 2: INPUTS & FUNDING
# ==============================================================================
with tabs[1]:
    st.header("Inputs, Startup Financing & Cost Lines")
    st.caption("Changes here update scenario previews immediately. Commit to the dated ledger in the Finance tab.")

    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Startup Financing & Opening Balances (Fixed Baseline)")
        st.table(
            pd.DataFrame(
                [
                    {"Item": "Owner Contribution (Equity)", "Amount (USD)": "$6,000.00", "Accounting Rule": "Increases Cash & Equity (Not Revenue)"},
                    {"Item": "Equipment Assets", "Amount (USD)": "$1,500.00", "Accounting Rule": "Asset on Balance Sheet (Not Double-Expensed)"},
                    {"Item": "Pre-Opening Expense", "Amount (USD)": "$500.00", "Accounting Rule": "Initial Retained Earnings = -$500.00"},
                    {"Item": "Opening Inventory", "Amount (USD)": "$0.00", "Accounting Rule": "Service/Education Model"},
                    {"Item": "Post-Startup Spendable Cash", "Amount (USD)": "$4,000.00", "Accounting Rule": "Starting Operating Cash"},
                ]
            )
        )

        st.subheader("Monthly Demand & Resource Inputs")
        inp["simulation_date"] = st.text_input("Simulation Period End Date (YYYY-MM-DD)", value=state["simulation_date"])
        state["simulation_date"] = inp["simulation_date"]

        inp["base_price"] = str(
            st.number_input("Workshop Seat Price ($/seat)", min_value=0.0, value=float(inp["base_price"]), step=1.0)
        )
        inp["D0"] = st.number_input("Baseline Demand D0 at $25 (seats/month)", min_value=0, value=int(inp["D0"]), step=5)
        inp["requested"] = st.number_input("Current Month Requested Seats", min_value=0, value=int(inp["requested"]), step=5)
        inp["staff_hours"] = str(
            st.number_input("Educator Productive Hours / Month", min_value=0.0, value=float(inp["staff_hours"]), step=1.0)
        )
        inp["hours_per_unit"] = str(
            st.number_input("Productive Hours per Seat", min_value=0.1, value=float(inp["hours_per_unit"]), step=0.1)
        )
        inp["venue_seats"] = st.number_input("Venue Seat Capacity / Month", min_value=0, value=int(inp["venue_seats"]), step=5)
        inp["no_show_rate"] = str(
            st.slider("No-Show Rate (0.00 to 1.00)", min_value=0.0, max_value=1.0, value=float(inp["no_show_rate"]), step=0.05)
        )
        inp["satisfaction_mean"] = str(
            st.slider("Supplied Survey Satisfaction Mean (1–5)", min_value=1.0, max_value=5.0, value=float(inp["satisfaction_mean"]), step=0.1)
        )

    with c_right:
        st.subheader("Editable Variable Costs (Per Attended Seat)")
        for k, v in state["cost_lines"]["variable"].items():
            state["cost_lines"]["variable"][k] = str(
                st.number_input(f"Variable: {k} ($/seat)", min_value=0.0, value=float(v), step=0.5)
            )
        new_var_total = sum(money(v) for v in state["cost_lines"]["variable"].values())
        st.markdown(f"**Total Variable Cost per Attended Seat:** `{fmt_usd(new_var_total)}`")

        st.subheader("Editable Fixed Costs (Monthly)")
        for k, v in state["cost_lines"]["fixed"].items():
            state["cost_lines"]["fixed"][k] = str(
                st.number_input(f"Fixed: {k} ($/month)", min_value=0.0, value=float(v), step=25.0)
            )
        new_fix_total = sum(money(v) for v in state["cost_lines"]["fixed"].values())
        st.markdown(f"**Total Monthly Fixed Expense:** `{fmt_usd(new_fix_total)}`")

        st.subheader("Campaign & Optional Financing Controls")
        inp["marketing_ad_cost"] = str(
            st.number_input("Own-Business Marketing Expense ($)", min_value=0.0, value=float(inp["marketing_ad_cost"]), step=25.0)
        )
        inp["loan_cash"] = str(
            st.number_input("Simulated Loan Proceeds ($ — increases cash/debt, not revenue)", min_value=0.0, value=float(inp["loan_cash"]), step=100.0)
        )
        inp["loan_principal"] = str(
            st.number_input("Loan Principal Repayment ($ — reduces cash/debt, not profit)", min_value=0.0, value=float(inp["loan_principal"]), step=50.0)
        )
        inp["interest"] = str(
            st.number_input("Loan Interest Expense ($)", min_value=0.0, value=float(inp["interest"]), step=10.0)
        )

# ==============================================================================
# TAB 3: MATH SKILLS & LEVELS (PRECALCULUS NUR-2)
# ==============================================================================
with tabs[2]:
    st.header(f"Math Skills & Levels — Precalculus ({state['selected_level']})")
    p0 = float(inp["base_price"])
    d0 = float(inp["D0"])
    v_cost = float(var_total)
    f_cost = float(fix_total)
    cap = preview["derived_capacity"]

    # 1. FOUNDATION: Average Cost Rational Function A(q) = F/q + v
    st.subheader("1. Rational Average Cost Function $A(q) = \frac{F}{q} + v$")
    st.markdown(
        f"- **Domain:** $0 < q \le {cap}$ seats (undefined at $q = 0$, vertical asymptote at $q = 0$, horizontal asymptote at $y = \${v_cost:.2f}$/seat).\n"
        f"- **At Full Capacity ($q = {cap}$):** $A({cap}) = \frac{{{f_cost:.2f}}}{{{cap}}} + {v_cost:.2f} = \${(f_cost/cap + v_cost) if cap > 0 else 0:.2f}$ per seat."
    )

    if cap > 0:
        q_vals = np.linspace(1, cap, 60)
        a_vals = f_cost / q_vals + v_cost
        fig_ac = go.Figure()
        fig_ac.add_trace(go.Scatter(x=q_vals, y=a_vals, mode="lines", name="Average Cost A(q)"))
        fig_ac.add_hline(y=v_cost, line_dash="dash", annotation_text=f"Horizontal Asymptote y = ${v_cost:.2f}")
        fig_ac.add_vline(x=0, line_dash="dot", annotation_text="Vertical Asymptote q = 0 (Excluded)")
        fig_ac.update_layout(
            title=f"Average Cost per Attended Seat A(q) | Snapshot {state['snapshot_id']} v{state['state_version']}",
            xaxis_title="Attended Workshop Seats (q)",
            yaxis_title="Average Cost ($ / seat)",
            height=350,
        )
        st.plotly_chart(fig_ac, use_container_width=True)

    # 2. APPLIED: Function Composition q(p), s(p) = min(cap, q(p)), R(p), C(s(p)), P(p)
    if state["selected_level"] in ["Applied", "Advanced"]:
        st.divider()
        st.subheader("2. Composed Demand, Revenue, Cost & Piecewise Profit")
        breakpoint_p = p0 * (2.0 - cap / d0) if d0 > 0 else 0.0
        st.markdown(
            f"- **Linear Demand:** $q(p) = \max(0, {2*d0:.0f} - {d0/p0:.2f}p)$ on $0 \le p \le {2*p0:.2f}$\n"
            f"- **Capacity-Clipped Sales:** $s(p) = \min({cap}, q(p))$ (breakpoint at $p = \${breakpoint_p:.2f}$)\n"
            f"- **Continuous Projection vs. Integer Ledger:** Continuous curves show smooth trends; actual simulated ledger transactions floor $s(p)$ to whole seats."
        )

        p_grid = np.linspace(0, 2 * p0, 101)
        q_grid = np.maximum(0.0, 2 * d0 - (d0 / p0) * p_grid)
        s_cont = np.minimum(cap, q_grid)
        r_cont = p_grid * s_cont
        c_cont = f_cost + v_cost * s_cont
        prof_cont = r_cont - c_cont

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=p_grid, y=r_cont, mode="lines", name="Revenue R(p) [Continuous]"))
        fig_comp.add_trace(go.Scatter(x=p_grid, y=c_cont, mode="lines", name="Total Cost C(s(p)) [Continuous]"))
        fig_comp.add_trace(go.Scatter(x=p_grid, y=prof_cont, mode="lines", name="Profit P(p) [Continuous]"))
        fig_comp.add_hline(y=0, line_dash="dash", annotation_text="Break-Even Zero Line ($0)")
        fig_comp.add_vline(x=breakpoint_p, line_dash="dot", annotation_text=f"Capacity Breakpoint p = ${breakpoint_p:.2f}")
        fig_comp.update_layout(
            title=f"Composed Revenue, Cost & Profit vs. Ticket Price | Snapshot {state['snapshot_id']}",
            xaxis_title="Ticket Price p ($ / seat)",
            yaxis_title="Monthly USD ($)",
            height=400,
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # Linked Input-Output Table
        sample_prices = [15.0, 20.0, 25.0, 31.25, 35.0, 40.0]
        comp_rows = []
        for sp in sample_prices:
            qd = precalc_demand(sp, d0, p0)
            sc = min(cap, qd)
            si = int(math.floor(sc))
            comp_rows.append(
                {
                    "Price p ($)": f"${sp:.2f}",
                    "Demand q(p)": round(qd, 2),
                    "Continuous s(p)": round(sc, 2),
                    "Integer Ledger Sales": si,
                    "Continuous Profit ($)": round(sp * sc - (f_cost + v_cost * sc), 2),
                    "Integer Ledger Profit ($)": round(sp * si - (f_cost + v_cost * si), 2),
                }
            )
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True)

    # 3. ADVANCED: Seasonal Trigonometric Demand Model D(t)
    if state["selected_level"] == "Advanced":
        st.divider()
        st.subheader("3. Advanced Extension — Seasonal Trigonometric Demand Model")
        st.markdown(
            f"**Formula:** $D(t) = {d0:.0f}\left(1 + 0.20\sin\left(\frac{{2\pi(t-1)}}{{12}}\right)\right)$ "
            "(12-month period, peak at $t=4$, minimum at $t=10$, clipped at capacity). "
            "*Assumption label: Fictional seasonal teaching extension.*"
        )
        months = list(range(1, 13))
        seasonal_req = [round(precalc_seasonal_demand(t, d0), 2) for t in months]
        realized_sales = [min(cap, int(math.floor(r))) for r in seasonal_req]

        fig_trig = go.Figure()
        fig_trig.add_trace(go.Scatter(x=months, y=seasonal_req, mode="lines+markers", name="Seasonal Demand D(t)"))
        fig_trig.add_trace(go.Bar(x=months, y=realized_sales, name="Capacity-Clipped Realized Sales", opacity=0.6))
        fig_trig.add_hline(y=cap, line_dash="dash", annotation_text=f"Capacity Cap ({cap} seats)")
        fig_trig.update_layout(
            title=f"12-Month Seasonal Demand D(t) vs. Capacity-Clipped Sales | Snapshot {state['snapshot_id']}",
            xaxis_title="Month Index t (1 = Jan, 4 = Apr Peak, 10 = Oct Low)",
            yaxis_title="Workshop Seats",
            height=380,
        )
        st.plotly_chart(fig_trig, use_container_width=True)

        trig_df = pd.DataFrame(
            {
                "Month t": months,
                "Seasonal Demand D(t)": seasonal_req,
                "Capacity Cap": [cap] * 12,
                "Realized Sales (Floored & Clipped)": realized_sales,
                "Unserved Demand": [max(0, int(math.floor(r)) - s) for r, s in zip(seasonal_req, realized_sales)],
            }
        )
        st.dataframe(trig_df, use_container_width=True)

    st.divider()
    st.subheader("Transfer Check (Predict Before Moving a Slider)")
    st.text_area(
        "Student Independent Worked Calculation & Limitation Note:",
        placeholder="Example: At q = 60, C(60) = $700 + $5(60) = $1,000 total cost, while A(60) = $1,000 / 60 = $16.67 per seat...",
    )

# ==============================================================================
# TAB 4: OPERATIONS & CUSTOMERS
# ==============================================================================
with tabs[3]:
    st.header("Operations & Customer Funnel")
    st.markdown(
        "**Rule:** `booked = min(requested, floor(staff_hours / hours_per_unit), venue_seats)` "
        "and `attended = floor(booked * (1 - no_show_rate))`. Payment and variable costs occur only on attended seats."
    )

    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Requested Demand", f"{preview['requested']} seats")
    o2.metric("Booked Seats", f"{preview['booked']} seats")
    o3.metric("Attended (Sold)", f"{preview['attended']} seats")
    o4.metric("Unserved Demand", f"{preview['unserved_demand']} seats")

    st.progress(min(1.0, preview["educator_utilization_pct"] / 100.0), text=f"Educator Utilization: {preview['educator_utilization_pct']}%")

    st.subheader("Catalog of Fictional Nonclinical Offerings")
    st.table(pd.DataFrame(state["offerings"]))

# ==============================================================================
# TAB 5: FINANCE & DATED LEDGER
# ==============================================================================
with tabs[4]:
    st.header("Finance & Dated Event Ledger")

    col_act, col_bal = st.columns([1.2, 1])
    with col_act:
        st.subheader("Commit Current Month to Dated Ledger")
        run_id_input = st.text_input(
            "Unique Run ID (Duplicate-Run Guard)",
            value=f"RUN-{state['simulation_date']}-v{state['state_version']}",
        )
        if st.button("Approve & Record Month Transaction", type="primary"):
            if run_id_input in state["executed_run_ids"]:
                st.warning(f"DUPLICATE RUN PREVENTED: `{run_id_input}` has already been recorded.")
            else:
                tx = {
                    "transaction_id": f"TX-{len(state['ledger']) + 1:04d}",
                    "run_id": run_id_input,
                    "date": state["simulation_date"],
                    "mode": state["run_mode"],
                    "state_version": state["state_version"],
                    "requested": preview["requested"],
                    "booked": preview["booked"],
                    "sold": preview["sold"],
                    "revenue": str(preview["revenue"]),
                    "variable_expense": str(preview["variable_expense"]),
                    "fixed_expense": str(preview["fixed_expense"]),
                    "marketing_expense": str(preview["marketing_expense"]),
                    "total_expense": str(preview["total_expense"]),
                    "operating_profit": str(preview["operating_profit"]),
                    "closing_cash": str(preview["ending_cash"]),
                }
                state["ledger"].append(tx)
                state["executed_run_ids"].append(run_id_input)
                state["inputs"]["opening_cash"] = str(preview["ending_cash"])
                state["state_version"] += 1
                state["snapshot_id"] = f"SNAP-{state['state_version']:04d}"
                st.success(f"Recorded `{tx['transaction_id']}` and updated cash to {fmt_usd(preview['ending_cash'])}.")
                st.rerun()

    with col_bal:
        st.subheader("Reconciled Accounting Snapshot")
        current_cash = money(state["inputs"]["opening_cash"])
        equip_assets = money(state["startup"]["equipment_assets"])
        total_assets = current_cash + equip_assets
        st.table(
            pd.DataFrame(
                [
                    {"Line": "Current Spendable Cash", "USD": fmt_usd(current_cash)},
                    {"Line": "Equipment Assets (Gross)", "USD": fmt_usd(equip_assets)},
                    {"Line": "Total Assets", "USD": fmt_usd(total_assets)},
                    {"Line": "Baseline Monthly Fixed Cost", "USD": fmt_usd(fix_total)},
                    {"Line": "Baseline Variable Cost / Seat", "USD": fmt_usd(var_total)},
                ]
            )
        )

    st.subheader("Dated Event Ledger")
    if state["ledger"]:
        ledger_df = pd.DataFrame(state["ledger"])
        st.dataframe(ledger_df, use_container_width=True)
        st.download_button(
            "Export Ledger CSV",
            data=ledger_df.to_csv(index=False),
            file_name=f"{state['team_id']}_NUR2_ledger.csv",
            mime="text/csv",
        )
    else:
        st.info("No transactions committed yet. Review inputs or run the fixture test in the next tab.")

# ==============================================================================
# TAB 6: FIXTURE & ACCEPTANCE TESTS
# ==============================================================================
with tabs[5]:
    st.header("NUR Acceptance & Fixture Verification")
    st.markdown(
        "Replays the exact 3-month `NUR` fixture (`sample_data/monthly_fixture.csv`) from opening cash **$4,000.00** "
        "and checks all handbook acceptance criteria (Handbook p. 85)."
    )

    fixture_csv_default = (
        "month,requested,capacity_override,ad_cost\n"
        "2027-01,80,60,0\n"
        "2027-02,88,60,100\n"
        "2027-03,72,45,0\n"
    )
    fixture_text = st.text_area("monthly_fixture.csv", value=fixture_csv_default, height=130)

    if st.button("Run NUR Acceptance Test Suite"):
        df_fix = pd.read_csv(StringIO(fixture_text))
        cash = Decimal("4000.00")
        results = []
        expected = [
            {"month": "2027-01", "sold": 60, "rev": Decimal("1500.00"), "exp": Decimal("1000.00"), "prof": Decimal("500.00"), "cash": Decimal("4500.00")},
            {"month": "2027-02", "sold": 60, "rev": Decimal("1500.00"), "exp": Decimal("1100.00"), "prof": Decimal("400.00"), "cash": Decimal("4900.00")},
            {"month": "2027-03", "sold": 45, "rev": Decimal("1125.00"), "exp": Decimal("925.00"), "prof": Decimal("200.00"), "cash": Decimal("5100.00")},
        ]

        all_pass = True
        for idx, row in df_fix.iterrows():
            res = compute_nur_month(
                requested=int(row["requested"]),
                base_price=Decimal("25.00"),
                staff_hours=Decimal("30.0"),
                hours_per_unit=Decimal("0.5"),
                venue_seats=60,
                no_show_rate=Decimal("0.00"),
                var_cost_per_unit=Decimal("5.00"),
                fixed_cost_total=Decimal("700.00"),
                marketing_cost=money(row["ad_cost"]),
                opening_cash=cash,
                capacity_override=int(row["capacity_override"]),
            )
            cash = res["ending_cash"]
            exp = expected[idx]
            row_pass = (
                res["sold"] == exp["sold"]
                and res["revenue"] == exp["rev"]
                and res["total_expense"] == exp["exp"]
                and res["operating_profit"] == exp["prof"]
                and res["ending_cash"] == exp["cash"]
            )
            all_pass = all_pass and row_pass
            results.append(
                {
                    "Month": row["month"],
                    "Sold": res["sold"],
                    "Revenue": fmt_usd(res["revenue"]),
                    "Total Expense": fmt_usd(res["total_expense"]),
                    "Operating Profit": fmt_usd(res["operating_profit"]),
                    "Closing Cash": fmt_usd(res["ending_cash"]),
                    "Status": "PASS" if row_pass else "FAIL",
                }
            )

        # Business-specific no-show test (no_show_rate = 0.20 -> booked=60, attended=48, rev=$1,200, var=$240, profit=$260)
        noshow_test = compute_nur_month(
            requested=80,
            base_price=Decimal("25.00"),
            staff_hours=Decimal("30.0"),
            hours_per_unit=Decimal("0.5"),
            venue_seats=60,
            no_show_rate=Decimal("0.20"),
            var_cost_per_unit=Decimal("5.00"),
            fixed_cost_total=Decimal("700.00"),
            marketing_cost=Decimal("0.00"),
            opening_cash=Decimal("4000.00"),
        )
        noshow_pass = (
            noshow_test["booked"] == 60
            and noshow_test["attended"] == 48
            and noshow_test["revenue"] == Decimal("1200.00")
            and noshow_test["variable_expense"] == Decimal("240.00")
            and noshow_test["operating_profit"] == Decimal("260.00")
        )

        # Zero-sales test
        zero_test = compute_nur_month(
            requested=0,
            base_price=Decimal("25.00"),
            staff_hours=Decimal("30.0"),
            hours_per_unit=Decimal("0.5"),
            venue_seats=60,
            no_show_rate=Decimal("0.00"),
            var_cost_per_unit=Decimal("5.00"),
            fixed_cost_total=Decimal("700.00"),
            marketing_cost=Decimal("0.00"),
            opening_cash=Decimal("4000.00"),
        )
        zero_pass = (
            zero_test["revenue"] == Decimal("0.00")
            and zero_test["variable_expense"] == Decimal("0.00")
            and zero_test["operating_profit"] == Decimal("-700.00")
        )

        st.dataframe(pd.DataFrame(results), use_container_width=True)
        st.write(f"**20% No-Show Test (Booked 60, Attended 48, Profit $260):** `{'PASS' if noshow_pass else 'FAIL'}`")
        st.write(f"**Zero-Sales Test (Revenue $0, Profit -$700):** `{'PASS' if zero_pass else 'FAIL'}`")
        if all_pass and noshow_pass and zero_pass:
            st.success("ALL STAGE 1 NUMERICAL & FIXTURE ACCEPTANCE TESTS PASSED.")
        else:
            st.error("One or more checks failed. Review inputs and formulas.")

# ==============================================================================
# TAB 7: STAGE 2-4 ROADMAP (HONEST UNIMPLEMENTED STATUS)
# ==============================================================================
with tabs[6]:
    st.header("Implementation Roadmap & Unfinished Features")
    st.table(
        pd.DataFrame(
            [
                {"Stage": "Stage 1 (Current)", "Modules": "Inputs, Precalculus Math Panel, Dated Ledger, Save/Restore JSON, Fixture Tests", "Status": "IMPLEMENTED"},
                {"Stage": "Stage 2 (Next)", "Modules": "AI Departmental Handoff Cards, Full Report Center (PDF/CSV), Costed Marketing Studio", "Status": "NOT YET IMPLEMENTED"},
                {"Stage": "Stage 3", "Modules": "Frozen-Snapshot Practice Assessment & Teacher-Locked Graded Key", "Status": "NOT YET IMPLEMENTED"},
                {"Stage": "Stage 4 (Optional)", "Modules": "Fictional Demonstration Storefront (No Real Payments)", "Status": "NOT YET IMPLEMENTED"},
            ]
        )
    )
