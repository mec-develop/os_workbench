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
    return (
        pd.DataFrame(supabase.table("layers").select("*").execute().data),
        pd.DataFrame(supabase.table("activities").select("*").execute().data),
        pd.DataFrame(supabase.table("activity_details").select("*").execute().data),
    )

layers, activities, activity_details = load_data()

# =========================
# SESSION STATE
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
    st.session_state.activity = None
    st.rerun()

def select_activity(activity_id):
    st.session_state.activity = activity_id
    st.rerun()

# =========================
# HELPERS
# =========================
def progress(activity_id):
    rows = activity_details[activity_details["activity_id"] == activity_id]
    return int((rows["status"] == "Complete").mean() * 100) if len(rows) else 0

def derive_status(activity_id):
    rows = activity_details[activity_details["activity_id"] == activity_id]
    statuses = rows["status"].tolist()

    if all(s == "Complete" for s in statuses):
        return "Complete"
    if any(s == "In Progress" for s in statuses) or (
        any(s == "Complete" for s in statuses) and any(s == "Not Started" for s in statuses)
    ):
        return "In Progress"
    return "Not Started"

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
# ACTIVITIES (INLINE DETAILS)
# -------------------------
elif st.session_state.page == "activities":

    if st.button("← Back"):
        go_layers()

    st.header(st.session_state.layer)

    # Layer progress
    lp = layer_progress(st.session_state.layer)
    st.progress(lp / 100)
    st.caption(f"Layer Progress: {lp}%")

    st.subheader("Activities")

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
                select_activity(row["activity_id"])

    # =========================
    # DETAILS (INLINE)
    # =========================
    st.markdown("---")

    aid = st.session_state.get("activity")

    if aid:
        act = activities[activities["activity_id"] == aid].iloc[0]

        st.subheader("Activity Details")
        st.markdown(f"### {act['activity_name']}")

        prog = progress(aid)
        status = derive_status(aid)

        c1, c2, c3, c4 = st.columns([2, 2, 4, 1])

        # OWNER
        with c1:
            st.caption("Owner")
            owner_options = ["Sam", "Marti"]
            current_owner = act["owner"]

            new_owner = st.selectbox(
                "",
                owner_options,
                index=owner_options.index(current_owner),
                key=f"owner_{aid}"
            )

            if new_owner != current_owner:
                supabase.table("activities").update(
                    {"owner": new_owner}
                ).eq("activity_id", aid).execute()

                st.cache_data.clear()
                st.rerun()

        # STATUS (derived)
        with c2:
            st.caption("Status")
            st.markdown(f"**{status}**")

        # PROGRESS
        with c3:
            st.caption("Progress")
            st.progress(prog / 100)

        # STORY POINTS
        with c4:
            st.caption("Story Points")
            st.markdown(f"### {act['story_points']}")

        # =========================
        # DELIVERABLES
        # =========================
        st.subheader("Deliverables")

        edit = st.toggle("Update Locations and Paths", key=f"edit_{aid}")

        rows_df = activity_details[activity_details["activity_id"] == aid]

        for _, row in rows_df.iterrows():
            c1, c2, c3, c4, c5 = st.columns(5)

            c1.write(row["artifact_name"])
            c2.write(row["artifact_type"])
            c3.write(row["format"])

            if edit:
                loc = c4.text_input(
                    "",
                    row["storage_location"],
                    key=f"loc_{row['row_id']}"
                )
                path = c5.text_input(
                    "",
                    row["path"],
                    key=f"path_{row['row_id']}"
                )

                if loc != row["storage_location"] or path != row["path"]:
                    supabase.table("activity_details").update({
                        "storage_location": loc,
                        "path": path
                    }).eq("row_id", row["row_id"]).execute()

                    st.cache_data.clear()
                    st.rerun()
            else:
                c4.write(row["storage_location"])
                c5.write(row["path"])

        # =========================
        # EXECUTION STEPS
        # =========================
        st.subheader("Execution Steps")

        headers = st.columns([2, 4, 4, 3, 2])
        headers[0].markdown("**Criteria**")
        headers[1].markdown("**Acceptance**")
        headers[2].markdown("**Meaning**")
        headers[3].markdown("**Measures**")
        headers[4].markdown("**Status**")

        for _, row in rows_df.iterrows():
            cols = st.columns([2, 4, 4, 3, 2])

            cols[0].write(row["criteria_category"])
            cols[1].write(row["acceptance_criteria"])
            cols[2].write(row["what_this_means"])
            cols[3].write(row["measures_and_success"])

            current_status = row["status"]

            new_status = cols[4].selectbox(
                "",
                ["Not Started", "In Progress", "Complete"],
                index=["Not Started", "In Progress", "Complete"].index(current_status),
                key=f"status_{row['row_id']}"
            )

            if new_status != current_status:
                supabase.table("activity_details").update(
                    {"status": new_status}
                ).eq("row_id", row["row_id"]).execute()

                st.cache_data.clear()
                st.rerun()