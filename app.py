import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Simulated session state for demo purposes
if "manual_entries" not in st.session_state:
    st.session_state.manual_entries = []
if "manual_entry_mode" not in st.session_state:
    st.session_state.manual_entry_mode = False
if "manual_input" not in st.session_state:
    st.session_state.manual_input = ""
if "from_location" not in st.session_state:
    st.session_state.from_location = "Main Warehouse"
if "to_location" not in st.session_state:
    st.session_state.to_location = "OTT19001"

# UI setup
st.title("📦 Parts Transfer")

# Location selectors
st.subheader("From Location")
st.selectbox("", ["Main Warehouse", "Secondary Warehouse"], key="from_location")

st.subheader("To Location")
st.selectbox("", ["OTT19001", "OTT19002", "OTT19003"], key="to_location")

# Toggle manual entry mode
if not st.session_state.manual_entry_mode:
    if st.button("⌨️ Manual Entry Mode - Type part numbers", key="manual_toggle"):
        st.session_state.manual_entry_mode = True
        st.rerun()
else:
    st.subheader("Enter part number or QR code")

    # Capture input
    manual_input = st.text_input("Type part number here", value=st.session_state.manual_input, key="manual_input", label_visibility="collapsed")

    # Check if Enter was pressed
    if manual_input and manual_input != st.session_state.manual_input:
        part_number = manual_input.strip()
        st.session_state.manual_entries.append({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "From": st.session_state.from_location,
            "To": st.session_state.to_location,
            "Part Number": part_number
        })
        st.session_state.manual_input = part_number  # Store the last entered value
        time.sleep(0.1)  # Small delay to avoid input race conditions
        st.rerun()

    # Show added entries
    if st.session_state.manual_entries:
        st.write("### 📝 Recently Added Parts")
        st.dataframe(pd.DataFrame(st.session_state.manual_entries))

    # Exit manual mode
    if st.button("❌ Close Manual Entry", key="manual_close"):
        st.session_state.manual_entry_mode = False
        st.session_state.manual_input = ""
        st.rerun()

# Regular part scan section (placeholder)
st.write("## 📱 Add Parts")
# Additional functionality can be added below
