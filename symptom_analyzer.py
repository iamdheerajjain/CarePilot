from typing import Dict, List, Any

def analyze_symptom_patterns(symptom_text: str) -> Dict[str, Any]:
	"""Analyze symptom patterns for better understanding."""
	text = symptom_text.lower()
	
	analysis = {
		"symptom_details": _extract_symptom_details(symptom_text),
		"pattern_matches": [],
		"body_systems_affected": [],
		"urgency_level": "routine"
	}
	
	# Check for pattern matches
	for category, patterns in SYMPTOM_PATTERNS.items():
		if isinstance(patterns, dict):
			for pattern_type, pattern_list in patterns.items():
				if any(pattern in text for pattern in pattern_list):
					analysis["pattern_matches"].append(f"{category}_{pattern_type}")
		else:
			if any(pattern in text for pattern in patterns):
				analysis["pattern_matches"].append(category)
	
	# Determine body systems affected
	body_system_keywords = {
		"cardiovascular": ["chest", "heart", "breathing", "palpitations"],
		"neurological": ["head", "brain", "seizure", "confusion", "weakness"],
		"respiratory": ["cough", "breathing", "lung", "chest"],
		"gastrointestinal": ["stomach", "abdomen", "nausea", "vomiting", "diarrhea"],
		"musculoskeletal": ["joint", "muscle", "bone", "back", "pain"],
		"dermatological": ["skin", "rash", "itching", "swelling"]
	}
	
	for system, keywords in body_system_keywords.items():
		if any(keyword in text for keyword in keywords):
			analysis["body_systems_affected"].append(system)
	
	# Determine urgency level
	emergency_keywords = ["emergency", "urgent", "severe", "unbearable", "can't breathe", "chest pain"]
	urgent_keywords = ["moderate", "persistent", "worsening", "fever", "pain"]
	
	if any(keyword in text for keyword in emergency_keywords):
		analysis["urgency_level"] = "emergency"
	elif any(keyword in text for keyword in urgent_keywords):
		analysis["urgency_level"] = "urgent"
	
	return analysis

def _extract_symptom_details(symptom_text: str) -> Dict[str, Any]:
	"""Extract detailed symptom information for better analysis."""
	text = symptom_text.lower()
	
	details = {
		"severity": "mild",
		"duration": "unknown",
		"onset": "gradual",
		"triggers": [],
		"associated_symptoms": [],
		"body_parts": [],
		"quality": "unknown"
	}
	
	# Severity assessment
	severity_keywords = {
		"mild": ["mild", "slight", "minor", "low"],
		"moderate": ["moderate", "medium", "noticeable"],
		"severe": ["severe", "intense", "unbearable", "excruciating", "worst"],
		"emergency": ["emergency", "urgent", "critical", "life-threatening"]
	}
	
	for level, keywords in severity_keywords.items():
		if any(keyword in text for keyword in keywords):
			details["severity"] = level
			break
	
	# Duration assessment
	duration_patterns = {
		"acute": ["sudden", "acute", "immediate", "just started", "minutes ago"],
		"subacute": ["hours ago", "this morning", "yesterday", "few days"],
		"chronic": ["weeks", "months", "years", "ongoing", "persistent", "recurring"]
	}
	
	for duration, patterns in duration_patterns.items():
		if any(pattern in text for pattern in patterns):
			details["duration"] = duration
			break
	
	# Onset assessment
	onset_patterns = {
		"sudden": ["sudden", "acute", "immediate", "all at once"],
		"gradual": ["gradual", "slowly", "over time", "progressively"],
		"intermittent": ["intermittent", "comes and goes", "episodic", "sporadic"]
	}
	
	for onset, patterns in onset_patterns.items():
		if any(pattern in text for pattern in patterns):
			details["onset"] = onset
			break
	
	# Body parts mentioned
	body_parts = [
		"head", "chest", "back", "stomach", "abdomen", "arm", "leg", "hand", "foot",
		"neck", "throat", "eye", "ear", "nose", "mouth", "heart", "lung", "kidney"
	]
	
	details["body_parts"] = [part for part in body_parts if part in text]
	
	return details

# Simplified symptom patterns for analysis
SYMPTOM_PATTERNS = {
	"chest_pain_types": {
		"crushing": ["crushing chest pain", "chest being crushed", "heavy chest pressure"],
		"burning": ["burning chest pain", "chest burning", "heartburn-like chest pain"],
		"pressure": ["chest pressure", "chest heaviness", "chest tightness", "chest squeezing"],
		"sharp": ["sharp chest pain", "stabbing chest pain", "knife-like chest pain"],
		"dull": ["dull chest pain", "aching chest pain", "chest discomfort"]
	},
	"cardiac_symptoms": {
		"chest_pain": ["chest pain", "chest pressure", "chest tightness", "chest discomfort", "chest burning"],
		"shortness_breath": ["shortness of breath", "dyspnea", "can't breathe", "struggling to breathe", "breathless"],
		"palpitations": ["palpitations", "irregular heartbeat", "racing heart", "heart skipping", "heart pounding"],
		"fatigue": ["fatigue", "tiredness", "exhaustion", "weakness", "lethargy"],
		"edema": ["swelling", "edema", "puffiness", "fluid retention", "ankle swelling"]
	},
	"neurological_symptoms": {
		"headache_types": {
			"migraine": ["throbbing headache", "pounding headache", "one-sided headache", "migraine"],
			"tension": ["tension headache", "band-like headache", "pressure headache"],
			"cluster": ["cluster headache", "severe one-sided headache", "eye pain"],
			"thunderclap": ["thunderclap headache", "sudden severe headache", "worst headache ever"]
		},
		"seizure_symptoms": ["seizure", "convulsions", "uncontrollable shaking", "jerking movements", "loss of consciousness"],
		"stroke_symptoms": ["facial droop", "arm weakness", "speech difficulty", "sudden weakness", "numbness"],
		"cognitive": ["confusion", "memory problems", "disorientation", "brain fog", "mental fog"]
	},
	"respiratory_symptoms": {
		"cough_types": {
			"productive": ["productive cough", "cough with phlegm", "cough with sputum"],
			"dry": ["dry cough", "hacking cough", "persistent cough"],
			"barking": ["barking cough", "croup cough", "seal-like cough"],
			"whooping": ["whooping cough", "pertussis", "paroxysmal cough"]
		},
		"breathing_difficulty": ["shortness of breath", "difficulty breathing", "labored breathing", "rapid breathing"],
		"respiratory_sounds": ["wheezing", "stridor", "crackles", "rales", "rhonchi"]
	},
	"gastrointestinal_symptoms": {
		"nausea_vomiting": ["nausea", "vomiting", "nauseous", "queasy", "throwing up"],
		"diarrhea": ["diarrhea", "loose stools", "watery stools", "frequent bowel movements"],
		"abdominal_pain": ["abdominal pain", "stomach pain", "belly pain", "tummy ache"],
		"digestive": ["indigestion", "heartburn", "acid reflux", "bloating", "gas"]
	}
}
