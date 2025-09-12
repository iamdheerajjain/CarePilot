import json
import os
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from symptom_analyzer import analyze_symptom_patterns
from fine_tuned_detectors import suggest_fine_tuned_conditions, get_condition_recommendations as get_fine_tuned_recommendations
from triage import compute_triage
from feedback_learning import FeedbackLearningSystem
from supabase_client import get_supabase_client, sign_in_with_email, sign_up_with_email, sign_out, get_current_user, insert_row, is_email_confirmed, is_user_authenticated, refresh_session_if_needed

APP_TITLE = "CarePilot: Quick Medical Triage (Non-Diagnostic)"
STORAGE_DIR = os.path.join("storage")
FEEDBACK_PATH = os.path.join(STORAGE_DIR, "feedback.jsonl")
RESOURCES_PATH = os.path.join("data", "resources.json")


def ensure_dirs() -> None:
	os.makedirs(STORAGE_DIR, exist_ok=True)


def load_resources() -> Dict[str, Any]:
	try:
		with open(RESOURCES_PATH, "r", encoding="utf-8") as f:
			return json.load(f)
	except FileNotFoundError:
		return {"general": [], "conditions": {}}


def disclaimer() -> None:
	st.markdown("**Educational only**: This app does not provide medical diagnoses or treatment. In an emergency, call your local emergency number.")
	st.markdown("By continuing, you agree that you understand this limitation and consent to non-diagnostic guidance.")




