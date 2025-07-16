import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
import time
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
if 'last_scanned_code' not in st.session_state:
    st.session_state.last_scanned_code = ""
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = 0
if 'scanning_mode' not in st.session_state:
    st.session_state.scanning_mode = None
if 'scan_feedback_active' not in st.session_state:
    st.session_state.scan_feedback_active = False
if 'scan_feedback_time' not in st.session_state:
    st.session_state.scan_feedback_time = 0

# Scan cooldown and feedback duration
SCAN_COOLDOWN = 2.0  # 2 seconds
FEEDBACK_DURATION = 2.0  # Exactly 2 seconds

def add_part(barcode):
    """Add or update part in the list"""
    if not barcode or len(barcode.strip()) < 2:
        st.error("Invalid QR code")
        return False
    
    barcode = barcode.strip().upper()
    current_time = time.time()
    
    # Check if we're in feedback period
    if st.session_state.scan_feedback_active:
        return False
    
    # Allow same code after feedback period expires (no cooldown for same code)
    # Only prevent rapid duplicate scans within the feedback period
    
    st.session_state.last_scanned_code = barcode
    st.session_state.last_scan_time = current_time
    
    # Activate scan feedback
    st.session_state.scan_feedback_active = True
    st.session_state.scan_feedback_time = current_time
    
    # Check if part already exists
    for part in st.session_state.parts:
        if part['barcode'] == barcode:
            part['quantity'] += 1
            return True
    
    # Add new part
    st.session_state.parts.append({
        'barcode': barcode,
        'quantity': 1,
        'timestamp': datetime.now()
    })
    return True

def check_feedback_timeout():
    """Check if feedback period has expired"""
    if st.session_state.scan_feedback_active:
        current_time = time.time()
        if current_time - st.session_state.scan_feedback_time > FEEDBACK_DURATION:
            st.session_state.scan_feedback_active = False
            st.rerun()

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
    st.session_state.last_scanned_code = ""
    st.session_state.last_scan_time = 0
    st.session_state.scanning_mode = None
    st.session_state.scan_feedback_active = False
    st.session_state.scan_feedback_time = 0

# CSS for better UI and mobile compatibility
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
        -webkit-tap-highlight-color: transparent;
    }
    .scanning-section {
        border: 3px solid #2196F3;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        background-color: #f0f8ff;
        position: relative;
    }
    .scanner-active {
        border-color: #4CAF50;
        background-color: #f8fff8;
    }
    .mode-selector {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .scan-feedback {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(76, 175, 80, 0.95);
        color: white;
        padding: 20px;
        border-radius: 15px;
        font-size: 1.5rem;
        font-weight: bold;
        text-align: center;
        z-index: 1000;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        animation: scanSuccess 0.5s ease-out;
    }
    @keyframes scanSuccess {
        0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0; }
        100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
    }
    .scan-feedback.success {
        background: rgba(76, 175, 80, 0.95);
    }
    .scan-feedback.update {
        background: rgba(33, 150, 243, 0.95);
    }
    /* Mobile-specific improvements */
    @media (max-width: 768px) {
        .stTextInput > div > div > input {
            font-size: 16px !important;
            -webkit-appearance: none;
            appearance: none;
            background-color: white;
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 12px;
        }
        .stTextInput > div > div > input:focus {
            border-color: #2196F3;
            outline: none;
        }
        .stButton > button {
            -webkit-tap-highlight-color: rgba(0,0,0,0);
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            touch-action: manipulation;
        }
    }
</style>
""", unsafe_allow_html=True)

# Vibration JavaScript for mobile
st.markdown("""
<script>
function triggerVibration() {
    if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200]);
    }
}
</script>
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
        if st.button("📷 Scan QR Code", type="primary" if st.session_state.scanning_mode == "qr" else "secondary"):
            st.session_state.scanning_mode = "qr"
            st.session_state.scan_feedback_active = False
            st.rerun()
    
    with col2:
        if st.button("⌨️ Manual Entry", type="primary" if st.session_state.scanning_mode == "manual" else "secondary"):
            st.session_state.scanning_mode = "manual"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# QR Code Scanning Section
