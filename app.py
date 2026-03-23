import streamlit as st
import pandas as pd
import math
from supabase import create_client

st.set_page_config(layout="wide")

# =========================
# SUPABASE CONNECTION
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
    layers = pd.DataFrame(
        supabase.table("layers").select("*").execute().data
    )
    activities = pd.DataFrame(
        supabase.table("activities").select("*").execute().data
    )
    activity_details = pd.DataFrame(
        supabase.table("activity_details").select("*").execute().data
    )
    return layers, activities, activity_details


layers, activities, activity_details = load_data()

# =========================
# SESSION STATE
# =========================
if "current_page" not in st.session_state:
    st.session_state.current_page = "layers"

if "selected_layer" not in st.session_state:
    st.session_state.selected_layer = None

if "selected_activity_id" not in st.session_state:
    st.session_state.selected_activity_id = None

if "toast_message" not in st.session_state:
    st.session_state.toast_message = None

# show toast once
if st.session_state.toast_message:
    st.toast(st.session_state.toast_message)
    st.session_state.toast_message = None

# =========================
# NAV
# =========================
def go_to_layers():
    st.session_state.selected_layer = None
    st.session_state.selected_activity_id = None
    st.session_state.current_page = "layers"
    st.rerun()


def go_to_layer_detail(layer: str):
    st.session_state.selected_layer = layer
    st.session_state.current_page = "layer_detail"
    st.rerun()

# =========================
# LOGIC
# =========================
def calculate_progress(activity_id: int) -> int:
    rows = activity_details[activity_details["activity_id"] == activity_id]
    if len(rows) == 0:
        return 0
    complete = len(rows[rows["status"] == "Complete"])
    return int((complete / len(rows)) * 100)


def derive_activity_status(activity_id: int) -> str:
    rows = activity_details[activity_details["activity_id"] == activity_id]
    statuses = rows["status"].fillna("Not Started").tolist()

    if all(s == "Complete" for s in statuses):
        return "Complete"
    if any(s == "In Progress" for s in statuses) or (
        any(s == "Complete" for s in statuses) and any(s == "Not Started" for s in statuses)
    ):
        return "In Progress"
    return "Not Started"


def calculate_layer_progress(layer_name: str) -> int:
    layer_rows = activities[activities["layer_name"] == layer_name]
    vals = [calculate_progress(a) for a in layer_rows["activity_id"]]
    return int(sum(vals) / len(vals)) if vals else 0


def get_color(progress: int) -> str:
    if progress == 0:
        return "#E5E7EB"
    elif progress < 40:
        return "#FCA5A5"
    elif progress < 70:
        return "#FDBA74"
    elif progress < 100:
        return "#BBF7D0"
    else:
        return "#4CAF50"


def get_status_color(status: str) -> str:
    if status == "Complete":
        return "#2E7D32"
    elif status == "In Progress":
        return "#B45309"
    return "#6B7280"


def get_blocker(activity_row):
    current_progress = calculate_progress(activity_row["activity_id"])
    if current_progress > 0:
        return None

    same_layer = activities[activities["layer_name"] == activity_row["layer_name"]]
    earlier = same_layer[same_layer["ooo"] < activity_row["ooo"]]

    for _, prior in earlier.iterrows():
        if calculate_progress(prior["activity_id"]) < 100:
            return prior["activity_name"]

    return None

# =========================
# TITLE
# =========================
st.title("OS Workbench")

# =========================
# LAYERS PAGE
# =========================
if st.session_state.current_page == "layers":
    st.header("Layers")

    cols = st.columns(5)

    for i, row in layers.iterrows():
        progress = calculate_layer_progress(row["layer_name"])
        with cols[i % 5]:
            if st.button(
                f"{row['layer_name']}\n{progress}%",
                use_container_width=True
            ):
                go_to_layer_detail(row["layer_name"])

    st.stop()

