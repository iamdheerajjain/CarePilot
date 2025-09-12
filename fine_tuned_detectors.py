from typing import List, Dict, Optional, Tuple
import threading
import os
import re
from datetime import datetime

try:
	from transformers import pipeline
except Exception:  # pragma: no cover
	pipeline = None  # type: ignore

_classifier_lock = threading.Lock()
_classifier = None

# Comprehensive keyword-to-condition mapping for simple inputs
SIMPLE_KEYWORD_MAPPINGS = {
	# Single symptom keywords with high accuracy mappings
	"headache": [
		("migraine", 0.85),
		("tension headache", 0.80),
		("cluster headache", 0.60),
		("sinus headache", 0.50)
	],
	"fever": [
		("influenza", 0.80),
		("pneumonia", 0.75),
		("covid-19", 0.70),
		("respiratory infection", 0.65),
		("viral infection", 0.60)
	],
	"cough": [
		("bronchitis", 0.80),
		("respiratory infection", 0.75),
		("pneumonia", 0.70),
		("asthma", 0.60),
		("covid-19", 0.65)
	],
	"chest pain": [
		("heart attack", 0.90),
		("angina", 0.80),
		("heart failure", 0.70),
		("pericarditis", 0.60),
		("muscle strain", 0.50)
	],
	"nausea": [
		("gastroenteritis", 0.80),
		("migraine", 0.70),
		("food poisoning", 0.75),
		("pregnancy", 0.60),
		("motion sickness", 0.55)
	],
	"vomiting": [
		("gastroenteritis", 0.85),
		("food poisoning", 0.80),
		("migraine", 0.70),
		("pregnancy", 0.65),
		("appendicitis", 0.60)
	],
	"diarrhea": [
		("gastroenteritis", 0.85),
		("food poisoning", 0.80),
		("irritable bowel syndrome", 0.60),
		("viral infection", 0.70),
		("bacterial infection", 0.65)
	],
	"tired": [
		("fatigue", 0.90),
		("anemia", 0.70),
		("depression", 0.65),
		("thyroid disorder", 0.60),
		("sleep disorder", 0.55)
	],
	"fatigue": [
		("chronic fatigue syndrome", 0.80),
		("anemia", 0.75),
		("depression", 0.70),
		("thyroid disorder", 0.65),
		("fibromyalgia", 0.60)
	],
	"dizzy": [
		("vertigo", 0.85),
		("low blood pressure", 0.70),
		("inner ear disorder", 0.65),
		("dehydration", 0.60),
		("anxiety", 0.55)
	],
	"dizziness": [
		("vertigo", 0.90),
		("low blood pressure", 0.75),
		("inner ear disorder", 0.70),
		("dehydration", 0.65),
		("anxiety", 0.60)
	],
	"sore throat": [
		("pharyngitis", 0.85),
		("strep throat", 0.80),
		("tonsillitis", 0.75),
		("viral infection", 0.70),
		("allergic reaction", 0.50)
	],
	"back pain": [
		("muscle strain", 0.80),
		("herniated disc", 0.70),
		("arthritis", 0.65),
		("kidney stones", 0.60),
		("spinal stenosis", 0.55)
	],
	"stomach ache": [
		("gastroenteritis", 0.80),
		("irritable bowel syndrome", 0.70),
		("food poisoning", 0.75),
		("gastritis", 0.65),
		("appendicitis", 0.60)
	],
	"abdominal pain": [
		("appendicitis", 0.80),
		("gastroenteritis", 0.75),
		("gallstones", 0.70),
		("irritable bowel syndrome", 0.65),
		("kidney stones", 0.60)
	],
	"rash": [
		("allergic reaction", 0.80),
		("contact dermatitis", 0.75),
		("eczema", 0.70),
		("psoriasis", 0.60),
		("viral infection", 0.55)
	],
	"swollen": [
		("edema", 0.85),
		("inflammation", 0.80),
		("allergic reaction", 0.70),
		("infection", 0.65),
		("injury", 0.60)
	],
	"swelling": [
		("edema", 0.90),
		("inflammation", 0.85),
		("allergic reaction", 0.75),
		("infection", 0.70),
		("injury", 0.65)
	],
	"bleeding": [
		("hemorrhage", 0.85),
		("injury", 0.80),
		("ulcer", 0.70),
		("hemorrhoids", 0.65),
		("menstrual disorder", 0.60)
	],
	"itchy": [
		("allergic reaction", 0.80),
		("eczema", 0.75),
		("contact dermatitis", 0.70),
		("psoriasis", 0.60),
		("dry skin", 0.55)
	],
	"itching": [
		("allergic reaction", 0.85),
		("eczema", 0.80),
		("contact dermatitis", 0.75),
		("psoriasis", 0.65),
		("dry skin", 0.60)
	],
	"shortness of breath": [
		("asthma", 0.85),
		("heart failure", 0.80),
		("pneumonia", 0.75),
		("anxiety", 0.70),
		("copd", 0.65)
	],
	"breathing difficulty": [
		("asthma", 0.90),
		("heart failure", 0.85),
		("pneumonia", 0.80),
		("anxiety", 0.75),
		("copd", 0.70)
	],
	"joint pain": [
		("arthritis", 0.85),
		("rheumatoid arthritis", 0.80),
		("osteoarthritis", 0.75),
		("gout", 0.70),
		("fibromyalgia", 0.60)
	],
	"muscle pain": [
		("muscle strain", 0.85),
		("fibromyalgia", 0.80),
		("tendonitis", 0.70),
		("overuse injury", 0.65),
		("viral infection", 0.60)
	],
	"weakness": [
		("anemia", 0.80),
		("stroke", 0.75),
		("multiple sclerosis", 0.70),
		("thyroid disorder", 0.65),
		("dehydration", 0.60)
	],
	"confusion": [
		("stroke", 0.85),
		("dementia", 0.80),
		("dehydration", 0.70),
		("low blood sugar", 0.65),
		("concussion", 0.60)
	],
	"seizure": [
		("epilepsy", 0.95),
		("febrile seizure", 0.80),
		("brain injury", 0.70),
		("stroke", 0.65),
		("metabolic disorder", 0.60)
	],
	"fainting": [
		("syncope", 0.90),
		("low blood pressure", 0.80),
		("dehydration", 0.70),
		("heart condition", 0.65),
		("anxiety", 0.60)
	],
	"faint": [
		("syncope", 0.85),
		("low blood pressure", 0.75),
		("dehydration", 0.70),
		("heart condition", 0.65),
		("anxiety", 0.60)
	]
}

