import streamlit as st
import numpy as np
import plotly.graph_objects as go
import time

# ==========================================
# 1. PAGE CONFIGURATION & HEADER
# ==========================================
st.set_page_config(page_title="Mazda RX-8 Spirit R Simulator", layout="wide")
st.title(" Mazda RX-8 Spirit R Twin-Turbo Acceleration Simulation")
st.markdown("""
This simulator validates the longitudinal dynamics of a modified Mazda RX-8 Spirit R.
You can **tune the individual boost pressures of the sequential turbochargers** via the sidebar to observe the direct impact on the power band and the 300 km/h top speed challenge.
""")

# ==========================================
# 2. SIDEBAR PARAMETERS & TURBO TUNING SLIDERS
# ==========================================
st.sidebar.header("⚙️ Vehicle Specifications")

# Vehicle & Aero
st.sidebar.subheader("Body & Aerodynamics")
mass = st.sidebar.number_input("Total Mass (kg)", value=1550, step=10)
Cd = st.sidebar.number_input("Drag Coefficient (Cd)", value=0.30, step=0.01)
A = st.sidebar.number_input("Frontal Area (m²)", value=2.0, step=0.1)

# NEW FEATURE: Turbocharger Tuning Sliders (0% to 100%)
st.sidebar.subheader("🌀 Turbocharger Tuning")
small_turbo_pct = st.sidebar.slider("Small Turbo Max Pressure (%)", 0, 100, 100, 5) / 100.0
large_turbo_pct = st.sidebar.slider("Large Turbo Max Pressure (%)", 0, 100, 100, 5) / 100.0

# Tire Parameters (275/35 R18)
st.sidebar.subheader("Tire Specifications")
tire_width = st.sidebar.number_input("Width (mm)", value=275)
aspect_ratio = st.sidebar.number_input("Aspect Ratio (%)", value=35)
rim_diameter = st.sidebar.number_input("Rim Diameter (inch)", value=18)

# Drivetrain
st.sidebar.subheader("Drivetrain")
final_drive = st.sidebar.number_input("Final Drive Ratio", value=4.777, step=0.001)
gear_ratios = {1: 3.815, 2: 2.260, 3: 1.536, 4: 1.177, 5: 1.000, 6: 0.787}
drivetrain_efficiency = 0.85

# Dynamic Controls
st.sidebar.subheader("Dynamic Controls")
shift_time = st.sidebar.slider("Shift Delay (sec)", 0.0, 1.0, 0.5, 0.05)
slip_time = st.sidebar.slider("Clutch Slip Time 1st Gear (sec)", 0.0, 2.0, 1.0, 0.1)
launch_rpm = st.sidebar.number_input("Launch RPM", value=6500, step=100)
redline_rpm = st.sidebar.number_input("Redline (RPM)", value=9500, step=100)

# ==========================================
# 3. ENGINE & TURBO LOGIC WITH SCALING FACTORS
# ==========================================
def get_boost_pressure(rpm, small_scale, large_scale):
    """
    Calculates boost pressure scaling dynamically with user inputs.
    Base setup: Small Turbo max = 0.5 bar, Large Turbo adds 1.0 bar (Total 1.5 bar).
    """
    b_small_max = 0.5 * small_scale
    b_large_max = 1.0 * large_scale
    b_total_max = b_small_max + b_large_max
    
    if rpm < 2500:
        return 0.0
    elif 2500 <= rpm < 3000:
        # Small turbo ramping up
        return b_small_max * ((rpm - 2500) / 500)
    elif 3000 <= rpm < 4000:
        # Small turbo holding its max pressure
        return b_small_max
    elif 4000 <= rpm < 5000:
        # Large turbo compounding
        return b_small_max + b_large_max * ((rpm - 4000) / 1000)
    elif 5000 <= rpm < 9000:
        # Combined full boost platform
        return b_total_max
    elif 9000 <= rpm <= 9500:
        # Proportional high-RPM linear degradation
        # Baseline dropped 0.4 bar out of 1.5 bar peak
        base_drop = 0.4 * (b_total_max / 1.5 if b_total_max > 0 else 0)
        return b_total_max - base_drop * ((rpm - 9000) / 500)
    else:
        base_drop = 0.4 * (b_total_max / 1.5 if b_total_max > 0 else 0)
        return b_total_max - base_drop