# =========================
# LAYER PAGE
# =========================
selected_layer = st.session_state.selected_layer

if st.button("← Back to Layers"):
    go_to_layers()

st.header(selected_layer)

layer_progress = calculate_layer_progress(selected_layer)
st.progress(layer_progress / 100)
st.caption(f"Layer Progress: {layer_progress}%")

# =========================
# FILTERS
# =========================
st.sidebar.header("Filters")

layer_acts = activities[activities["layer_name"] == selected_layer]

owners = st.sidebar.multiselect(
    "Owner",
    sorted(layer_acts["owner"].dropna().unique())
)

search = st.sidebar.text_input("Search Activity")

filtered = layer_acts.copy()

if owners:
    filtered = filtered[filtered["owner"].isin(owners)]

if search:
    filtered = filtered[
        filtered["activity_name"].str.contains(search, case=False, na=False)
    ]

# =========================
# TILE GRID
# =========================
st.subheader("Activities")

acts = filtered.to_dict("records")

cols_per_row = 3
rows = math.ceil(len(acts) / cols_per_row)

for r in range(rows):
    cols = st.columns(cols_per_row)

    for c in range(cols_per_row):
        idx = r * cols_per_row + c
        if idx >= len(acts):
            continue

        a = acts[idx]
        progress = calculate_progress(a["activity_id"])
        blocker = get_blocker(a)

        if blocker:
            color = "#D1D5DB"
            label = f"{a['activity_name']}\nBlocked by: {blocker}"
        else:
            color = get_color(progress)
            label = f"{a['activity_name']}\n{progress}%"

        st.markdown(
            f"""
            <style>
            div[data-testid="stButton"][key="tile_{a['activity_id']}"] button {{
                background: {color};
                border-radius: 12px;
                height: 110px;
                font-weight: 600;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        with cols[c]:
            if st.button(label, key=f"tile_{a['activity_id']}", use_container_width=True):
                st.session_state.selected_activity_id = a["activity_id"]

# =========================
# DETAILS
# =========================
st.subheader("Activity Details")

aid = st.session_state.get("selected_activity_id")

if aid:
    act = activities[activities["activity_id"] == aid].iloc[0]

    prog = calculate_progress(aid)
    status = derive_activity_status(aid)

    st.subheader(act["activity_name"])

    c1, c2, c3, c4 = st.columns([2, 2, 4, 1])

    with c1:
        st.caption("Owner")
        new_owner = st.selectbox("", ["Sam", "Marti"], key="owner")

        if new_owner != act["owner"]:
            supabase.table("activities").update(
                {"owner": new_owner}
            ).eq("activity_id", aid).execute()

            st.session_state.toast_message = "Saved ✓"
            st.cache_data.clear()
            st.rerun()

    with c2:
        st.caption("Status")
        st.markdown(f"### {status}")

    with c3:
        st.caption("Progress")
        st.progress(prog / 100)

    with c4:
        st.caption("Points")
        st.markdown(f"### {act['story_points']}")

    # =========================
    # EXECUTION STEPS
    # =========================
    st.subheader("Execution Steps")

    rows_df = activity_details[activity_details["activity_id"] == aid]

    for _, row in rows_df.iterrows():

        cols = st.columns([2, 4, 4, 3, 2])

        cols[0].write(row["criteria_category"])
        cols[1].write(row["acceptance_criteria"])
        cols[2].write(row["what_this_means"])
        cols[3].write(row["measures_and_success"])

        new_status = cols[4].selectbox(
            "",
            ["Not Started", "In Progress", "Complete"],
            key=f"status_{row['row_id']}"
        )

        if new_status != row["status"]:
            supabase.table("activity_details").update(
                {"status": new_status}
            ).eq("row_id", row["row_id"]).execute()

            st.session_state.toast_message = "Saved ✓"
            st.cache_data.clear()
            st.rerun()

else:
    st.info("Select an activity")