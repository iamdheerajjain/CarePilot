import os
from datetime import datetime
from typing import Any, Dict, Optional

_client = None


def _load_env() -> None:
	# Lazy env load for environments using .env
	try:
		from dotenv import load_dotenv  # type: ignore
		import warnings
		# Suppress dotenv parsing warnings
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			try:
				load_dotenv(override=False)
			except (UnicodeDecodeError, Exception):
				# Handle corrupted .env files gracefully
				pass
	except Exception:
		return


def get_supabase_client():
	"""Return a cached Supabase client or None if not configured."""
	global _client
	if _client is not None:
		return _client

	_load_env()
	url = os.getenv("SUPABASE_URL", "").strip()
	key = os.getenv("SUPABASE_ANON_KEY", "").strip()
	if not url or not key:
		return None

	try:
		from supabase import create_client  # type: ignore
	except Exception:
		return None

	_client = create_client(url, key)
	return _client


def sign_in_with_email(email: str, password: str) -> Dict[str, Any]:
	client = get_supabase_client()
	if client is None:
		return {"error": "Supabase not configured"}
	try:
		res = client.auth.sign_in_with_password({"email": email, "password": password})
		
		# Update last login timestamp
		if res and hasattr(res, 'user') and res.user:
			user_id = getattr(res.user, 'id', None)
			if user_id:
				update_result = update_user_last_login(user_id)
				if update_result.get("error"):
					print(f"Warning: Could not update last login: {update_result['error']}")
				else:
					print(f"Last login updated for: {email}")
		
		return {"data": res, "error": None}
	except Exception as e:
		return {"error": str(e)}


def sign_up_with_email(email: str, password: str, name: str = None) -> Dict[str, Any]:
	client = get_supabase_client()
	if client is None:
		return {"error": "Supabase not configured"}
	try:
		# Add redirect URL for email confirmation
		# This should match your app's URL or a confirmation page
		redirect_url = os.getenv("SITE_URL", "http://localhost:8501")
		
		# For deployed apps, try to detect the current URL
		if not redirect_url or "localhost" in redirect_url:
			# Try to get the current URL from Streamlit
			try:
				import streamlit as st
				if hasattr(st, 'get_option') and st.get_option('server.baseUrlPath'):
					base_url = st.get_option('server.baseUrlPath')
					if base_url and not base_url.startswith('http'):
						redirect_url = f"https://{base_url}"
			except:
				pass
		
		# Prepare user metadata with name if provided
		user_metadata = {}
		if name:
			user_metadata["full_name"] = name
			user_metadata["display_name"] = name
		
		# Add additional profile information
		user_metadata["signup_source"] = "carepilot_app"
		user_metadata["signup_timestamp"] = datetime.utcnow().isoformat() + "Z"
		
		res = client.auth.sign_up({
			"email": email, 
			"password": password,
			"options": {
				"email_redirect_to": f"{redirect_url}/",
				"data": user_metadata
			}
		})
		
		# Log successful registration for debugging
		if res and hasattr(res, 'user') and res.user:
			print(f"User registered successfully: {email}")
			
			# Create user profile in users table
			user_id = getattr(res.user, 'id', None)
			if user_id:
				profile_result = create_user_profile(user_id, email, name, "carepilot_app")
				if profile_result.get("error"):
					print(f"Warning: Could not create user profile: {profile_result['error']}")
				else:
					print(f"User profile created successfully for: {email}")
		
		return {"data": res, "error": None}
	except Exception as e:
		print(f"Registration error: {e}")
		return {"error": str(e)}


def sign_out() -> Optional[str]:
	client = get_supabase_client()
	if client is None:
		return None
	try:
		client.auth.sign_out()
		return None
	except Exception as e:
		return str(e)


