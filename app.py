import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("OS Workbench")

st.markdown("### System Overview")

@st.cache_data
def load_data():
    layers = pd.read_csv("data/layers.csv")
    activities = pd.read_csv("data/activities.csv")
    activity_details = pd.read_csv("data/activity_details.csv")
    return layers, activities, activity_details

layers, activities, activity_details = load_data()

st.markdown("#### Layers")
st.dataframe(layers)

st.markdown("#### Activities")
st.dataframe(activities.head(20))
