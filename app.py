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
    .qr-scanner-container {
        text-align: center;
        padding: 20px;
        border: 3px dashed #2196F3;
        border-radius: 10px;
        margin: 10px 0;
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

# QR Scanner Section - REAL-TIME SCANNING
if st.session_state.scanning_mode == "qr_scanner":
    with st.container():
        st.markdown('<div class="scanning-section scanner-active">', unsafe_allow_html=True)
        
        st.info("📱 **QR Scanner Active** - Point camera at QR codes")
        
        # HTML5 QR Scanner - Direct implementation
        st.markdown("""
        <div class="qr-scanner-container">
            <div id="qr-reader" style="width: 100%; max-width: 500px; margin: 0 auto; min-height: 300px; display: flex; align-items: center; justify-content: center;">
                <div id="loading-message" style="text-align: center; color: #666;">
                    📱 Requesting camera access...<br>
                    <small>Please allow camera permission when prompted</small>
                </div>
            </div>
        </div>
        
        <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
        <script>
            let html5QrCode;
            let isScanning = false;
            let scannerStarted = false;
            
            function updateStatus(message, isError = false) {
                const loadingDiv = document.getElementById('loading-message');
                if (loadingDiv) {
                    loadingDiv.innerHTML = message;
                    loadingDiv.style.color = isError ? 'red' : '#666';
                }
            }
            
            function startScanner() {
                if (isScanning || scannerStarted) return;
                
                console.log("Initializing QR Scanner...");
                updateStatus("🔄 Initializing camera...");
                
                html5QrCode = new Html5Qrcode("qr-reader");
                
                const qrCodeSuccessCallback = (decodedText, decodedResult) => {
                    console.log('QR Code scanned:', decodedText);
                    
                    // Add scanned code to hidden input
                    const hiddenInput = document.getElementById('scanned_code_input');
                    if (hiddenInput) {
                        hiddenInput.value = decodedText;
                        hiddenInput.dispatchEvent(new Event('input', { bubbles: true }));
                        
                        // Brief success feedback
                        updateStatus("✅ Code scanned: " + decodedText.substring(0, 20) + "...");
                        setTimeout(() => {
                            updateStatus("📱 Scanner active - Point camera at QR codes");
                        }, 1500);
                    }
                    
                    // Trigger vibration if available
                    if (navigator.vibrate) {
                        navigator.vibrate([200, 100, 200]);
                    }
                };
                
                const config = { 
                    fps: 10, 
                    qrbox: { width: 250, height: 250 },
                    aspectRatio: 1.0,
                    disableFlip: false
                };
                
                // First check for camera permissions
                navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
                    .then(function(stream) {
                        // Permission granted, stop the test stream
                        stream.getTracks().forEach(track => track.stop());
                        
                        // Now start the actual QR scanner
                        updateStatus("📱 Starting QR scanner...");
                        
                        html5QrCode.start(
                            { facingMode: "environment" }, 
                            config, 
                            qrCodeSuccessCallback
                        ).then(() => {
                            isScanning = true;
                            scannerStarted = true;
                            updateStatus("📱 Scanner active - Point camera at QR codes");
                            console.log("QR Scanner started successfully");
                        }).catch(err => {
                            console.error("QR Scanner start error:", err);
                            updateStatus("❌ Scanner failed to start: " + err.message, true);
                        });
                    })
                    .catch(function(err) {
                        console.error("Camera permission error:", err);
                        let errorMsg = "❌ Camera access required<br>";
                        
                        if (err.name === 'NotAllowedError') {
                            errorMsg += "Please allow camera access and click 'Restart Scanner'";
                        } else if (err.name === 'NotFoundError') {
                            errorMsg += "No camera found on this device";
                        } else if (err.name === 'NotSupportedError') {
                            errorMsg += "Camera not supported in this browser";
                        } else {
                            errorMsg += "Error: " + err.message;
                        }
                        
                        updateStatus(errorMsg, true);
                    });
            }
            
            function stopScanner() {
                if (html5QrCode && isScanning) {
                    html5QrCode.stop().then(() => {
                        isScanning = false;
                        scannerStarted = false;
                        console.log("QR Scanner stopped");
                        updateStatus("Scanner stopped");
                    }).catch(err => {
                        console.error("Error stopping scanner:", err);
                    });
                }
            }
            
            // Auto-start scanner when the section loads
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(startScanner, 500);
                });
            } else {
                setTimeout(startScanner, 500);
            }
            
            // Stop scanner when page unloads
            window.addEventListener('beforeunload', stopScanner);
            
            // Expose functions globally for button access
            window.restartQRScanner = function() {
                stopScanner();
                setTimeout(startScanner, 1000);
            };
            
            window.stopQRScanner = stopScanner;
        </script>
        """, unsafe_allow_html=True)
        
        # Hidden input to capture scanned results
        scanned_code = st.text_input(
            "Scanned code will appear here",
            placeholder="Waiting for scan result...",
            key="scanned_result",
            label_visibility="hidden"
        )
        
        # Add JavaScript to connect scanner to input
        st.markdown("""
        <script>
            // Connect the scanner output to the Streamlit input
            const observer = new MutationObserver(function(mutations) {
                const input = document.querySelector('input[data-testid="stTextInput-scanned_result"]');
                if (input && !input.id) {
                    input.id = 'scanned_code_input';
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        </script>
        """, unsafe_allow_html=True)
        
        # Process scanned code
        if scanned_code and scanned_code.strip():
            if add_part(scanned_code, from_scanner=True):
                # Clear the input and continue scanning
                st.session_state.scanned_result = ""
                st.rerun()
        
        # Scanner controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Restart Scanner", key="restart_scanner"):
                st.markdown("""
                <script>
                    if (window.restartQRScanner) {
                        window.restartQRScanner();
                    }
                </script>
                """, unsafe_allow_html=True)
        
        with col2:
            if st.button("❌ Close Scanner", key="close_scanner"):
                st.markdown("""
                <script>
                    if (window.stopQRScanner) {
                        window.stopQRScanner();
                    }
                </script>
                """, unsafe_allow_html=True)
                st.session_state.scanning_mode = None
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