# Synonym expansion for better keyword recognition
SYNONYM_EXPANSIONS = {
	"headache": ["head pain", "head ache", "cranial pain", "cephalgia"],
	"fever": ["temperature", "high temp", "hot", "burning up", "febrile"],
	"cough": ["coughing", "hacking", "persistent cough"],
	"chest pain": ["chest pressure", "chest tightness", "chest discomfort"],
	"nausea": ["nauseous", "queasy", "sick feeling", "upset stomach"],
	"vomiting": ["vomit", "throwing up", "puking", "emesis"],
	"diarrhea": ["loose stools", "watery stools", "frequent bowel movements"],
	"tired": ["fatigue", "exhausted", "weary", "lethargic"],
	"dizzy": ["dizziness", "lightheaded", "vertigo", "unsteady"],
	"sore throat": ["throat pain", "pharyngitis", "throat irritation"],
	"back pain": ["backache", "spinal pain", "lumbar pain"],
	"stomach ache": ["abdominal pain", "belly pain", "tummy ache", "stomach pain"],
	"rash": ["skin rash", "redness", "skin irritation", "dermatitis"],
	"swollen": ["swelling", "puffiness", "inflammation", "edema"],
	"bleeding": ["blood", "hemorrhage", "blood loss"],
	"itchy": ["itching", "pruritus", "skin irritation"],
	"shortness of breath": ["breathing difficulty", "dyspnea", "can't breathe"],
	"joint pain": ["arthralgia", "joint stiffness", "joint inflammation"],
	"muscle pain": ["myalgia", "muscle ache", "muscle soreness"],
	"weakness": ["muscle weakness", "generalized weakness", "fatigue"],
	"confusion": ["disorientation", "mental fog", "brain fog"],
	"seizure": ["convulsions", "uncontrollable shaking", "fits"],
	"fainting": ["faint", "passing out", "syncope", "blackout"]
}

