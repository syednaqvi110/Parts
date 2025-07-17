import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
import time

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
if 'scanning_mode' not in st.session_state:
    st.session_state.scanning_mode = None
if 'last_scanned_code' not in st.session_state:
    st.session_state.last_scanned_code = ""
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = 0
if 'closing_scanner' not in st.session_state:
    st.session_state.closing_scanner = False

# Scan cooldown to prevent rapid duplicate scans
SCAN_COOLDOWN = 1.5  # 1.5 seconds between same codes

def add_part(barcode, from_scanner=False):
    """Add or update part in the list"""
    if not barcode or len(barcode.strip()) < 2:
        if from_scanner:
            st.error("Invalid QR code")
        else:
            st.error("Invalid part number")
        return False
    
    barcode = barcode.strip().upper()
    current_time = time.time()
    
    # For scanner: prevent rapid duplicate scans but allow intentional repeats
    if from_scanner:
        if (barcode == st.session_state.last_scanned_code and 
            current_time - st.session_state.last_scan_time < SCAN_COOLDOWN):
            return False  # Too soon, ignore
        
        st.session_state.last_scanned_code = barcode
        st.session_state.last_scan_time = current_time
    
    # Check if part already exists
    for part in st.session_state.parts:
        if part['barcode'] == barcode:
            part['quantity'] += 1
            if from_scanner:
                st.success(f"🎯 Item: {barcode} scanned (Total qty: {part['quantity']})")
            else:
                st.success(f"✅ Updated: {barcode} (qty: {part['quantity']})")
            return True
    
    # Add new part
    st.session_state.parts.append({
        'barcode': barcode,
        'quantity': 1,
        'timestamp': datetime.now()
    })
    
    if from_scanner:
        st.success(f"🎯 Item: {barcode} scanned (Total qty: 1)")
    else:
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
    st.session_state.scanning_mode = None
    st.session_state.last_scanned_code = ""
    st.session_state.last_scan_time = 0
    st.session_state.closing_scanner = False

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
    .scanning-section {
        border: 3px solid #2196F3;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        background-color: #f0f8ff;
    }
    .scanner-active {
        border-color: #ff4444;
        background-color: #fff8f8;
    }
    .mode-selector {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    input[type="text"] {
        font-size: 16px !important;
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

# Input Method Selection
st.header("📱 Add Parts")

with st.container():
    st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
    
    # Mode selection buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📷 QR Scanner", type="primary" if st.session_state.scanning_mode == "qr_scanner" else "secondary"):
            st.session_state.scanning_mode = "qr_scanner"
            st.rerun()
    
    with col2:
        if st.button("⌨️ Manual Entry", type="primary" if st.session_state.scanning_mode == "manual" else "secondary"):
            st.session_state.scanning_mode = "manual"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# QR Scanner Section - WORKING VERSION
if st.session_state.scanning_mode == "qr_scanner":
    with st.container():
        st.markdown('<div class="scanning-section scanner-active">', unsafe_allow_html=True)
        
        st.info("📱 **QR Scanner Active** - Continuously scans QR codes")
        
        try:
            from streamlit_qrcode_scanner import qrcode_scanner
            
            # This is the working QR scanner that continuously scans
            qr_code = qrcode_scanner(key='qrcode_scanner')
            
            # Process scanned code immediately - but only if we're not closing the scanner
            if qr_code and not st.session_state.closing_scanner:
                if add_part(qr_code, from_scanner=True):
                    st.rerun()
                    
        except ImportError:
            st.error("❌ QR Scanner library not installed. Please install: pip install streamlit-qrcode-scanner")
            st.info("💡 Use Manual Entry mode instead")
        
        # Option to close scanner
        if st.button("❌ Close Scanner", key="close_scanner"):
            # Set flag to prevent processing any pending scans
            st.session_state.closing_scanner = True
            # Clear any pending scanner state to prevent duplicate processing
            st.session_state.scanning_mode = None
            # Force a clean state by clearing the scanner key
            if 'qrcode_scanner' in st.session_state:
                del st.session_state['qrcode_scanner']
            # Reset the closing flag for next time
            st.session_state.closing_scanner = False
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Manual Entry Section
elif st.session_state.scanning_mode == "manual":
    with st.container():
        st.markdown('<div class="scanning-section">', unsafe_allow_html=True)
        
        st.info("⌨️ **Manual Entry Mode** - Enter part numbers")
        
        # Auto-focus script
        st.markdown("""
        <script>
        setTimeout(function() {
            var inputs = document.querySelectorAll('input[type="text"]');
            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].placeholder && inputs[i].placeholder.includes('Type or scan')) {
                    inputs[i].focus();
                    break;
                }
            }
        }, 200);
        </script>
        """, unsafe_allow_html=True)
        
        # Form for Enter key support
        with st.form(key='manual_form', clear_on_submit=True):
            manual_code = st.text_input(
                "Enter/Scan part number", 
                placeholder="Type or scan part number then press Enter",
                help="Use keyboard or physical scanner"
            )
            
            col1, col2 = st.columns([3, 1])
            with col2:
                submitted = st.form_submit_button("Add Part", type="primary")
            
            if submitted and manual_code:
                if add_part(manual_code, from_scanner=False):
                    st.rerun()
        
        # Option to close manual entry
        if st.button("❌ Close Manual Entry", key="close_manual"):
            st.session_state.scanning_mode = None
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Show mode selection hint
if st.session_state.scanning_mode is None:
    st.info("👆 **Choose a method above** to start adding parts")

# Parts List Section
st.header("📋 Parts List")

if st.session_state.parts:
    # Summary
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
    st.info("No parts added yet - select a method above to start")

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
            
            # Auto-reset for new transfer
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
        missing.append("Add at least one part")
    
    if missing:
        st.warning(f"⚠️ **Required:** {', '.join(missing)}")

# Emergency reset button
if st.session_state.parts:
    st.divider()
    if st.button("🔄 Clear All Parts", help="Emergency reset - clear all parts"):
        reset_transfer()
        st.rerun()