def render_suggestions(symptoms_text: str, resources: Dict[str, Any], age: int = None, duration_hours: float = None, medical_history: str = "") -> List[Dict[str, Any]]:
	if not symptoms_text.strip():
		st.warning("Please enter your symptoms.")
		st.stop()

	with st.spinner("Analyzing symptoms with fine-tuned medical AI..."):
		# Get fine-tuned predictions optimized for both simple and complex inputs
		preds = suggest_fine_tuned_conditions(symptoms_text, k=5, age=age, duration_hours=duration_hours, medical_history=medical_history)
		
		# Apply feedback learning adjustments
		feedback_system = FeedbackLearningSystem()
		preds = feedback_system.apply_learning_adjustments(symptoms_text, preds)

	if not preds:
		st.info("No suggestions yet. Try adding more details.")
		return []

	# Enhanced display with confidence indicators
	st.subheader("Possible conditions (not a diagnosis)")
	
	# Calculate confidence level
	scores = [p["score"] for p in preds]
	max_score = max(scores)
	score_range = max_score - min(scores)
	
	# Confidence assessment
	if max_score >= 0.8 and score_range >= 0.3:
		confidence_level = "High"
		confidence_color = "🟢"
		confidence_message = "Strong pattern match detected"
	elif max_score >= 0.6 and score_range >= 0.2:
		confidence_level = "Moderate"
		confidence_color = "🟡"
		confidence_message = "Good pattern match detected"
	elif max_score >= 0.4:
		confidence_level = "Low"
		confidence_color = "🟠"
		confidence_message = "Weak pattern match - more details needed"
	else:
		confidence_level = "Very Low"
		confidence_color = "🔴"
		confidence_message = "Very weak pattern match - please provide more details"
	
	# Display confidence indicator
	st.markdown(f"**Confidence Level:** {confidence_color} {confidence_level} - {confidence_message}")
	
	# Enhanced chart and table view
	chart_cols = st.columns([2, 1])
	with chart_cols[0]:
		# Create enhanced chart with confidence colors
		chart_data = {
			"Condition": [p["condition"].title() for p in preds],
			"Score": [round(p["score"], 3) for p in preds],
		}
		st.bar_chart(chart_data, x="Condition", height=220)
	
	with chart_cols[1]:
		# Enhanced table with confidence indicators
		table_data = {
			"Condition": [p["condition"].title() for p in preds],
			"Score": [round(p["score"], 3) for p in preds],
			"Confidence": [
				"🟢 High" if score >= 0.7 else 
				"🟡 Moderate" if score >= 0.5 else 
				"🟠 Low" if score >= 0.3 else 
				"🔴 Very Low" 
				for score in scores
			]
		}
		st.dataframe(table_data, hide_index=True, use_container_width=True)

	# Enhanced feedback based on scores
	if max_score < 0.5 or score_range < 0.1:
		st.warning("⚠️ **Low Confidence Warning:** Scores are low or very similar. This often happens when symptom descriptions are brief or ambiguous.")
		st.info("💡 **Tips for better results:**\n- Include onset timing (sudden, gradual, etc.)\n- Describe severity (mild, moderate, severe)\n- Mention triggers or associated symptoms\n- Add duration and any pattern changes")
	elif max_score >= 0.8:
		st.success("✅ **High Confidence:** Strong pattern match detected. The top suggestion is highly relevant.")
	elif max_score >= 0.6:
		st.info("ℹ️ **Moderate Confidence:** Good pattern match. Consider the top suggestions carefully.")

	# Symptom pattern analysis
	st.markdown("---")
	st.subheader("Symptom Analysis")
	
	# Analyze symptom patterns
	symptom_analysis = analyze_symptom_patterns(symptoms_text)
	
	col1, col2, col3 = st.columns(3)
	with col1:
		st.metric("Severity Level", symptom_analysis["symptom_details"]["severity"].title())
	with col2:
		st.metric("Onset Pattern", symptom_analysis["symptom_details"]["onset"].title())
	with col3:
		st.metric("Urgency Level", symptom_analysis["urgency_level"].title())
	
	# Show body systems affected
	if symptom_analysis["body_systems_affected"]:
		st.markdown("**Body Systems Affected:**")
		for system in symptom_analysis["body_systems_affected"]:
			st.write(f"- {system.replace('_', ' ').title()}")
	
	# Show pattern matches
	if symptom_analysis["pattern_matches"]:
		st.markdown("**Symptom Patterns Detected:**")
		for pattern in symptom_analysis["pattern_matches"]:
			st.write(f"- {pattern.replace('_', ' ').title()}")

	# Enhanced condition explanations with recommendations
	st.markdown("---")
	st.subheader("Condition Analysis & Recommendations")
	
	for i, pred in enumerate(preds[:3]):  # Show top 3 with explanations
		condition = pred["condition"]
		score = pred["score"]
		severity = pred.get("severity", "routine")
		category = pred.get("category", "general")
		
		# Color code based on severity
		severity_colors = {
			"emergency": "🔴",
			"urgent": "🟠", 
			"routine": "🟢"
		}
		severity_icon = severity_colors.get(severity, "🟢")
		
		with st.expander(f"{severity_icon} {i+1}. {condition.title()} (Score: {score:.3f}) - {severity.title()}", expanded=(i==0)):
			# Get condition-specific information
			explanation = get_condition_explanation(condition, symptoms_text, age, duration_hours)
			st.markdown(explanation)
			
			# Show fine-tuned recommendations if available
			recommendations = get_fine_tuned_recommendations(condition)
			if recommendations:
				st.markdown("**🎯 Specific Recommendations:**")
				
				if recommendations.get("immediate_actions"):
					st.markdown("**Immediate Actions:**")
					for action in recommendations["immediate_actions"]:
						st.write(action)
				
				if recommendations.get("warning_signs"):
					st.markdown("**⚠️ Warning Signs to Watch For:**")
					for sign in recommendations["warning_signs"]:
						st.write(f"- {sign}")
				
				if recommendations.get("prevention"):
					st.markdown("**🛡️ Prevention Tips:**")
					for tip in recommendations["prevention"]:
						st.write(f"- {tip}")
			
			# Show related resources
			condition_key = condition.lower()
			links = resources.get("conditions", {}).get(condition_key, [])
			if links:
				st.markdown("**📚 Learn more:**")
				for link in links:
					st.write(f"- [{link['name']}]({link['url']})")

	# Links for the top suggestion
	top = preds[0]["condition"].lower()
	links = resources.get("conditions", {}).get(top, [])
	if links:
		st.markdown("---")
		st.markdown("**🔗 Quick Resources for Top Suggestion:**")
		for link in links:
			st.write(f"- [{link['name']}]({link['url']})")
	
	return preds