# Emergency keyword patterns that should trigger high priority
EMERGENCY_KEYWORDS = {
	"chest pain": "heart attack",
	"shortness of breath": "respiratory emergency", 
	"severe headache": "stroke",
	"confusion": "stroke",
	"seizure": "epilepsy",
	"fainting": "syncope",
	"severe bleeding": "hemorrhage",
	"unconscious": "emergency"
}

def _get_classifier():
	global _classifier
	if _classifier is not None:
		return _classifier
	with _classifier_lock:
		if _classifier is None:
			if pipeline is None:
				return None
			model_name = os.getenv("HF_ZS_MODEL", "facebook/bart-large-mnli")
			_classifier = pipeline(
				"zero-shot-classification",
				model=model_name,
				device=-1,
			)
	return _classifier

def _expand_synonyms(text: str) -> str:
	"""Expand synonyms in the text for better matching."""
	text_lower = text.lower()
	expanded_text = text_lower
	
	for main_term, synonyms in SYNONYM_EXPANSIONS.items():
		if main_term in text_lower:
			# Add synonyms to the text
			expanded_text += " " + " ".join(synonyms)
		else:
			# Check if any synonym is present and add main term
			for synonym in synonyms:
				if synonym in text_lower:
					expanded_text += " " + main_term
					break
	
	return expanded_text

def _get_simple_keyword_suggestions(text: str, age: Optional[int] = None, 
								   duration_hours: Optional[float] = None, 
								   medical_history: Optional[str] = None) -> List[Dict[str, any]]:
	"""Get suggestions for simple keyword inputs with high accuracy."""
	text_lower = text.lower().strip()
	suggestions = []
	
	# Direct keyword matching
	if text_lower in SIMPLE_KEYWORD_MAPPINGS:
		conditions = SIMPLE_KEYWORD_MAPPINGS[text_lower]
		for condition, base_score in conditions:
			# Apply age adjustments
			adjusted_score = base_score
			if age is not None:
				adjusted_score = _apply_age_adjustments(condition, adjusted_score, age)
			
			# Apply duration adjustments
			if duration_hours is not None:
				adjusted_score = _apply_duration_adjustments(condition, adjusted_score, duration_hours)
			
			# Apply medical history adjustments
			if medical_history:
				adjusted_score = _apply_history_adjustments(condition, adjusted_score, medical_history)
			
			suggestions.append({
				"condition": condition,
				"score": min(1.0, adjusted_score),
				"severity": _get_condition_severity(condition),
				"category": _get_condition_category(condition),
				"confidence": "high" if adjusted_score > 0.7 else "moderate"
			})
	
	# Check for emergency patterns
	for keyword, emergency_condition in EMERGENCY_KEYWORDS.items():
		if keyword in text_lower:
			emergency_score = 0.9 if "severe" in text_lower else 0.8
			suggestions.append({
				"condition": emergency_condition,
				"score": emergency_score,
				"severity": "emergency",
				"category": "emergency",
				"confidence": "high"
			})
	
	# Sort by score and return top suggestions
	suggestions.sort(key=lambda x: x["score"], reverse=True)
	return suggestions[:5]

def _apply_age_adjustments(condition: str, score: float, age: int) -> float:
	"""Apply age-based adjustments to condition scores."""
	# Pediatric conditions (0-17)
	if age < 18:
		pediatric_conditions = ["febrile seizure", "croup", "hand foot mouth disease", "chickenpox"]
		if condition in pediatric_conditions:
			return min(1.0, score * 1.3)
		# Reduce adult conditions
		adult_conditions = ["dementia", "alzheimer's", "prostate cancer", "menopause"]
		if condition in adult_conditions:
			return score * 0.5
	
	# Geriatric conditions (65+)
	elif age >= 65:
		geriatric_conditions = ["dementia", "alzheimer's", "stroke", "pneumonia", "fall risk"]
		if condition in geriatric_conditions:
			return min(1.0, score * 1.2)
		# Reduce pediatric conditions
		pediatric_conditions = ["croup", "hand foot mouth disease", "chickenpox", "measles"]
		if condition in pediatric_conditions:
			return score * 0.3
	
	return score

