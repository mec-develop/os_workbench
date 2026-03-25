import streamlit as st
import pandas as pd
import math
from supabase import create_client

st.set_page_config(layout="wide")

# =========================
# DB CONNECTION
# =========================
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    return (
        pd.DataFrame(supabase.table("layers").select("*").execute().data),
        pd.DataFrame(supabase.table("activities").select("*").execute().data),
        pd.DataFrame(supabase.table("activity_details").select("*").execute().data),
    )

layers, activities, activity_details = load_data()

# =========================
# SESSION
# =========================
if "page" not in st.session_state:
    st.session_state.page = "layers"

if "layer" not in st.session_state:
    st.session_state.layer = None

if "activity" not in st.session_state:
    st.session_state.activity = None

# =========================
# NAV
# =========================
def go_layers():
    st.session_state.page = "layers"
    st.session_state.layer = None
    st.session_state.activity = None
    st.rerun()

def go_layer(layer):
    st.session_state.page = "activities"
    st.session_state.layer = layer
    st.rerun()

def go_activity(activity_id):
    st.session_state.page = "details"
    st.session_state.activity = activity_id
    st.rerun()

# =========================
# HELPERS
# =========================
def progress(activity_id):
    rows = activity_details[activity_details["activity_id"] == activity_id]
    return int((rows["status"] == "Complete").mean() * 100) if len(rows) else 0

def layer_progress(layer):
    acts = activities[activities["layer_name"] == layer]
    vals = [progress(a) for a in acts["activity_id"]]
    return int(sum(vals) / len(vals)) if vals else 0

# =========================
# UI
# =========================
st.title("OS Workbench")

# -------------------------
# LAYERS
# -------------------------
if st.session_state.page == "layers":
    st.header("Layers")

    cols = st.columns(5)

    for i, row in layers.iterrows():
        p = layer_progress(row["layer_name"])

        with cols[i % 5]:
            if st.button(
                f"{row['layer_name']}\n{p}%",
                key=f"layer_{i}",
                use_container_width=True
            ):
                go_layer(row["layer_name"])

# -------------------------
# ACTIVITIES
# -------------------------
elif st.session_state.page == "activities":

    if st.button("← Back"):
        go_layers()

    st.header(st.session_state.layer)

    acts = activities[activities["layer_name"] == st.session_state.layer]

    cols = st.columns(3)

    for i, row in acts.iterrows():
        p = progress(row["activity_id"])

        with cols[i % 3]:
            if st.button(
                f"{row['activity_name']}\n{p}%",
                key=f"act_{row['activity_id']}",
                use_container_width=True
            ):
                go_activity(row["activity_id"])

# -------------------------
# DETAILS
# -------------------------
elif st.session_state.page == "details":

    if st.button("← Back"):
        go_layer(st.session_state.layer)

    act = activities[activities["activity_id"] == st.session_state.activity].iloc[0]
    st.header(act["activity_name"])

    rows = activity_details[activity_details["activity_id"] == act["activity_id"]]

    for _, row in rows.iterrows():
        new_status = st.selectbox(
            row["acceptance_criteria"],
            ["Not Started", "In Progress", "Complete"],
            key=f"row_{row['row_id']}"
        )

        if new_status != row["status"]:
            supabase.table("activity_details").update(
                {"status": new_status}
            ).eq("row_id", row["row_id"]).execute()

            st.cache_data.clear()
            st.rerun()