def get_condition_explanation(condition: str, symptoms: str, age: int = None, duration_hours: float = None) -> str:
	"""Generate contextual explanations for conditions."""
	explanations = {
		"heart attack": "A heart attack occurs when blood flow to the heart muscle is blocked, usually by a blood clot. Symptoms often include chest pain, shortness of breath, and sweating. This is a medical emergency requiring immediate attention.",
		"stroke": "A stroke occurs when blood flow to the brain is interrupted, causing brain cells to die. Symptoms may include sudden weakness, confusion, or difficulty speaking. This is a medical emergency requiring immediate attention.",
		"pneumonia": "Pneumonia is an infection that inflames the air sacs in one or both lungs. Symptoms typically include fever, cough, and difficulty breathing. Treatment often involves antibiotics and rest.",
		"asthma": "Asthma is a chronic condition that causes inflammation and narrowing of the airways. Symptoms include wheezing, shortness of breath, and chest tightness. Triggers vary by individual.",
		"migraine": "A migraine is a severe headache that can cause throbbing pain, nausea, and sensitivity to light and sound. It often affects one side of the head and can last for hours or days.",
		"gastroenteritis": "Gastroenteritis is inflammation of the stomach and intestines, often caused by viruses or bacteria. Symptoms include nausea, vomiting, diarrhea, and abdominal pain.",
		"urinary tract infection": "A UTI is an infection in any part of the urinary system. Symptoms include painful urination, frequent urination, and lower abdominal pain. Treatment typically involves antibiotics.",
		"anxiety": "Anxiety is a feeling of worry, nervousness, or unease. It can cause physical symptoms like rapid heartbeat, sweating, and difficulty concentrating. Treatment may include therapy and medication.",
		"depression": "Depression is a mood disorder that causes persistent feelings of sadness and loss of interest. Symptoms can include fatigue, changes in sleep and appetite, and difficulty concentrating.",
		"allergic reaction": "An allergic reaction occurs when the immune system overreacts to a substance. Symptoms can range from mild (rash, itching) to severe (anaphylaxis). Severe reactions require immediate medical attention.",
	}
	
	base_explanation = explanations.get(condition.lower(), f"{condition} is a medical condition that may be related to your symptoms. Please consult with a healthcare provider for proper evaluation and treatment.")
	
	# Add contextual information
	context = []
	if age is not None:
		if age < 18:
			context.append("In children, this condition may present differently and requires special consideration.")
		elif age >= 65:
			context.append("In older adults, this condition may have additional risk factors and complications.")
	
	if duration_hours is not None:
		if duration_hours < 24:
			context.append("The recent onset of symptoms suggests an acute condition that may require prompt evaluation.")
		elif duration_hours > 168:
			context.append("The prolonged duration of symptoms suggests a chronic or persistent condition that should be evaluated.")
	
	if context:
		base_explanation += " " + " ".join(context)
	
	return base_explanation


def render_triage(symptoms_text: str, age: int, duration_hours: float, medical_history: str = "", pain_scale: int = 0, severity: str = "Mild") -> Dict[str, Any]:
	result = compute_triage(symptoms_text, age=age, duration_hours=duration_hours, medical_history=medical_history, pain_scale=pain_scale, severity=severity)
	st.subheader("Triage recommendation")
	st.markdown(f"**Level:** {result.level}")
	if result.reasons:
		st.markdown("**Reasons:**")
		for r in result.reasons:
			st.write(f"- {r}")
	if result.actions:
		st.markdown("**Next steps:**")
		for a in result.actions:
			st.write(f"- {a}")
	return {"level": result.level, "reasons": result.reasons, "actions": result.actions}