def _apply_duration_adjustments(condition: str, score: float, duration_hours: float) -> float:
	"""Apply duration-based adjustments to condition scores."""
	# Acute conditions (0-6 hours)
	if duration_hours <= 6:
		acute_conditions = ["heart attack", "stroke", "appendicitis", "gallstones", "anaphylaxis"]
		if condition in acute_conditions:
			return min(1.0, score * 1.2)
		# Reduce chronic conditions
		chronic_conditions = ["fibromyalgia", "irritable bowel syndrome", "chronic fatigue syndrome"]
		if condition in chronic_conditions:
			return score * 0.7
	
	# Chronic conditions (>7 days)
	elif duration_hours > 168:
		chronic_conditions = ["fibromyalgia", "irritable bowel syndrome", "chronic fatigue syndrome", "arthritis"]
		if condition in chronic_conditions:
			return min(1.0, score * 1.2)
		# Reduce acute conditions
		acute_conditions = ["appendicitis", "gallstones", "food poisoning"]
		if condition in acute_conditions:
			return score * 0.6
	
	return score

def _apply_history_adjustments(condition: str, score: float, medical_history: str) -> float:
	"""Apply medical history adjustments to condition scores."""
	history_lower = medical_history.lower()
	
	# Diabetes-related
	if any(term in history_lower for term in ["diabetes", "diabetic"]):
		diabetes_conditions = ["diabetes", "diabetic ketoacidosis", "hypoglycemia", "diabetic neuropathy"]
		if condition in diabetes_conditions:
			return min(1.0, score * 1.3)
	
	# Cardiovascular
	if any(term in history_lower for term in ["heart", "cardiac", "hypertension", "high blood pressure"]):
		cardiac_conditions = ["heart attack", "stroke", "heart failure", "angina"]
		if condition in cardiac_conditions:
			return min(1.0, score * 1.2)
	
	# Respiratory
	if any(term in history_lower for term in ["asthma", "copd", "lung"]):
		respiratory_conditions = ["asthma", "copd", "pneumonia", "bronchitis"]
		if condition in respiratory_conditions:
			return min(1.0, score * 1.2)
	
	return score

def _get_condition_severity(condition: str) -> str:
	"""Get severity level for a condition."""
	emergency_conditions = [
		"heart attack", "stroke", "anaphylaxis", "septic shock", "cardiac arrest",
		"respiratory emergency", "severe bleeding", "hemorrhage", "syncope"
	]
	
	urgent_conditions = [
		"pneumonia", "appendicitis", "gallstones", "kidney stones", "meningitis",
		"sepsis", "diabetic ketoacidosis", "hypoglycemia", "epilepsy"
	]
	
	if condition in emergency_conditions:
		return "emergency"
	elif condition in urgent_conditions:
		return "urgent"
	else:
		return "routine"

def _get_condition_category(condition: str) -> str:
	"""Get category for a condition."""
	categories = {
		"cardiovascular": ["heart attack", "stroke", "angina", "heart failure", "syncope"],
		"respiratory": ["pneumonia", "asthma", "copd", "bronchitis", "respiratory infection"],
		"neurological": ["migraine", "tension headache", "epilepsy", "vertigo", "dementia"],
		"gastrointestinal": ["gastroenteritis", "food poisoning", "appendicitis", "gallstones", "irritable bowel syndrome"],
		"dermatological": ["allergic reaction", "eczema", "psoriasis", "contact dermatitis"],
		"musculoskeletal": ["arthritis", "muscle strain", "fibromyalgia", "tendonitis"],
		"endocrine": ["diabetes", "thyroid disorder", "diabetic ketoacidosis", "hypoglycemia"],
		"mental_health": ["depression", "anxiety", "chronic fatigue syndrome"],
		"infectious": ["influenza", "covid-19", "viral infection", "bacterial infection", "strep throat"]
	}
	
	for category, conditions in categories.items():
		if condition in conditions:
			return category
	
	return "general"

