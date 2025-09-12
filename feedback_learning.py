import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter

try:
	from supabase_client import get_supabase_client, get_current_user, insert_row
except ImportError:
	get_supabase_client = None
	get_current_user = None
	insert_row = None


class FeedbackLearningSystem:
	"""A system to learn from user feedback and improve predictions over time."""
	
	def __init__(self, feedback_file: str = "storage/feedback.jsonl"):
		self.feedback_file = feedback_file
		self.ensure_storage_dir()
		self.pattern_weights = self._load_pattern_weights()
		self.condition_corrections = self._load_condition_corrections()
	
	def ensure_storage_dir(self):
		"""Ensure the storage directory exists."""
		os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
	
	def _load_pattern_weights(self) -> Dict[str, float]:
		"""Load pattern weights from stored feedback."""
		weights_file = "storage/pattern_weights.json"
		try:
			with open(weights_file, 'r') as f:
				return json.load(f)
		except FileNotFoundError:
			return defaultdict(float)
	
	def _load_condition_corrections(self) -> Dict[str, Dict[str, float]]:
		"""Load condition correction factors from feedback."""
		corrections_file = "storage/condition_corrections.json"
		try:
			with open(corrections_file, 'r') as f:
				return json.load(f)
		except FileNotFoundError:
			return defaultdict(lambda: defaultdict(float))
	
	def _save_pattern_weights(self):
		"""Save pattern weights to file."""
		weights_file = "storage/pattern_weights.json"
		with open(weights_file, 'w') as f:
			json.dump(dict(self.pattern_weights), f)
	
	def _save_condition_corrections(self):
		"""Save condition corrections to file."""
		corrections_file = "storage/condition_corrections.json"
		with open(corrections_file, 'w') as f:
			json.dump(dict(self.condition_corrections), f)
	
	def record_feedback(self, symptoms: str, predictions: List[Dict[str, float]], 
					   correct_condition: Optional[str] = None, 
					   helpful_score: str = "Somewhat",
					   comments: str = ""):
		"""Record user feedback for learning."""
		feedback_record = {
			"timestamp": datetime.utcnow().isoformat() + "Z",
			"symptoms": symptoms,
			"predictions": predictions,
			"correct_condition": correct_condition,
			"helpful_score": helpful_score,
			"comments": comments
		}
		
		# Save to feedback file
		with open(self.feedback_file, 'a', encoding='utf-8') as f:
			f.write(json.dumps(feedback_record, ensure_ascii=False) + "\n")
		
		# Save to Supabase if configured
		if get_supabase_client and insert_row:
			try:
				user = get_current_user()
				user_id = user.get("id") if user else None
				
				# Create feedback record for database
				supabase_record = {
					"symptoms": symptoms,
					"predictions": predictions,
					"correct_condition": correct_condition,
					"helpful_score": helpful_score,
					"comments": comments,
					"created_at": feedback_record["timestamp"]
				}
				
				# Add user_id if available, otherwise use a default for anonymous feedback
				if user_id:
					supabase_record["user_id"] = user_id
					print(f"Attempting to save authenticated feedback to database: {supabase_record}")
				else:
					# For anonymous feedback, we'll use a special user_id or handle it differently
					supabase_record["user_id"] = None  # Allow NULL user_id for anonymous feedback
					print(f"Attempting to save anonymous feedback to database: {supabase_record}")
				
				res = insert_row("feedback", supabase_record)
				if res.get("error"):
					print(f"Feedback save error: {res['error']}")  # Debug output
					# Try alternative approach - save without user_id
					if "user_id" in str(res.get("error", "")):
						print("Retrying without user_id...")
						supabase_record.pop("user_id", None)
						res = insert_row("feedback", supabase_record)
						if res.get("error"):
							print(f"Retry also failed: {res['error']}")
						else:
							print(f"Feedback saved successfully (anonymous): {res.get('data')}")
					else:
						print(f"Database error: {res['error']}")
				else:
					print(f"Feedback saved successfully to database: {res.get('data')}")
			except Exception as e:
				print(f"Error saving feedback to database: {e}")
				# Try to save without user_id as fallback
				try:
					fallback_record = {
						"symptoms": symptoms,
						"predictions": predictions,
						"correct_condition": correct_condition,
						"helpful_score": helpful_score,
						"comments": comments,
						"created_at": feedback_record["timestamp"]
					}
					print("Attempting fallback save without user_id...")
					res = insert_row("feedback", fallback_record)
					if res.get("error"):
						print(f"Fallback save also failed: {res['error']}")
					else:
						print(f"Fallback save successful: {res.get('data')}")
				except Exception as fallback_error:
					print(f"Fallback save error: {fallback_error}")
		
		# Update learning models
		self._update_pattern_weights(symptoms, predictions, correct_condition, helpful_score)
		self._update_condition_corrections(symptoms, predictions, correct_condition, helpful_score)
	
	def _update_pattern_weights(self, symptoms: str, predictions: List[Dict[str, float]], 
							   correct_condition: Optional[str], helpful_score: str):
		"""Update pattern weights based on feedback."""
		symptoms_lower = symptoms.lower()
		
		# Extract symptom patterns
		patterns = self._extract_symptom_patterns(symptoms_lower)
		
		# Determine if predictions were helpful
		helpful_multiplier = self._get_helpful_multiplier(helpful_score)
		
		for pattern in patterns:
			if correct_condition:
				# If we know the correct condition, boost patterns that led to correct predictions
				top_prediction = predictions[0]["condition"] if predictions else None
				if top_prediction == correct_condition:
					self.pattern_weights[pattern] += 0.1 * helpful_multiplier
				else:
					self.pattern_weights[pattern] -= 0.05 * helpful_multiplier
			else:
				# General helpfulness feedback
				self.pattern_weights[pattern] += 0.02 * helpful_multiplier
		
		self._save_pattern_weights()
	
	def _update_condition_corrections(self, symptoms: str, predictions: List[Dict[str, float]], 
									correct_condition: Optional[str], helpful_score: str):
		"""Update condition-specific correction factors."""
		symptoms_lower = symptoms.lower()
		helpful_multiplier = self._get_helpful_multiplier(helpful_score)
		
		if correct_condition:
			# Boost the correct condition for similar symptom patterns
			for pred in predictions:
				condition = pred["condition"]
				if condition == correct_condition:
					self.condition_corrections[symptoms_lower][condition] += 0.2 * helpful_multiplier
				else:
					self.condition_corrections[symptoms_lower][condition] -= 0.1 * helpful_multiplier
		
		self._save_condition_corrections()
	
	def _extract_symptom_patterns(self, symptoms: str) -> List[str]:
		"""Extract key symptom patterns from text with enhanced medical terminology."""
		patterns = []
		
		# Enhanced symptom keywords with medical terminology
		symptom_keywords = [
			# Pain and discomfort
			"pain", "ache", "hurt", "sore", "tender", "throbbing", "burning", "stabbing", "cramping",
			# Fever and temperature
			"fever", "temperature", "hot", "cold", "chills", "sweating", "rigors", "hyperthermia", "hypothermia",
			# Gastrointestinal
			"nausea", "vomit", "sick", "queasy", "emesis", "regurgitation", "retching",
			"diarrhea", "loose", "watery", "constipation", "bowel", "stool",
			# Neurological
			"headache", "migraine", "throbbing", "cephalgia", "cranial pain",
			"confusion", "memory", "forget", "disorientation", "cognitive", "mental fog",
			"seizure", "convulsion", "shaking", "epileptic", "tonic-clonic",
			"weakness", "fatigue", "tired", "exhausted", "lethargy", "malaise",
			"numbness", "tingling", "paresthesia", "loss of sensation",
			# Cardiovascular
			"chest", "heart", "breathing", "breath", "dyspnea", "shortness", "palpitations", "arrhythmia",
			# Respiratory
			"cough", "coughing", "phlegm", "sputum", "wheezing", "stridor", "barking",
			# Dermatological
			"rash", "itch", "red", "swollen", "inflammation", "lesion", "blister", "hives",
			# Musculoskeletal
			"joint", "muscle", "bone", "stiffness", "swelling", "tenderness", "spasm",
			# Genitourinary
			"urination", "urinary", "bladder", "kidney", "pelvic", "genital",
			# Mental health
			"anxiety", "panic", "depression", "sad", "hopeless", "mood", "emotional",
			# Emergency symptoms
			"bleeding", "blood", "hemorrhage", "unconscious", "faint", "collapse", "emergency"
		]
		
		for keyword in symptom_keywords:
			if keyword in symptoms:
				patterns.append(keyword)
		
		# Enhanced body parts with medical terminology
		body_parts = [
			"head", "neck", "chest", "back", "stomach", "abdomen", "pelvis",
			"arm", "leg", "hand", "foot", "knee", "elbow", "shoulder", "hip",
			"throat", "ear", "eye", "nose", "mouth", "tongue", "lips",
			"heart", "lung", "liver", "kidney", "bladder", "brain", "spine"
		]
		
		for part in body_parts:
			if part in symptoms:
				patterns.append(f"body_{part}")
		
		# Temporal patterns
		temporal_patterns = [
			"sudden", "acute", "chronic", "persistent", "ongoing", "recurring",
			"intermittent", "episodic", "gradual", "rapid", "slow", "immediate"
		]
		
		for pattern in temporal_patterns:
			if pattern in symptoms:
				patterns.append(f"temporal_{pattern}")
		
		# Severity patterns
		severity_patterns = [
			"severe", "mild", "moderate", "intense", "unbearable", "excruciating",
			"worst", "terrible", "awful", "horrible", "extreme", "minimal"
		]
		
		for pattern in severity_patterns:
			if pattern in symptoms:
				patterns.append(f"severity_{pattern}")
		
		# Symptom combinations
		if "chest" in symptoms and "pain" in symptoms:
			patterns.append("chest_pain_combo")
		if "shortness" in symptoms and "breath" in symptoms:
			patterns.append("shortness_breath_combo")
		if "nausea" in symptoms and "vomiting" in symptoms:
			patterns.append("nausea_vomiting_combo")
		if "fever" in symptoms and "cough" in symptoms:
			patterns.append("fever_cough_combo")
		if "headache" in symptoms and "nausea" in symptoms:
			patterns.append("headache_nausea_combo")
		
		return patterns
	
	def _get_helpful_multiplier(self, helpful_score: str) -> float:
		"""Convert helpfulness score to multiplier."""
		multipliers = {
			"No": -0.5,
			"Somewhat": 0.1,
			"Yes": 0.5
		}
		return multipliers.get(helpful_score, 0.1)
	
	def get_pattern_weight(self, pattern: str) -> float:
		"""Get weight for a specific pattern."""
		return self.pattern_weights.get(pattern, 0.0)
	
	def get_condition_correction(self, symptoms: str, condition: str) -> float:
		"""Get correction factor for a condition given symptoms."""
		symptoms_lower = symptoms.lower()
		return self.condition_corrections.get(symptoms_lower, {}).get(condition, 0.0)
	
	def apply_learning_adjustments(self, symptoms: str, predictions: List[Dict[str, float]]) -> List[Dict[str, float]]:
		"""Apply enhanced learning adjustments to predictions."""
		adjusted_predictions = []
		symptoms_lower = symptoms.lower()
		
		for pred in predictions:
			condition = pred["condition"]
			base_score = pred["score"]
			
			# Apply pattern-based adjustments with enhanced weighting
			pattern_adjustment = 0.0
			patterns = self._extract_symptom_patterns(symptoms_lower)
			for pattern in patterns:
				weight = self.get_pattern_weight(pattern)
				# Enhanced weighting based on pattern type
				if pattern.startswith("severity_"):
					pattern_adjustment += weight * 0.15  # Severity patterns are important
				elif pattern.startswith("temporal_"):
					pattern_adjustment += weight * 0.12  # Temporal patterns are important
				elif pattern.endswith("_combo"):
					pattern_adjustment += weight * 0.2  # Symptom combinations are very important
				else:
					pattern_adjustment += weight * 0.1
			
			# Apply condition-specific corrections
			condition_adjustment = self.get_condition_correction(symptoms_lower, condition)
			
			# Apply similarity-based adjustments
			similarity_adjustment = self._get_similarity_adjustment(symptoms_lower, condition)
			
			# Apply confidence-based adjustments
			confidence_adjustment = self._get_confidence_adjustment(symptoms_lower, condition)
			
			# Combine all adjustments
			total_adjustment = pattern_adjustment + condition_adjustment + similarity_adjustment + confidence_adjustment
			adjusted_score = max(0.0, min(1.0, base_score + total_adjustment))
			
			adjusted_predictions.append({
				"condition": condition,
				"score": adjusted_score
			})
		
		# Sort by adjusted scores
		adjusted_predictions.sort(key=lambda x: x["score"], reverse=True)
		return adjusted_predictions
	
	def _get_similarity_adjustment(self, symptoms: str, condition: str) -> float:
		"""Get adjustment based on similarity to previous successful cases."""
		# This would ideally use more sophisticated similarity matching
		# For now, we'll use a simple keyword-based approach
		similarity_score = 0.0
		
		# Check for similar symptom patterns in successful cases
		# This is a simplified version - in practice, you'd want more sophisticated matching
		if condition in self.condition_corrections:
			for symptom_pattern, corrections in self.condition_corrections.items():
				if condition in corrections and corrections[condition] > 0.1:
					# Simple similarity check
					common_words = set(symptoms.split()) & set(symptom_pattern.split())
					if len(common_words) > 0:
						similarity_score += 0.05 * len(common_words)
		
		return min(0.2, similarity_score)  # Cap the adjustment
	
	def _get_confidence_adjustment(self, symptoms: str, condition: str) -> float:
		"""Get adjustment based on confidence in the prediction."""
		confidence_score = 0.0
		
		# Higher confidence for conditions with strong pattern matches
		patterns = self._extract_symptom_patterns(symptoms)
		strong_patterns = [p for p in patterns if self.get_pattern_weight(p) > 0.2]
		
		if len(strong_patterns) > 0:
			confidence_score += 0.1 * len(strong_patterns)
		
		# Higher confidence for emergency conditions with emergency keywords
		emergency_conditions = ["heart attack", "stroke", "anaphylaxis", "septic shock"]
		emergency_keywords = ["severe", "intense", "unbearable", "emergency", "urgent"]
		
		if condition in emergency_conditions and any(keyword in symptoms for keyword in emergency_keywords):
			confidence_score += 0.15
		
		return min(0.2, confidence_score)  # Cap the adjustment
	
