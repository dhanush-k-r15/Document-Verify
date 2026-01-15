import streamlit as st
import google.generativeai as genai
import PIL.Image
import json
import re

# --- 1. CONFIGURATION ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Add your API Key to .streamlit/secrets.toml first!")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-latest')

# --- 2. GOVERNANCE: Fixed Regex Logic ---
def check_id_format(id_val, doc_type):
    # Clean up spaces/hyphens for strict matching
    clean_id = re.sub(r'[\s-]', '', str(id_val))
    
    if "aadhaar" in doc_type.lower():
        # Aadhaar: 12 digits, doesn't start with 0 or 1
        return bool(re.match(r'^[2-9]{1}[0-9]{11}$', clean_id))
    elif "pan" in doc_type.lower():
        # PAN: 5 letters, 4 digits, 1 letter
        return bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', clean_id.upper()))
    return True

# Utility to safely grab JSON from AI text
def extract_json(text):
    try:
        # Look for JSON block if AI adds conversational text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except:
        return None

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="FlashVerify AI", layout="wide")
st.title("🛡️ FlashVerify: Indian ID Intelligence")
st.markdown("---")

uploaded_file = st.file_uploader("Scan Aadhaar or PAN Card", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    # IMPORTANT: Keep 'img' as a PIL object for Gemini
    img = PIL.Image.open(uploaded_file)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(img, caption="Input Scan", use_container_width=True)

    with col2:
        with st.spinner("AI Analysis in progress..."):
            prompt = """
            Identify this ID and extract data. Return ONLY JSON:
            {
              "name": "Full Name",
              "id_num": "ID Number",
              "doc_type": "Aadhaar/PAN",
              "lang": "Detected Language",
              "tamper": "Low/Medium/High",
              "reason": "Note on authenticity"
            }
            """
            try:
                # FIX: Passing PIL 'img' directly resolves the Blob error
                response = model.generate_content([prompt, img])
                res = extract_json(response.text)
                
                if res:
                    # Run Code-Based Governance
                    is_valid = check_id_format(res['id_num'], res['doc_type'])
                    
                    st.subheader(f"ID Type: {res['doc_type']}")
                    st.write(f"**Name:** {res['name']}")
                    st.write(f"**ID Number:** {res['id_num']}")
                    st.write(f"**Language:** {res['lang']}")
                    
                    if is_valid and res['tamper'] == "Low":
                        st.success("✅ DOCUMENT VERIFIED")
                        st.balloons()
                    else:
                        st.error(f"🚨 ALERT: {res['reason']}")
                        if not is_valid:
                            st.warning(f"Note: ID format for {res['doc_type']} is mathematically invalid.")
                    
                    with st.expander("Technical Audit Logs"):
                        st.json(res)
                else:
                    st.error("AI couldn't structure the data. Please try a clearer photo.")
            
            except Exception as e:
                st.error(f"System Error: {e}")
