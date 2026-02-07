"""
ShopStream - Billing Engine Testbed
A Streamlit application for testing multi-tenant billing workflows with Supabase
"""

import streamlit as st
import time
import uuid
from datetime import datetime
from supabase import create_client, Client

# ============================================================================
# CONFIGURATION
# ============================================================================

def init_supabase() -> Client:
    """Initialize Supabase client using secrets with corrected parameters"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    # FIXED: Direct initialization to avoid version-specific keyword issues
    return create_client(url, key)

# ============================================================================
# FINANCIAL GUARD CONTEXT MANAGER
# ============================================================================

class monitor_guard:
    """
    Context manager for tracking billable operations.
    Wraps Agent execution to produce 'Financial Spans' for Revgate.
    """
    def __init__(self, entity_id: str, product_key: str, revenue_potential: float):
        self.entity_id = entity_id
        self.product_key = product_key
        self.revenue_potential = revenue_potential
        self.transaction_id = str(uuid.uuid4())
        self.supabase = init_supabase()
        
    def __enter__(self):
        st.toast(f"🔍 Tracking started: {self.product_key} (${self.revenue_potential:.2f})")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # State Machine Logic: 
        # Code Failure -> VOIDED | Success -> PROVISIONAL
        status = "VOIDED" if exc_type is not None else "PROVISIONAL"
        self._log_transaction(status)
        return False # Ensure exceptions are still raised for QA visibility
    
    def _log_transaction(self, status: str):
        try:
            transaction = {
                "id": self.transaction_id,
                "entity_id": self.entity_id,
                "product_key": self.product_key,
                "status": status,
                "revenue": self.revenue_potential,
                "created_at": datetime.utcnow().isoformat()
            }
            self.supabase.table("transactions").insert(transaction).execute()
        except Exception as e:
            st.error(f"Failed to log transaction: {e}")

# ============================================================================
# BUSINESS LOGIC & QA UTILITIES
# ============================================================================

def add_product_listing(entity_id: str, fail: bool):
    with monitor_guard(entity_id, "listing", 0.10):
        time.sleep(0.5)
        if fail: raise Exception("Forced Listing Failure")
        st.success("✅ Listing added!")

def generate_smart_copy(entity_id: str, fail: bool):
    with monitor_guard(entity_id, "smart_copy", 1.00):
        with st.spinner("🤖 AI thinking..."):
            time.sleep(1.5)
        if fail: raise Exception("Forced AI Generation Failure")
        st.success("✅ AI Copy ready!")

def brand_safety_check(entity_id: str, fail: bool):
    with monitor_guard(entity_id, "brand_guard", 5.00):
        with st.spinner("🛡️ Analyzing..."):
            time.sleep(2.0)
        if fail: raise Exception("Forced Safety Guard Failure")
        st.success("✅ Safety check passed!")

def run_batch(op_func, entity_id: str, count: int, fail: bool):
    success, failure = 0, 0
    p_bar = st.progress(0)
    for i in range(count):
        try:
            op_func(entity_id, fail)
            success += 1
        except:
            failure += 1
        p_bar.progress((i + 1) / count)
    st.success(f"🎯 Batch: {success} Success, {failure} Fail")

# ============================================================================
# MAIN UI
# ============================================================================

def main():
    st.set_page_config(page_title="ShopStream - Revgate Testbed", layout="wide")
    st.title("🛒 ShopStream: Billing Engine Testbed")
    
    with st.sidebar:
        st.header("⚙️ Config & QA")
        entity_id = st.selectbox("Client", ["Test Shop A", "Test Shop B"])
        force_fail = st.toggle("⚡ Force Code Failure")
        batch_size = st.slider("🔥 Stress Test Size", 1, 20, 5)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📦 Listing ($0.10)")
        if st.button("➕ Add Listing"): add_product_listing(entity_id, force_fail)
        if st.button("🔥 Batch Listings"): run_batch(add_product_listing, entity_id, batch_size, force_fail)

    with col2:
        st.markdown("### ✨ Smart Copy ($1.00)")
        if st.button("🤖 Generate Copy"): generate_smart_copy(entity_id, force_fail)
        if st.button("🔥 Batch Copy"): run_batch(generate_smart_copy, entity_id, batch_size, force_fail)

    with col3:
        st.markdown("### 🛡️ Brand Safety ($5.00)")
        if st.button("🔍 Safety Check"): brand_safety_check(entity_id, force_fail)
        if st.button("🔥 Batch Safety"): run_batch(brand_safety_check, entity_id, batch_size, force_fail)

    st.divider()
    st.header("🗂️ Ingestion Audit (Last 5)")
    try:
        supabase = init_supabase()
        txs = supabase.table("transactions").select("*").order("created_at", desc=True).limit(5).execute().data
        for tx in txs:
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{tx['status']}**: {tx['product_key']} | ID: {tx['entity_id']} | ${tx['revenue']}")
            if tx['status'] == "PROVISIONAL" and c2.button("🚫 Void", key=tx['id']):
                supabase.table("transactions").update({"status": "VOIDED"}).eq("id", tx['id']).execute()
                st.rerun()
    except Exception:
        st.info("Log in to Supabase to see recent transactions.")

if __name__ == "__main__":
    main()
