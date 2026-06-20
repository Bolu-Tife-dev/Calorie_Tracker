import os
import json
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# 1. SETUP & CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI Calorie Tracker", page_icon="🥗", layout="centered")

# Retrieve API key securely from environment variables or a text input
api_key = os.environ.get("GEMINI_API_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("Please enter your Gemini API Key in the sidebar to unlock the tracker.")
    st.markdown("👉 You can get a free key from [Google AI Studio](https://aistudio.google.com/)")
    st.stop()

# Initialize the Gemini Client
client = genai.Client(api_key=api_key)

# Initialize a simple session state memory to log food for the day
if "daily_log" not in st.session_state:
    st.session_state.daily_log = []

TARGET_CALORIES = 1850
TARGET_PROTEIN = 150

# -----------------------------------------------------------------------------
# 2. APP INTERFACE & BRANDING
# -----------------------------------------------------------------------------
st.title("🥗 Snapshot Calorie Tracker")
st.markdown("Snap or upload a photo of your meal to calculate and log calories and protein instantly.")

# Visual Dashboard for Daily Targets
total_cals = sum(item['calories'] for item in st.session_state.daily_log)
total_protein = sum(item['protein'] for item in st.session_state.daily_log)

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Calories Logged", value=f"{total_cals} / {TARGET_CALORIES} kcal", 
              delta=f"{TARGET_CALORIES - total_cals} remaining", delta_color="inverse")
with col2:
    st.metric(label="Protein Logged", value=f"{total_protein} / {TARGET_PROTEIN} g", 
              delta=f"{TARGET_PROTEIN - total_protein} remaining")

st.divider()

# -----------------------------------------------------------------------------
# 3. IMAGE INPUT & ADDITIONAL CONTEXT
# -----------------------------------------------------------------------------
input_method = st.radio("Choose Input Method:", ("Upload Image", "Use Camera"))

image = None
if input_method == "Use Camera":
    camera_img = st.camera_input("Take a photo of your meal")
    if camera_img:
        image = Image.open(camera_img)
else:
    uploaded_file = st.file_uploader("Choose a food image...", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        image = Image.open(uploaded_file)

# Text input for hidden ingredients (oils, butter, specific brands)
hidden_details = st.text_input(
    "Any hidden details? (Optional)", 
    placeholder="e.g., Cooked in 1 tbsp olive oil, full-fat Greek yogurt, etc."
)

# -----------------------------------------------------------------------------
# 4. AI VISION ANALYSIS
# -----------------------------------------------------------------------------
if image:
    st.image(image, caption="Target Meal", width=300)
    
    if st.button("Analyze & Log Meal", type="primary"):
        with st.spinner("AI is evaluating portion sizes and macros..."):
            
            # Crafting a structured system prompt to force a reliable JSON output
            prompt = f"""
            Analyze this food image. Identify the dishes, estimate their portion sizes/weights, 
            and calculate total calories and protein (in grams). 
            
            Additional context provided by the user: {hidden_details if hidden_details else "None"}
            
            You must return your response STRICTLY as a JSON object with exactly these three keys:
            - "food_name": (string, short description of the meal)
            - "calories": (integer, estimated total calories)
            - "protein": (integer, estimated total protein in grams)
            
            Do not include markdown formatting, backticks, or text outside the JSON object.
            """
            
            try:
                # Use the recommended model for multimodal tasks
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[image, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                # Parse the structured JSON response
                result = json.loads(response.text.strip())
                
                # Save to session history
                st.session_state.daily_log.append({
                    "name": result.get("food_name", "Unknown Meal"),
                    "calories": int(result.get("calories", 0)),
                    "protein": int(result.get("protein", 0))
                })
                
                st.success(f"Successfully logged: {result.get('food_name')}")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error parsing image: {e}")

# -----------------------------------------------------------------------------
# 5. DISPLAY LOGGED MEALS
# -----------------------------------------------------------------------------
if st.session_state.daily_log:
    st.subheader("Today's Food Log")
    for i, item in enumerate(st.session_state.daily_log):
        st.markdown(f"**{i+1}. {item['name']}** — 🔥 {item['calories']} kcal | 💪 {item['protein']}g protein")
    
    if st.button("Clear Log"):
        st.session_state.daily_log = []
        st.rerun()