def feedback_section(context: Dict[str, Any], predictions: List[Dict[str, Any]] = None) -> None:
	st.markdown("---")
	st.header("Anonymous feedback (optional)")
	
	# Use a separate form for feedback to prevent interference with main form
	with st.form("feedback_form", clear_on_submit=True):
		# Enhanced feedback form
		col1, col2 = st.columns(2)
		with col1:
			useful = st.select_slider("Was this guidance helpful?", options=["No", "Somewhat", "Yes"], value="Somewhat")
		with col2:
			correct_condition = st.selectbox(
				"If you know the correct condition, select it:",
				options=["Unknown"] + [pred["condition"] for pred in (predictions or [])],
				index=0
			)
		
		comments = st.text_area("Any comments to improve this tool? (Do not include personal info)")
		save = st.checkbox("I consent to store this feedback locally (anonymous)")
		
		submit_feedback = st.form_submit_button("Submit feedback", use_container_width=True)
		
		if submit_feedback:
			if not save:
				st.info("Feedback not saved (no consent).")
			else:
				ensure_dirs()
				
				# Record feedback for learning (this handles both file and database storage)
				feedback_system = FeedbackLearningSystem()
				feedback_system.record_feedback(
					symptoms=context.get("symptoms_text", ""),
					predictions=predictions or [],
					correct_condition=correct_condition if correct_condition != "Unknown" else None,
					helpful_score=useful,
					comments=comments.strip()
				)
				
				# Also save to original feedback file for compatibility
				record = {
					"timestamp": datetime.utcnow().isoformat() + "Z",
					"helpful": useful,
					"comments": comments.strip(),
					"context": context,
				}
				with open(FEEDBACK_PATH, "a", encoding="utf-8") as f:
					f.write(json.dumps(record, ensure_ascii=False) + "\n")
				
				st.success("Thanks! Your feedback was saved and will help improve predictions.")


def _inject_css() -> None:
	st.markdown(
		"""
		<style>
			/***** Layout and typography tweaks *****/
			.main > div {
				padding-top: 0.5rem;
			}
			.block-container {
				padding-top: 1.2rem;
				padding-bottom: 2rem;
			}
			h1, h2, h3 { letter-spacing: 0.2px; }
			/***** Buttons *****/
			.stButton > button {
				border-radius: 8px;
				padding: 0.6rem 1rem;
				border: 1px solid rgba(49,51,63,0.2);
			}
			/***** Info/warning cards *****/
			.stAlert { border-radius: 8px; }
			/***** Tabs *****/
			.stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
		</style>
		""",
		unsafe_allow_html=True,
	)


