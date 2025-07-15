import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
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
if 'last_scanned' not in st.session_state:
    st.session_state.last_scanned = ""

def add_part(barcode):
    """Add or update part in the list"""
    if not barcode or len(barcode.strip()) < 2:
        st.error("Invalid barcode")
        return False
    
    barcode = barcode.strip().upper()
    
    # Prevent duplicate rapid scans
    if barcode == st.session_state.last_scanned:
        return False
    
    st.session_state.last_scanned = barcode
    
    # Check if part already exists
    for part in st.session_state.parts:
        if part['barcode'] == barcode:
            part['quantity'] += 1
            st.success(f"✅ Updated: {barcode} (qty: {part['quantity']})")
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

def save_transfer_data(from_location, to_location, parts_data):
    """Save transfer to Google Sheets"""
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

def reset_transfer():
    """Reset everything for new transfer"""
    st.session_state.parts = []
    st.session_state.transfer_complete = False
    st.session_state.last_scanned = ""

# CSS for better UI
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
    .scanner-container {
        border: 3px solid #4CAF50;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        background-color: #f8fffe;
    }
    .scanner-active {
        border-color: #ff4444;
        background-color: #fff8f8;
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

# Real-time Barcode Scanner Section
st.header("🎯 Live Barcode Scanner")

# Scanner container with styling
with st.container():
    st.markdown('<div class="scanner-container">', unsafe_allow_html=True)
    
    st.info("📱 **Live Scanner Active** - Point camera at barcode to scan automatically")
    
    # Real-time QR/Barcode Scanner
    qr_code = qrcode_scanner(key='live_scanner')
    
    if qr_code:
        # Auto-add scanned barcode
        if add_part(qr_code):
            # Clear the last scanned to allow rescanning same item
            st.session_state.last_scanned = ""
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Manual Entry Section (Backup)
st.header("⌨️ Manual Entry")

# Form for Enter key support
with st.form(key='barcode_form', clear_on_submit=True):
    manual_barcode = st.text_input(
        "Type barcode here", 
        placeholder="Enter part number and press Enter",
        help="Backup method if camera scanning doesn't work"
    )
    
    submitted = st.form_submit_button("Add Part", type="secondary")
    
    if submitted and manual_barcode:
        if add_part(manual_barcode):
            st.rerun()

# Parts List Section
st.header("📋 Parts List")

if st.session_state.parts:
    # Summary at top
    total_items = sum(p['quantity'] for p in st.session_state.parts)
    st.info(f"📊 **{total_items} total items** • **{len(st.session_state.parts)} different parts**")
    
    # Parts display
    for i, part in enumerate(st.session_state.parts):
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 1])
            
            with col1:
                st.write(f"**{part['barcode']}**")
            
            with col2:
                # Quantity controls
                qty_col1, qty_col2, qty_col3 = st.columns([1, 2, 1])
                with qty_col1:
                    if st.button("➖", key=f"dec_{i}", help="Decrease"):
                        if part['quantity'] > 1:
                            update_quantity(i, part['quantity'] - 1)
                            st.rerun()
                
                with qty_col2:
                    st.write(f"**{part['quantity']}**")
                
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
    st.info("No parts scanned yet - use the live scanner above")

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
        
        if save_transfer_data(from_location, to_location, parts_data):
            st.success(f"✅ **Transfer Completed!** {sum(p['quantity'] for p in st.session_state.parts)} items transferred")
            st.balloons()
            
            # Auto-reset for new transfer (no separate button needed)
            reset_transfer()
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
        st.warning(f"⚠️ **Required:** {', '.join(missing)}")

# Quick reset button (for emergencies)
if st.session_state.parts:
    if st.button("🔄 Clear All Parts", help="Emergency reset - clear all scanned parts"):
        reset_transfer()
        st.rerun()
