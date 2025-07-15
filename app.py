import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
from PIL import Image

# Configure page
st.set_page_config(
    page_title="Parts Transfer Scanner",
    page_icon="📦",
    layout="centered"
)

# Google Sheets URL (replace with your actual URL)
GOOGLE_SHEETS_URL = 'https://script.google.com/macros/s/AKfycbyCVe8VytbR-UqcXEcshlfbbVf6cG3Y61PfP3hnpZPY1QvIDxIUALpB2_StHCf4MC3VZA/exec'

# Initialize session state
if 'parts' not in st.session_state:
    st.session_state.parts = []
if 'transfer_complete' not in st.session_state:
    st.session_state.transfer_complete = False

def add_part(barcode):
    """Add or update part in the list"""
    if not barcode or len(barcode.strip()) < 2:
        st.error("Invalid barcode")
        return False
    
    barcode = barcode.strip().upper()
    
    # Check if part already exists
    for part in st.session_state.parts:
        if part['barcode'] == barcode:
            part['quantity'] += 1
            st.success(f"Updated: {barcode} (qty: {part['quantity']})")
            return True
    
    # Add new part
    st.session_state.parts.append({
        'barcode': barcode,
        'quantity': 1,
        'timestamp': datetime.now()
    })
    st.success(f"Added: {barcode}")
    return True

def remove_part(index):
    """Remove part from list"""
    if 0 <= index < len(st.session_state.parts):
        removed = st.session_state.parts.pop(index)
        st.success(f"Removed: {removed['barcode']}")

def update_quantity(index, new_qty):
    """Update part quantity"""
    if 0 <= index < len(st.session_state.parts) and new_qty > 0:
        st.session_state.parts[index]['quantity'] = new_qty

def save_transfer(from_location, to_location, parts):
    """Save transfer to Google Sheets"""
    try:
        transfer_data = {
            'timestamp': datetime.now().isoformat(),
            'fromLocation': from_location,
            'toLocation': to_location,
            'parts': [{'barcode': p['barcode'], 'quantity': p['quantity']} for p in parts],
            'totalParts': sum(p['quantity'] for p in parts),
            'partTypes': len(parts)
        }
        
        response = requests.post(
            GOOGLE_SHEETS_URL,
            json=transfer_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        return True
    except Exception as e:
        st.error(f"Save failed: {str(e)}")
        return False

# Main App
st.title("📦 Parts Transfer Scanner")

# Transfer Details Section
st.header("📍 Transfer Details")
col1, col2 = st.columns(2)

with col1:
    from_location = st.text_input("From Location *", placeholder="e.g., Main Warehouse")

with col2:
    to_location = st.text_input("To Location *", placeholder="e.g., OTT19001")

# Scanner Section
st.header("🎯 Barcode Entry")

# Photo upload for reference
st.subheader("📷 Upload Photo (Optional)")
uploaded_file = st.file_uploader(
    "Take photo of barcode for reference",
    type=['png', 'jpg', 'jpeg'],
    help="Upload a photo to help verify the barcode"
)

if uploaded_file:
    image = Image.open(uploaded_file)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(image, caption="Barcode Photo", use_column_width=True)
    st.info("👆 Now type the barcode from this image below")

# Manual Entry
st.subheader("⌨️ Enter Barcode")
manual_barcode = st.text_input("Type barcode here", placeholder="Scan or type barcode")

if st.button("Add Part", type="primary", disabled=not manual_barcode):
    if add_part(manual_barcode):
        st.rerun()

# Parts List Section
st.header("📋 Scanned Parts")

if st.session_state.parts:
    # Display parts with edit capabilities
    for i, part in enumerate(st.session_state.parts):
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.write(f"**{part['barcode']}**")
        
        with col2:
            new_qty = st.number_input(
                "Qty", 
                min_value=1, 
                max_value=999, 
                value=part['quantity'],
                key=f"qty_{i}"
            )
            if new_qty != part['quantity']:
                update_quantity(i, new_qty)
        
        with col3:
            if st.button("➕", key=f"inc_{i}", help="Increase quantity"):
                update_quantity(i, part['quantity'] + 1)
                st.rerun()
        
        with col4:
            if st.button("🗑️", key=f"del_{i}", help="Remove part"):
                remove_part(i)
                st.rerun()
        
        st.divider()
    
    # Summary
    total_items = sum(p['quantity'] for p in st.session_state.parts)
    part_types = len(st.session_state.parts)
    
    st.info(f"📊 **Summary:** {total_items} total items • {part_types} different parts")
    
else:
    st.info("No parts added yet")

# Complete Transfer Section
st.header("✅ Complete Transfer")

can_complete = (
    from_location and 
    to_location and 
    st.session_state.parts and 
    not st.session_state.transfer_complete
)

if st.button(
    "Complete Transfer", 
    type="primary", 
    disabled=not can_complete,
    use_container_width=True
):
    if save_transfer(from_location, to_location, st.session_state.parts):
        st.success(f"✅ Transfer completed! {sum(p['quantity'] for p in st.session_state.parts)} items transferred")
        st.session_state.transfer_complete = True
        
        # Auto-reset after success
        st.balloons()
        
        if st.button("Start New Transfer", type="secondary", use_container_width=True):
            st.session_state.parts = []
            st.session_state.transfer_complete = False
            st.rerun()

# Validation messages
if not can_complete and not st.session_state.transfer_complete:
    missing = []
    if not from_location:
        missing.append("From Location")
    if not to_location:
        missing.append("To Location")
    if not st.session_state.parts:
        missing.append("At least one part")
    
    if missing:
        st.warning(f"Please provide: {', '.join(missing)}")

# Reset button
if st.session_state.parts:
    st.divider()
    if st.button("🔄 Reset All", help="Clear all data and start over"):
        st.session_state.parts = []
        st.session_state.transfer_complete = False
        st.rerun()