def render_signin_page() -> None:
	"""Render the dedicated sign-in page."""
	st.set_page_config(page_title="CarePilot - Sign In", page_icon="🩺", layout="centered")
	_inject_css()
	
	# Check if Supabase is configured
	sb_client = get_supabase_client()
	
	# Center the content
	col1, col2, col3 = st.columns([1, 2, 1])
	with col2:
		st.markdown("<br>", unsafe_allow_html=True)
		st.markdown("""
		<div style="text-align: center;">
			<h1>🩺 CarePilot</h1>
			<h3>Quick Medical Triage Guidance</h3>
			<p style="color: #666;">Please sign in to access the application</p>
		</div>
		""", unsafe_allow_html=True)
		
		st.markdown("---")
		
		# Show different content based on Supabase configuration
		if sb_client is None:
			# Supabase not configured - show demo mode
			st.info("🔧 **Demo Mode**: Authentication is not configured. Click below to continue without authentication.")
			st.markdown("""
			<div style="text-align: center; padding: 20px;">
				<p>This is a demonstration version of CarePilot.</p>
				<p>To enable full authentication, configure Supabase environment variables.</p>
			</div>
			""", unsafe_allow_html=True)
			
			if st.button("Continue to Demo", use_container_width=True, type="primary"):
				st.session_state.user = {"id": "demo_user", "email": "demo@example.com", "name": "Demo User"}
				st.rerun()
		else:
			# Supabase configured - show normal auth form
			with st.container():
				mode = st.radio("Choose an option:", options=["Sign in", "Sign up"], index=0, horizontal=True)
				
				with st.form("auth_form"):
					email = st.text_input("Email", placeholder="Enter your email address")
					password = st.text_input("Password", type="password", placeholder="Enter your password")
					
					# Add name field for sign up
					if mode == "Sign up":
						name = st.text_input("Full Name", placeholder="Enter your full name")
					
					if mode == "Sign in":
						submit_button = st.form_submit_button("Sign In", use_container_width=True, type="primary")
						if submit_button:
							if not email.strip() or not password.strip():
								st.error("Please enter both email and password.")
							else:
								with st.spinner("Signing in..."):
									res = sign_in_with_email(email.strip(), password)
									if res.get("error"):
										st.error(f"Sign in failed: {res['error']}")
									else:
										# Check if email confirmation should be bypassed
										bypass_email_confirmation = os.getenv("BYPASS_EMAIL_CONFIRMATION", "true").lower() == "true"
										
										if bypass_email_confirmation or is_email_confirmed():
											st.session_state.user = get_current_user()
											st.success("Successfully signed in!")
											st.rerun()
										else:
											st.warning("⚠️ **Email not confirmed!** Please check your email and click the confirmation link before signing in.")
											st.info("💡 **Demo Mode**: Email confirmation is bypassed. You should be able to sign in now.")
					else:
						submit_button = st.form_submit_button("Create Account", use_container_width=True, type="primary")
						if submit_button:
							if not email.strip() or not password.strip():
								st.error("Please enter both email and password.")
							elif mode == "Sign up" and not name.strip():
								st.error("Please enter your full name.")
							elif len(password) < 6:
								st.error("Password must be at least 6 characters long.")
							else:
								with st.spinner("Creating account..."):
									res = sign_up_with_email(email.strip(), password, name.strip() if mode == "Sign up" else None)
									if res.get("error"):
										st.error(f"Account creation failed: {res['error']}")
									else:
										st.success("✅ Account created successfully!")
										st.info("🎉 **You can now sign in immediately!** (Email confirmation bypassed for demo)")
										st.markdown("""
										**Next steps:**
										1. Switch to "Sign in" tab above
										2. Use your email and password to sign in
										3. Start using the app!
										""")
		
	st.markdown("---")
	
	# Safety notice
	st.markdown("""
	<div style="text-align: center; color: #666; font-size: 0.9em;">
		<p><strong>Educational only:</strong> This app does not provide medical diagnoses or treatment.</p>
		<p>In an emergency, call your local emergency number.</p>
	</div>
	""", unsafe_allow_html=True)