def get_base_torque(rpm):
    """ Base Naturally Aspirated (NA) rotary torque curve """
    if rpm < 1100:
        return 130.0
    elif 1100 <= rpm < 6200:
        return 130.0 + 70.0 * ((rpm - 1100) / (6200 - 1100))
    elif 6200 <= rpm < 9200:
        return 200.0 - 50.0 * ((rpm - 6200) / (9200 - 6200))
    else:
        return 150.0 - 40.0 * ((rpm - 9200) / (9500 - 9200))

def get_total_torque(rpm, small_scale, large_scale):
    """ Total torque scaling based on turbo modifiers """
    boost = get_boost_pressure(rpm, small_scale, large_scale)
    base_tq = get_base_torque(rpm)
    return base_tq * (1.0 + boost)

# Calculate tire dynamic radius (meters)
tire_radius = (rim_diameter * 25.4 / 2 + tire_width * aspect_ratio / 100) / 1000

# ==========================================
# 4. STATIC VISUALIZATION (ENGINE MAP)
# ==========================================
st.markdown("---")
st.subheader("📊 Engine & Turbo Characteristics (Tuned)")

rpm_range = np.linspace(1000, 9500, 500)
# Passing the live slider states to the plotting array
boost_curve = [get_boost_pressure(r, small_turbo_pct, large_turbo_pct) for r in rpm_range]
base_tq_curve = [get_base_torque(r) for r in rpm_range]
total_tq_curve = [get_total_torque(r, small_turbo_pct, large_turbo_pct) for r in rpm_range]
power_kw_curve = [(t * r) / 9550 for t, r in zip(total_tq_curve, rpm_range)]

fig_eng = go.Figure()
fig_eng.add_trace(go.Scatter(x=rpm_range, y=total_tq_curve, name="Total Torque (Nm)", line=dict(color='#2563eb', width=2.5), yaxis='y1'))
fig_eng.add_trace(go.Scatter(x=rpm_range, y=base_tq_curve, name="Base NA Torque", line=dict(color='#94a3b8', width=2, dash='dot'), yaxis='y1'))
fig_eng.add_trace(go.Scatter(x=rpm_range, y=power_kw_curve, name="Power (kW)", line=dict(color='#dc2626', width=2.5), yaxis='y2'))
fig_eng.add_trace(go.Scatter(x=rpm_range, y=boost_curve, name="Boost (Bar)", line=dict(color='#059669', width=2, dash='dash'), yaxis='y3'))

# Plotly v6+ compatible layout dicts
fig_eng.update_layout(
    xaxis=dict(title=dict(text="<b>Engine Speed (RPM)</b>")),
    yaxis=dict(title=dict(text="<b>Torque (Nm)</b>", font=dict(color="#2563eb")), tickfont=dict(color="#2563eb")),
    yaxis2=dict(title=dict(text="<b>Power (kW)</b>", font=dict(color="#dc2626")), tickfont=dict(color="#dc2626"), anchor="x", overlaying="y", side="right"),
    yaxis3=dict(title=dict(text="<b>Boost (Bar)</b>", font=dict(color="#059669")), tickfont=dict(color="#059669"), anchor="free", overlaying="y", side="right", position=0.95),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(r=80)
)
st.plotly_chart(fig_eng, use_container_width=True)

# ==========================================
# 5. LONGITUDINAL DYNAMICS SIMULATION (DYNAMIC WITH POWER & TORQUE)
# ==========================================
import time # Ensure this is imported at the top of your file!