def suggest_fine_tuned_conditions(symptom_text: str, k: int = 5, age: Optional[int] = None, 
								 duration_hours: Optional[float] = None, medical_history: Optional[str] = None) -> List[Dict[str, any]]:
	"""Fine-tuned condition suggestion that works well for both simple and complex inputs."""
	text = (symptom_text or "").strip()
	if not text:
		return []
	
	# First try simple keyword matching for single words or short phrases
	words = text.lower().split()
	if len(words) <= 3:  # Simple input
		simple_suggestions = _get_simple_keyword_suggestions(text, age, duration_hours, medical_history)
		if simple_suggestions:
			return simple_suggestions[:k]
	
	# For more complex inputs, use the enhanced model
	classifier = _get_classifier()
	if classifier is not None:
		# Expand synonyms for better matching
		expanded_text = _expand_synonyms(text)
		
		# Get all possible conditions
		all_conditions = []
		for conditions in SIMPLE_KEYWORD_MAPPINGS.values():
			all_conditions.extend([cond[0] for cond in conditions])
		
		# Remove duplicates while preserving order
		unique_conditions = list(dict.fromkeys(all_conditions))
		
		result = classifier(
			expanded_text,
			unique_conditions,
			multi_label=True,
			hypothesis_template="These symptoms are consistent with {}."
		)
		
		# Process results
		suggestions = []
		for condition, score in zip(result["labels"], result["scores"]):
			# Apply contextual adjustments
			adjusted_score = score
			
			if age is not None:
				adjusted_score = _apply_age_adjustments(condition, adjusted_score, age)
			
			if duration_hours is not None:
				adjusted_score = _apply_duration_adjustments(condition, adjusted_score, duration_hours)
			
			if medical_history:
				adjusted_score = _apply_history_adjustments(condition, adjusted_score, medical_history)
			
			# Boost score for emergency conditions
			if condition in ["heart attack", "stroke", "anaphylaxis"] and any(term in text.lower() for term in ["severe", "intense", "emergency"]):
				adjusted_score = min(1.0, adjusted_score * 1.3)
			
			suggestions.append({
				"condition": condition,
				"score": min(1.0, adjusted_score),
				"severity": _get_condition_severity(condition),
				"category": _get_condition_category(condition),
				"confidence": "high" if adjusted_score > 0.7 else "moderate" if adjusted_score > 0.5 else "low"
			})
		
		# Sort by score and return top k
		suggestions.sort(key=lambda x: x["score"], reverse=True)
		return suggestions[:k]
	
	# Fallback to simple keyword matching
	return _get_simple_keyword_suggestions(text, age, duration_hours, medical_history)[:k]

def get_condition_recommendations(condition: str) -> Dict[str, List[str]]:
	"""Get specific recommendations for a condition."""
	recommendations = {
		"heart attack": {
			"immediate_actions": [
				"🚨 Call emergency services immediately (911/999/112)",
				"🚨 Do not drive yourself - use emergency services",
				"🚨 Chew aspirin if available and not allergic",
				"🚨 Stay calm and rest while waiting for help"
			],
			"warning_signs": [
				"Chest pain or pressure lasting more than a few minutes",
				"Pain spreading to arm, neck, jaw, or back",
				"Shortness of breath with or without chest pain",
				"Nausea, vomiting, or cold sweats"
			]
		},
		"stroke": {
			"immediate_actions": [
				"🚨 Call emergency services immediately",
				"🚨 Note the time symptoms started (critical for treatment)",
				"🚨 Do not give food or drink",
				"🚨 Keep person calm and comfortable"
			],
			"warning_signs": [
				"Facial drooping (one side of face droops)",
				"Arm weakness (one arm drifts down)",
				"Speech difficulty (slurred or strange speech)",
				"Time to call emergency services"
			]
		},
		"migraine": {
			"immediate_actions": [
				"🌙 Rest in a dark, quiet room",
				"💊 Take migraine medication as prescribed",
				"🧊 Apply cold compress to head or neck",
				"💧 Stay hydrated"
			],
			"prevention": [
				"Identify and avoid triggers",
				"Maintain regular sleep schedule",
				"Eat regular meals, stay hydrated"
			]
		},
		"pneumonia": {
			"immediate_actions": [
				"🏥 Seek medical attention within 24 hours",
				"💊 Take prescribed antibiotics as directed",
				"💧 Stay hydrated and get plenty of rest",
				"🌡️ Monitor fever and breathing"
			],
			"warning_signs": [
				"High fever (101°F/38.3°C or higher)",
				"Cough with yellow, green, or bloody mucus",
				"Shortness of breath or rapid breathing"
			]
		}
	}
	
	return recommendations.get(condition, {
		"immediate_actions": ["Consult with a healthcare provider"],
		"warning_signs": ["Monitor symptoms closely"],
		"prevention": ["Follow medical advice"]
	})