def render_main_app() -> None:
	"""Render the main application after authentication."""
	st.set_page_config(page_title=APP_TITLE, page_icon="🩺", layout="wide")
	_inject_css()

	# Top header with title and profile button
	col1, col2 = st.columns([3, 1])
	with col1:
		st.title("CarePilot")
		st.caption("Quick, educational triage guidance")
	
	with col2:
		# Profile button aligned to the right with custom styling
		if st.session_state.user:
			user_email = st.session_state.user.get('email', 'user')
			# Add custom CSS for circular profile button
			st.markdown("""
			<style>
			.profile-button {
				position: relative;
				top: 20px;
				display: flex;
				justify-content: flex-end;
			}
			.profile-button .stPopover > div {
				border-radius: 50% !important;
				width: 60px !important;
				height: 60px !important;
				min-width: 60px !important;
				min-height: 60px !important;
				display: flex !important;
				align-items: center !important;
				justify-content: center !important;
				background-color: #f0f2f6 !important;
				border: 3px solid #1f77b4 !important;
				box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
				transition: all 0.3s ease !important;
				font-size: 24px !important;
				cursor: pointer !important;
				padding: 0 !important;
				margin: 0 !important;
			}
			.profile-button .stPopover > div:hover {
				background-color: #1f77b4 !important;
				color: white !important;
				transform: scale(1.1) !important;
				box-shadow: 0 6px 12px rgba(0,0,0,0.25) !important;
			}
			</style>
			""", unsafe_allow_html=True)
			
			with st.container():
				st.markdown('<div class="profile-button">', unsafe_allow_html=True)
				with st.popover("👤", use_container_width=True):
					st.write(f"**Email:** {user_email}")
					st.write(f"**Name:** {st.session_state.user.get('name', 'User')}")
					st.markdown("---")
					if st.button("Sign out", use_container_width=True):
						err = sign_out()
						if err:
							st.error(f"Sign out failed: {err}")
						else:
							# Clear all session state related to user
							st.session_state.user = None
							# Clear any cached data
							if "user_data" in st.session_state:
								del st.session_state.user_data
							st.success("Successfully signed out!")
							st.rerun()
				st.markdown('</div>', unsafe_allow_html=True)
	
	# Welcome note below title
	if st.session_state.user:
		user_name = st.session_state.user.get('name', 'User')
		st.success(f"👋 Welcome, {user_name}!")

	# Safety notice
	st.markdown("---")
	disclaimer()

	# Main application content
	st.markdown("### Tell us about your symptoms")
	with st.form("survey_form", clear_on_submit=False):
		col1, col2 = st.columns(2)
		with col1:
			age = st.number_input("Age (years)", min_value=0, max_value=120, value=30, step=1)
		with col2:
			# Duration input with unit selection
			duration_col1, duration_col2 = st.columns([2, 1])
			with duration_col1:
				duration_value = st.number_input("How long have symptoms lasted?", min_value=0.0, value=12.0, step=1.0)
			with duration_col2:
				duration_unit = st.selectbox("Unit", options=["hours", "days"], index=0)
			
			# Convert to hours for internal processing
			if duration_unit == "days":
				duration_hours = duration_value * 24
			else:
				duration_hours = duration_value
		symptoms_text = st.text_area(
			"Describe your symptoms",
			placeholder="e.g., Sudden chest tightness, shortness of breath, sweating",
			height=120,
		)
		additional = st.text_input("Optional: key medical history or medications")
		
		# Pain and severity assessment
		st.markdown("**Pain and Severity Assessment**")
		col3, col4 = st.columns(2)
		with col3:
			pain_scale = st.slider("Pain level (0-10)", min_value=0, max_value=10, value=0, 
								 help="0 = No pain, 10 = Worst pain imaginable")
		with col4:
			severity = st.select_slider("Overall symptom severity", 
									 options=["Mild", "Moderate", "Severe"], 
									 value="Mild")
		
		consent = st.checkbox("I understand this is not a diagnosis and agree to proceed.", value=False)
		submitted = st.form_submit_button("Analyze symptoms", use_container_width=True)

	if submitted:
		if not consent:
			st.warning("Please check the consent box to proceed.")
			st.stop()
		
		resources = load_resources()
		col_a, col_b = st.columns([2, 1])
		with col_a:
			tab_overview, tab_conditions, tab_triage, tab_resources, tab_feedback = st.tabs([
				"Overview",
				"Conditions",
				"Triage",
				"Resources",
				"Feedback",
			])

			with tab_overview:
				st.subheader("Summary")
				# Display duration with the original unit
				if duration_unit == "days":
					duration_display = f"{float(duration_value)} days"
				else:
					duration_display = f"{float(duration_value)} hours"
				st.write(f"Age: {int(age)}  |  Duration: {duration_display}")
				st.write(f"Symptoms: {symptoms_text}")
				if additional:
					st.caption(f"History/meds: {additional}")
				
				# Display pain and severity information
				st.markdown("**Pain & Severity Assessment:**")
				st.write(f"Pain Level: {pain_scale}/10")
				st.write(f"Symptom Severity: {severity}")
				
				# Pain scale interpretation
				if pain_scale >= 8:
					st.warning("⚠️ High pain level - consider seeking immediate medical attention")
				elif pain_scale >= 5:
					st.info("🔶 Moderate pain level - monitor closely")
				elif pain_scale > 0:
					st.success("✅ Low pain level - continue monitoring")

			with tab_conditions:
				preds = render_suggestions(symptoms_text, resources, age=int(age), duration_hours=float(duration_hours), medical_history=additional)

			with tab_triage:
				triage = render_triage(symptoms_text, int(age), float(duration_hours), additional, pain_scale, severity)

			with tab_resources:
				st.subheader("General resources")
				for link in resources.get("general", []):
					st.write(f"- [{link['name']}]({link['url']})")

			with tab_feedback:
				context = {
					"age": int(age),
					"duration_hours": float(duration_hours),
					"symptoms_text": symptoms_text,
				}
				feedback_section(context, preds)

		# Persist submission to Supabase if available
		if st.session_state.user:
			row = {
				"user_id": st.session_state.user.get("id"),
				"age": int(age),
				"duration_hours": float(duration_hours),
				"symptoms_text": symptoms_text,
				"medical_history": additional,
				"pain_scale": int(pain_scale),
				"severity": str(severity),
				"created_at": datetime.utcnow().isoformat() + "Z",
			}
			res = insert_row("surveys", row)
			if res.get("error"):
				st.error(f"Could not save survey to database: {res['error']}")
			else:
				st.success("Survey saved to database successfully!")

		with col_b:
			st.markdown("### Tips")
			st.info("Include onset, severity, triggers, and associated symptoms for better suggestions.")

	else:
		st.info("Fill in the form and press Analyze to see guidance.")