st.markdown("---")
st.subheader("⏱️ Dynamic Acceleration Simulation (0 - 300+ km/h)")

if st.button("🚀 RUN DYNAMIC SIMULATION", type="primary"):
    # Environmental Constants
    rho = 1.225 # Air density (kg/m^3)
    g = 9.81    # Gravity (m/s^2)
    Crr = 0.015 # Rolling resistance coefficient
    mu = 1.0    # Tire grip coefficient

    # Integration variables
    dt = 0.01  # Time step (10ms)
    t = 0.0
    v_ms = 0.0
    current_gear = 1
    engine_rpm = launch_rpm # Initialize RPM
    current_torque = 0.0    # Initialize Torque variable
    
    # Trackers
    time_100, time_200, time_300 = None, None, None
    time_history, speed_history, gear_history, force_history, resist_history = [], [], [], [], []
    
    is_shifting = False
    shift_timer = 0.0
    
    # --- UI Placeholders for Dynamic Animation ---
    st.markdown("### Live Telemetry")
    progress_bar = st.progress(0)
    live_dashboard = st.empty() # Placeholder for live metrics
    
    # Run loop until 310 km/h or timeout (60 seconds)
    while (v_ms * 3.6) < 310.0 and t < 60.0:
        v_kmh = v_ms * 3.6
        
        # Record milestones
        if v_kmh >= 100 and time_100 is None: time_100 = t
        if v_kmh >= 200 and time_200 is None: time_200 = t
        if v_kmh >= 300 and time_300 is None: time_300 = t
            
        # Resistance
        F_aero = 0.5 * rho * Cd * A * v_ms**2
        F_roll = mass * g * Crr
        F_resistance = F_aero + F_roll
        
        # Drivetrain State Machine
        if is_shifting:
            F_tractive = 0.0
            current_torque = 0.0 # Torque drops to zero during gear shifts
            shift_timer -= dt
            if shift_timer <= 0:
                is_shifting = False
            wheel_rpm = (v_ms * 60) / (2 * np.pi * tire_radius)
            engine_rpm = wheel_rpm * gear_ratios[current_gear] * final_drive
        else:
            if current_gear == 1 and t <= slip_time:
                # 1st Gear Clutch Slip Phase
                engine_rpm = launch_rpm
                k_slip = t / slip_time if slip_time > 0 else 1.0
                current_torque = get_total_torque(engine_rpm, small_turbo_pct, large_turbo_pct)
                F_tractive = (current_torque * gear_ratios[current_gear] * final_drive * drivetrain_efficiency) / tire_radius * k_slip
            else:
                # Locked Gear Phase
                wheel_rpm = (v_ms * 60) / (2 * np.pi * tire_radius)
                engine_rpm = wheel_rpm * gear_ratios[current_gear] * final_drive
                
                # Check for Redline Shift trigger
                if engine_rpm > redline_rpm and current_gear < max(gear_ratios.keys()):
                    is_shifting = True
                    current_gear += 1
                    shift_timer = shift_time
                    F_tractive = 0.0
                    current_torque = 0.0 # Instant cut-off
                else:
                    current_torque = get_total_torque(engine_rpm, small_turbo_pct, large_turbo_pct)
                    F_tractive = (current_torque * gear_ratios[current_gear] * final_drive * drivetrain_efficiency) / tire_radius
            
            # Traction limit check
            F_max_grip = mu * mass * g
            F_tractive = min(F_tractive, F_max_grip)
            
        # Equivalent mass calculation
        delta = 0.04 + 0.05 * (gear_ratios[current_gear]**2)
        m_eq = mass * (1 + delta)
        
        # Instantaneous acceleration calculation
        a = (F_tractive - F_resistance) / m_eq
        
        if a < 0 and not is_shifting and F_tractive > 0:
            a = 0 # Top speed limit hit
            
        # Euler integration step
        v_ms += a * dt
        t += dt
        
        # Save logs
        time_history.append(t)
        speed_history.append(v_kmh)
        gear_history.append(current_gear)
        force_history.append(F_tractive)
        resist_history.append(F_resistance)
        
        # ==========================================
        # UI DYNAMIC UPDATE LOGIC (1:1 SIMULATION)
        # ==========================================
        # Refresh the dashboard view every 10 iterations (0.1 seconds of sim time)
        if int(t / dt) % 10 == 0:
            progress_val = min(int((v_kmh / 310) * 100), 100)
            progress_bar.progress(progress_val)
            
            # Calculate live horsepower (hp) from real-time torque and engine speed
            live_power_kw = (current_torque * engine_rpm) / 9550
            live_power_hp = live_power_kw * 1.341
            
            with live_dashboard.container():
                # Expanded into 6 metrics column layout
                lc1, lc2, lc3, lc4, lc5, lc6 = st.columns(6)
                lc1.metric("Live Speed", f"{v_kmh:.1f} km/h")
                lc2.metric("Current Gear", f"G {current_gear}")
                
                rpm_color = "🔴" if is_shifting or engine_rpm > (redline_rpm - 500) else "🟢"
                lc3.metric("Engine RPM", f"{rpm_color} {int(engine_rpm)} RPM")
                
                # New Telemetry Indicators
                lc4.metric("Live Torque", f"{current_torque:.1f} Nm")
                lc5.metric("Live Power", f"{live_power_hp:.1f} hp")
                
                lc6.metric("Sim Time", f"{t:.1f} s")
                
            time.sleep(0.1) # Pauses for 0.1s in real-world to achieve a 1:1 timeline match
            
        if a == 0 and current_gear == 6 and not is_shifting:
            break

    # ==========================================
    # 6. FINAL RESULTS & VISUALIZATION - INTERACTIVE
    # ==========================================
    live_dashboard.empty()
    st.success("🏁 Simulation Complete!")

    st.markdown("### 📊 Final Performance Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("0-100 km/h", f"{time_100:.2f} s" if time_100 else "N/A")
    c2.metric("100-200 km/h", f"{(time_200 - time_100):.2f} s" if time_200 else "N/A")
    c3.metric("0-300 km/h", f"{time_300:.2f} s" if time_300 else "Failed")
    c4.metric("Top Speed Achieved", f"{max(speed_history):.1f} km/h")

    fig_dyn = go.Figure()
    fig_dyn.add_trace(go.Scatter(x=time_history, y=speed_history, name="Vehicle Speed (km/h)", line=dict(color='black', width=3), yaxis='y1'))
    fig_dyn.add_hline(y=300, line_dash="dash", line_color="red", annotation_text="300 km/h Barrier")
    fig_dyn.add_trace(go.Scatter(x=time_history, y=force_history, name="Tractive Force (N)", line=dict(color='orange', width=2), opacity=0.7, yaxis='y2'))
    fig_dyn.add_trace(go.Scatter(x=time_history, y=resist_history, name="Total Resistance (N)", line=dict(color='purple', width=2, dash='dashdot'), opacity=0.7, yaxis='y2'))

    gear_changes = np.where(np.diff(gear_history) > 0)[0]
    for idx in gear_changes:
        fig_dyn.add_vline(x=time_history[idx], line_width=1, line_dash="dot", line_color="blue", opacity=0.4)
        fig_dyn.add_annotation(x=time_history[idx], y=speed_history[idx] + 20, text=f"G{gear_history[idx+1]}", showarrow=False, font=dict(color="blue", size=10))

    fig_dyn.update_layout(
        xaxis=dict(title="<b>Time (sec)</b>"),
        yaxis=dict(title="<b>Speed (km/h)</b>"),
        yaxis2=dict(title="<b>Force (N)</b>", anchor="x", overlaying="y", side="right"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    st.plotly_chart(fig_dyn, use_container_width=True)