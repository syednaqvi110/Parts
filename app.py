import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
from PIL import Image
from streamlit_qrcode_scanner import qrcode_scanner

# Configure page
st.set_page_config(
    page_title="Parts Transfer Scanner",
    page_icon="📦",
    layout="centered"
)

# Google Sheets URL
GOOGLE_SHEETS_URL = 'https://script.google.com/macros/s/AKfycbyCVe8VytbR-UqcXEcshlfbbVf6cG3Y61PfP3hnpZPY1QvIDxIUALpB2_StHCf4MC3VZA/exec'

# Initialize session state
if 'parts' not in st.session_state:
    st.session_state.parts = []
if 'transfer_complete' not in st.session_state:
    st.session_state.transfer_complete = False

@st.cache_data
def get_empty_dataframe():
    """Cached empty dataframe for performance"""
    return pd.DataFrame(columns=['barcode', 'quantity'])

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
            st.success(f"✅ {barcode} (qty: {part['quantity']})")
            return True
    
    # Add new part
    st.session_state.parts.append({
        'barcode': barcode,
        'quantity': 1,
        'timestamp': datetime.now()
    })
    st.success(f"✅ Added: {barcode}")
    return True

def remove_part(index):
    """Remove part from list"""
    if 0 <= index < len(st.session_state.parts):
        removed = st.session_state.parts.pop(index)
        st.success(f"🗑️ Removed: {removed['barcode']}")

def update_quantity(index, new_qty):
    """Update part quantity"""
    if 0 <= index < len(st.session_state.parts) and new_qty > 0:
        st.session_state.parts[index]['quantity'] = new_qty

@st.cache_data
def save_transfer(from_location, to_location, parts_data):
    """Save transfer to Google Sheets with caching"""
    try:
        transfer_data = {
            'timestamp': datetime.now().isoformat(),
            'fromLocation': from_location,
            'toLocation': to_location,
            'parts': parts_data,
            'totalParts': sum(p['quantity'] for p in parts_data),
            'partTypes': len(parts_data)
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

# CSS for faster loading and better UI
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .scan-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
    }
    .quantity-control {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Main App
st.title("📦 Parts Transfer")

# Transfer Details Section
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        from_location = st.text_input("From Location", placeholder="Main Warehouse")
    with col2:
        to_location = st.text_input("To Location", placeholder="OTT19001")

# Real-time Scanner Section
st.header("🎯 Live Barcode Scanner")

# Live QR/Barcode Scanner
if st.checkbox("📱 Start Live Scanner", key="scanner_toggle"):
    qr_code = qrcode_scanner(key='qrcode_scanner')
    
    if qr_code:
        # Auto-add scanned barcode
        if add_part(qr_code):
            # Clear the scanner by rerunning
            st.rerun()

# Manual Entry (for backup)
with st.expander("⌨️ Manual Entry", expanded=False):
    manual_col1, manual_col2 = st.columns([3, 1])
    with manual_col1:
        manual_barcode = st.text_input("Enter barcode", key="manual_input")
    with manual_col2:
        if st.button("Add", key="add_manual"):
            if manual_barcode and add_part(manual_barcode):
                st.session_state.manual_input = ""  # Clear input
                st.rerun()

# Parts List Section
st.header("📋 Parts List")

if st.session_state.parts:
    # Quick summary at top
    total_items = sum(p['quantity'] for p in st.session_state.parts)
    st.info(f"📊 {total_items} items • {len(st.session_state.parts)} types")
    
    # Compact parts display
    for i, part in enumerate(st.session_state.parts):
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 1])
            
            with col1:
                st.write(f"**{part['barcode']}**")
            
            with col2:
                # Quantity controls in one row
                qty_col1, qty_col2, qty_col3 = st.columns([1, 2, 1])
                with qty_col1:
                    if st.button("➖", key=f"dec_{i}", help="Decrease"):
                        if part['quantity'] > 1:
                            update_quantity(i, part['quantity'] - 1)
                            st.rerun()
                
                with qty_col2:
                    st.write(f"**{part['quantity']}**", key=f"qty_display_{i}")
                
                with qty_col3:
                    if st.button("➕", key=f"inc_{i}", help="Increase"):
                        update_quantity(i, part['quantity'] + 1)
                        st.rerun()
            
            with col3:
                if st.button("🗑️", key=f"del_{i}", help="Remove"):
                    remove_part(i)
                    st.rerun()
            
            if i < len(st.session_state.parts) - 1:
                st.divider()
else:
    st.info("No parts scanned yet")

# Complete Transfer Section
st.header("✅ Complete Transfer")

can_complete = (
    from_location and 
    to_location and 
    st.session_state.parts and 
    not st.session_state.transfer_complete
)

if can_complete:
    if st.button("🚀 Complete Transfer", type="primary"):
        parts_data = [{'barcode': p['barcode'], 'quantity': p['quantity']} for p in st.session_state.parts]
        
        if save_transfer(from_location, to_location, parts_data):
            st.success(f"✅ Transfer completed! {sum(p['quantity'] for p in st.session_state.parts)} items")
            st.balloons()
            st.session_state.transfer_complete = True
            
            # Auto-reset
            if st.button("🔄 New Transfer", type="secondary"):
                st.session_state.parts = []
                st.session_state.transfer_complete = False
                st.rerun()
else:
    # Show what's missing
    missing = []
    if not from_location:
        missing.append("From Location")
    if not to_location:
        missing.append("To Location")
    if not st.session_state.parts:
        missing.append("Scan at least one part")
    
    if missing:
        st.warning(f"Need: {', '.join(missing)}")

# Quick reset button
if st.session_state.parts and not st.session_state.transfer_complete:
    if st.button("🔄 Clear All", help="Reset everything"):
        st.session_state.parts = []
        st.rerun()