def main() -> None:
	# Determine if Supabase is configured
	sb_client = get_supabase_client()
	# Enable auth if Supabase is configured OR if explicitly requested via env var
	# Default to showing auth page unless explicitly disabled
	use_auth = sb_client is not None or os.getenv("ENABLE_AUTH", "true").lower() == "true"
	
	# Set BYPASS_EMAIL_CONFIRMATION=false to enable email confirmation
	os.environ["BYPASS_EMAIL_CONFIRMATION"] = os.getenv("BYPASS_EMAIL_CONFIRMATION", "true")
	
	# Initialize user session state
	if "user" not in st.session_state:
		# Only try to get current user if we're using auth and don't have a user yet
		if use_auth:
			try:
				current_user = get_current_user()
				st.session_state.user = current_user
			except Exception as e:
				print(f"Error getting current user: {e}")
				st.session_state.user = None
		else:
			st.session_state.user = None
	
	# Check if user session is still valid (only if using auth)
	if use_auth and st.session_state.user:
		try:
			# First check if user is still authenticated (lightweight check)
			if not is_user_authenticated():
				# Try to refresh the session before giving up
				if refresh_session_if_needed():
					# Session was refreshed, continue with normal flow
					pass
				else:
					# Session expired or invalid, clear user state
					st.session_state.user = None
			
			# If we still have a user, verify and update user data
			if st.session_state.user:
				verified_user = get_current_user()
				if verified_user:
					# Update session state with fresh user data
					st.session_state.user = verified_user
				else:
					# Something went wrong, clear user state
					st.session_state.user = None
		except Exception as e:
			print(f"Error verifying user session: {e}")
			# If there's an error verifying, keep the current session state
			# This prevents unnecessary logouts due to temporary network issues
			pass
	
	# If authentication is required but user is not signed in, show sign-in page
	if use_auth and not st.session_state.user:
		render_signin_page()
		return
	
	# If authentication is not required or user is signed in, show main app
	render_main_app()


if __name__ == "__main__":
	main()