if st.session_state.scanning_mode == "qr":
    # Check if feedback period has expired
    feedback_expired = check_feedback_timeout()
    
    with st.container():
        st.markdown('<div class="scanning-section scanner-active">', unsafe_allow_html=True)
        
        if not st.session_state.scan_feedback_active:
            st.info("📱 **QR Scanner Active** - Point camera at QR code")
            st.caption("⏱️ 2-second pause after each scan")
            
            # QR Code Scanner (only when not in feedback mode)
            qr_code = qrcode_scanner(key='qr_scanner_active')
            
            if qr_code:
                if add_part(qr_code):
                    # Trigger vibration
                    st.markdown('<script>triggerVibration();</script>', unsafe_allow_html=True)
                    # Don't rerun here - let the feedback show
        else:
            # Show scan feedback overlay
            st.info("📱 **QR Scanner Active** - Point camera at QR code")
            st.caption("⏱️ 2-second pause after each scan")
            
            # Still show the scanner component but it won't process new scans
            qrcode_scanner(key='qr_scanner_active')
            
            # Show feedback overlay
            part_found = False
            for part in st.session_state.parts:
                if part['barcode'] == st.session_state.last_scanned_code:
                    part_found = True
                    if part['quantity'] > 1:
                        st.markdown(f'''
                        <div class="scan-feedback update">
                            ✅ ITEM SCANNED<br>
                            <small>{part['barcode']}</small><br>
                            <small>Quantity: {part['quantity']}</small>
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''
                        <div class="scan-feedback success">
                            ✅ ITEM SCANNED<br>
                            <small>{part['barcode']}</small><br>
                            <small>Added successfully</small>
                        </div>
                        ''', unsafe_allow_html=True)
                    break
            
            if not part_found:
                st.markdown(f'''
                <div class="scan-feedback success">
                    ✅ ITEM SCANNED<br>
                    <small>{st.session_state.last_scanned_code}</small><br>
                    <small>Added successfully</small>
                </div>
                ''', unsafe_allow_html=True)
        
        # If feedback just expired, rerun to refresh scanner
        if feedback_expired:
            st.rerun()
        
        # Auto-refresh every 0.5 seconds during feedback to check timeout
        if st.session_state.scan_feedback_active:
            time.sleep(0.5)
            st.rerun()
        
        # Option to close scanner (with safety check)
        if st.button("❌ Close Scanner", key="close_scanner"):
            st.session_state.scanning_mode = None
            st.session_state.scan_feedback_active = False
            st.session_state.last_scanned_code = ""  # Clear to prevent accidental adds
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Manual Entry Section
elif st.session_state.scanning_mode == "manual":
    with st.container():
        st.markdown('<div class="scanning-section">', unsafe_allow_html=True)
        
        st.info("⌨️ **Manual Entry Mode** - Type part numbers")
        
        # Use a form for proper Enter key handling
        with st.form(key='manual_form', clear_on_submit=True):
            manual_code = st.text_input(
                "Enter part number or QR code", 
                placeholder="Type part number and press Enter",
                help="Enter any part number or QR code value"
            )
            
            # Add button
            submitted = st.form_submit_button("➕ Add Part", type="primary", use_container_width=True)
            
            if submitted and manual_code and manual_code.strip():
                if add_part(manual_code):
                    # Show success message
                    for part in st.session_state.parts:
                        if part['barcode'] == manual_code.strip().upper():
                            if part['quantity'] > 1:
                                st.success(f"✅ Updated: {part['barcode']} (qty: {part['quantity']})")
                            else:
                                st.success(f"✅ Added: {part['barcode']}")
                            break
                    st.rerun()
                elif manual_code.strip():
                    st.warning("Please enter a valid part number")
        
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
    if st.button("🚀 Complete Transfer", type="primary", use_container_width=True):
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
    if st.button("🔄 Clear All Parts", help="Emergency reset - clear all parts", use_container_width=True):
        reset_transfer()
        st.rerun()