def get_current_user() -> Optional[Dict[str, Any]]:
	client = get_supabase_client()
	if client is None:
		return None
	try:
		# Get the current session first
		session = client.auth.get_session()
		if not session or not hasattr(session, 'user') or not session.user:
			return None
			
		user = session.user
		
		# Normalize to a plain dict with typical fields
		user_metadata = getattr(user, "user_metadata", {}) or {}
		if isinstance(user, dict):
			user_metadata = user.get("user_metadata", {})
		
		# Extract user ID
		user_id = getattr(user, "id", None)
		if not user_id and isinstance(user, dict):
			user_id = user.get("id")
		
		# Extract email
		email = getattr(user, "email", None)
		if not email and isinstance(user, dict):
			email = user.get("email")
		
		# Extract name with fallbacks
		name = user_metadata.get("full_name") or user_metadata.get("display_name") or "User"
		
		return {
			"id": user_id,
			"email": email,
			"email_confirmed_at": getattr(user, "email_confirmed_at", None),
			"created_at": getattr(user, "created_at", None),
			"name": name,
			"signup_source": user_metadata.get("signup_source", "unknown"),
			"signup_timestamp": user_metadata.get("signup_timestamp"),
			"metadata": user_metadata,  # Include full metadata for debugging
		}
	except Exception as e:
		print(f"Error getting current user: {e}")
		return None


def is_email_confirmed() -> bool:
	"""Check if the current user's email is confirmed."""
	user = get_current_user()
	if not user:
		return False
	return user.get("email_confirmed_at") is not None


def is_user_authenticated() -> bool:
	"""Check if user is currently authenticated without making API calls."""
	client = get_supabase_client()
	if client is None:
		return False
	try:
		# Check if we have a valid session without making a full API call
		session = client.auth.get_session()
		return session is not None and hasattr(session, 'user') and session.user is not None
	except Exception:
		return False


def refresh_session_if_needed() -> bool:
	"""Refresh the session if it's close to expiring. Returns True if session is valid."""
	client = get_supabase_client()
	if client is None:
		return False
	try:
		# Try to refresh the session
		client.auth.refresh_session()
		return True
	except Exception as e:
		print(f"Session refresh failed: {e}")
		return False


def create_user_profile(user_id: str, email: str, full_name: str = None, signup_source: str = "carepilot_app") -> Dict[str, Any]:
	"""Create a user profile in the users table."""
	client = get_supabase_client()
	if client is None:
		return {"error": "Supabase not configured"}
	
	try:
		user_data = {
			"id": user_id,
			"email": email,
			"full_name": full_name,
			"display_name": full_name,
			"signup_source": signup_source,
			"signup_timestamp": datetime.utcnow().isoformat() + "Z",
			"is_active": True
		}
		
		print(f"Creating user profile: {user_data}")  # Debug output
		res = client.table("users").insert(user_data).execute()
		print(f"User profile created: {res}")  # Debug output
		return {"data": getattr(res, "data", None), "error": None}
	except Exception as e:
		print(f"User profile creation error: {e}")  # Debug output
		return {"error": str(e)}


def update_user_last_login(user_id: str) -> Dict[str, Any]:
	"""Update user's last login timestamp."""
	client = get_supabase_client()
	if client is None:
		return {"error": "Supabase not configured"}
	
	try:
		update_data = {
			"last_login": datetime.utcnow().isoformat() + "Z",
			"updated_at": datetime.utcnow().isoformat() + "Z"
		}
		
		res = client.table("users").update(update_data).eq("id", user_id).execute()
		return {"data": getattr(res, "data", None), "error": None}
	except Exception as e:
		print(f"Last login update error: {e}")
		return {"error": str(e)}


def insert_row(table: str, row: Dict[str, Any]) -> Dict[str, Any]:
	client = get_supabase_client()
	if client is None:
		return {"error": "Supabase not configured"}
	try:
		print(f"Inserting into {table}: {row}")  # Debug output
		res = client.table(table).insert(row).execute()
		print(f"Insert result: {res}")  # Debug output
		return {"data": getattr(res, "data", None), "error": None}
	except Exception as e:
		print(f"Insert error: {e}")  # Debug output
		return {"error": str(e)}


