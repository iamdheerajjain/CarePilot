from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re


@dataclass
class TriageResult:
	level: str  # "Emergency" | "Urgent" | "Routine" | "Self-care"
	reasons: List[str]
	actions: List[str]


EMERGENCY_PATTERNS = [
	# Cardiovascular emergencies
	re.compile(r"\b(chest pain|pressure|tightness|squeezing|crushing)\b", re.I),
	re.compile(r"\b(short(ness)? of breath|difficulty breathing|can't breathe|struggling to breathe)\b", re.I),
	re.compile(r"\b(sudden weakness|facial droop|slurred speech|one-sided weakness|arm weakness)\b", re.I),
	re.compile(r"\b(irregular heartbeat|racing heart|palpitations|heart skipping)\b", re.I),
	
	# Neurological emergencies
	re.compile(r"\b(violent|worst|thunderclap|sudden severe) headache\b", re.I),
	re.compile(r"\b(confusion|loss of consciousness|faint(ed|ing)|unresponsive)\b", re.I),
	re.compile(r"\b(seizure|convulsions|uncontrollable shaking|epileptic)\b", re.I),
	re.compile(r"\b(sudden vision loss|double vision|blind spot)\b", re.I),
	
	# Respiratory emergencies
	re.compile(r"\b(anaphylaxis|throat swelling|can't breathe|airway obstruction)\b", re.I),
	re.compile(r"\b(severe asthma attack|wheezing severely|blue lips|cyanosis)\b", re.I),
	
	# Trauma and bleeding
	re.compile(r"\b(severe bleeding|uncontrolled bleeding|profuse bleeding|arterial bleeding)\b", re.I),
	re.compile(r"\b(head injury|concussion|loss of consciousness|memory loss)\b", re.I),
	re.compile(r"\b(severe burn|third degree|chemical burn)\b", re.I),
	
	# Abdominal emergencies
	re.compile(r"\b(severe abdominal pain|peritonitis|rigid abdomen)\b", re.I),
	re.compile(r"\b(vomiting blood|hematemesis|black stools|melena)\b", re.I),
	
	# Metabolic emergencies
	re.compile(r"\b(diabetic ketoacidosis|DKA|high blood sugar|ketones)\b", re.I),
	re.compile(r"\b(severe hypoglycemia|low blood sugar|diabetic coma)\b", re.I),
	re.compile(r"\b(heat stroke|hyperthermia|no sweating|hot and dry)\b", re.I),
	re.compile(r"\b(hypothermia|severe cold|shivering uncontrollably)\b", re.I),
	
	# Poisoning and overdose
	re.compile(r"\b(drug overdose|alcohol poisoning|suicide attempt|poisoning)\b", re.I),
	re.compile(r"\b(carbon monoxide|CO poisoning|headache nausea confusion)\b", re.I),
	
	# Pediatric emergencies
	re.compile(r"\b(high fever|febrile seizure|temperature over 104)\b", re.I),
	re.compile(r"\b(severe dehydration|no urination|sunken eyes|dry mouth)\b", re.I),
	re.compile(r"\b(croup|barking cough|stridor|difficulty breathing)\b", re.I),
]

URGENT_PATTERNS = [
	# Fever and infection
	re.compile(r"\b(fever|temperature|high temp|chills)\b", re.I),
	re.compile(r"\b(persistent fever|fever for days|fever not responding)\b", re.I),
	re.compile(r"\b(severe infection|worsening infection|spreading infection)\b", re.I),
	
	# Pain patterns
	re.compile(r"\b(severe pain|intense pain|unbearable pain|pain scale 8|pain scale 9|pain scale 10)\b", re.I),
	re.compile(r"\b(persistent pain|pain not improving|pain getting worse)\b", re.I),
	re.compile(r"\b(abdominal pain|stomach pain|belly pain)\b", re.I),
	re.compile(r"\b(chest pain|chest discomfort|chest pressure)\b", re.I),
	
	# Gastrointestinal urgent
	re.compile(r"\b(persistent vomiting|unable to keep fluids down|vomiting blood)\b", re.I),
	re.compile(r"\b(severe diarrhea|bloody diarrhea|dehydration)\b", re.I),
	re.compile(r"\b(severe nausea|constant nausea|can't eat)\b", re.I),
	
	# Respiratory urgent
	re.compile(r"\b(coughing blood|hemoptysis|blood in sputum)\b", re.I),
	re.compile(r"\b(worsening cough|cough not improving|persistent cough)\b", re.I),
	re.compile(r"\b(shortness of breath|breathing difficulty|can't catch breath)\b", re.I),
	
	# Neurological urgent
	re.compile(r"\b(severe headache|migraine|headache not responding)\b", re.I),
	re.compile(r"\b(confusion|disorientation|memory problems)\b", re.I),
	re.compile(r"\b(seizure|convulsions|uncontrollable shaking)\b", re.I),
	
	# Cardiovascular urgent
	re.compile(r"\b(chest pain|chest pressure|chest tightness)\b", re.I),
	re.compile(r"\b(irregular heartbeat|palpitations|racing heart)\b", re.I),
	re.compile(r"\b(dizziness|lightheadedness|feeling faint)\b", re.I),
	
	# Genitourinary urgent
	re.compile(r"\b(painful urination|burning urination|blood in urine)\b", re.I),
	re.compile(r"\b(severe back pain|flank pain|kidney pain)\b", re.I),
	re.compile(r"\b(inability to urinate|urinary retention|no urination)\b", re.I),
	
	# Dermatological urgent
	re.compile(r"\b(severe rash|spreading rash|rash with fever)\b", re.I),
	re.compile(r"\b(allergic reaction|swelling|hives)\b", re.I),
	re.compile(r"\b(severe itching|uncontrollable itching)\b", re.I),
	
	# Musculoskeletal urgent
	re.compile(r"\b(severe back pain|back pain with numbness|back pain with weakness)\b", re.I),
	re.compile(r"\b(joint swelling|severe joint pain|joint deformity)\b", re.I),
	re.compile(r"\b(inability to move|paralysis|numbness)\b", re.I),
	
	# Pediatric urgent
	re.compile(r"\b(fever in infant|fever under 3 months|high fever child)\b", re.I),
	re.compile(r"\b(severe dehydration|no wet diapers|sunken fontanelle)\b", re.I),
	re.compile(r"\b(severe croup|barking cough|stridor)\b", re.I),
	
	# Geriatric urgent
	re.compile(r"\b(fever in elderly|confusion in elderly|fall in elderly)\b", re.I),
	re.compile(r"\b(severe weakness|inability to walk|bedridden)\b", re.I),
	
	# Mental health urgent
	re.compile(r"\b(suicidal thoughts|self harm|suicide attempt)\b", re.I),
	re.compile(r"\b(severe depression|hopelessness|can't function)\b", re.I),
	re.compile(r"\b(severe anxiety|panic attack|can't calm down)\b", re.I),
]


def compute_triage(symptom_text: str, age: Optional[int] = None, duration_hours: Optional[float] = None, medical_history: Optional[str] = None, pain_scale: Optional[int] = None, severity: Optional[str] = None) -> TriageResult:
	text = (symptom_text or "").strip()
	reasons: List[str] = []
	urgency_multiplier = 1.0
	
	# Enhanced age-based risk adjustments
	if age is not None:
		if age < 1:
			urgency_multiplier = 2.5  # Infants are very high risk
			reasons.append("Infant under 1 year - very high risk")
		elif age < 3:
			urgency_multiplier = 2.0  # Toddlers are high risk
			reasons.append("Child under 3 years - high risk")
		elif age < 12:
			urgency_multiplier = 1.3  # Children are higher risk
			reasons.append("Child under 12 years - higher risk")
		elif age >= 80:
			urgency_multiplier = 1.8  # Very elderly are very high risk
			reasons.append("Age 80+ - very high risk")
		elif age >= 65:
			urgency_multiplier = 1.4  # Elderly are higher risk
			reasons.append("Age 65+ - higher risk")
		elif age >= 50:
			urgency_multiplier = 1.1  # Middle-aged are slightly higher risk
			reasons.append("Age 50+ - slightly higher risk")
	
	# Enhanced duration-based adjustments
	if duration_hours is not None:
		if duration_hours < 0.5:  # Less than 30 minutes
			urgency_multiplier *= 1.4  # Very recent onset
			reasons.append("Very recent onset (< 30 minutes)")
		elif duration_hours < 1:
			urgency_multiplier *= 1.3  # Recent onset
			reasons.append("Recent onset (< 1 hour)")
		elif duration_hours < 6:
			urgency_multiplier *= 1.2  # Acute onset
			reasons.append("Acute onset (< 6 hours)")
		elif duration_hours > 168:  # 7 days
			reasons.append("Symptoms persist > 7 days")
		elif duration_hours > 72:  # 3 days
			reasons.append("Symptoms persist > 3 days")
		elif duration_hours > 24:  # 1 day
			reasons.append("Symptoms persist > 24 hours")
	
	# Enhanced medical history considerations
	if medical_history:
		history_lower = medical_history.lower()
		
		# High-risk conditions
		if any(term in history_lower for term in ["diabetes", "diabetic", "heart disease", "hypertension", "high blood pressure", "coronary artery disease"]):
			urgency_multiplier *= 1.3
			reasons.append("Cardiovascular risk factors")
		
		if any(term in history_lower for term in ["immunocompromised", "cancer", "chemotherapy", "transplant", "hiv", "aids"]):
			urgency_multiplier *= 1.6
			reasons.append("Immunocompromised status - high risk")
		
		if any(term in history_lower for term in ["pregnancy", "pregnant", "gestational"]):
			urgency_multiplier *= 1.4
			reasons.append("Pregnancy - higher risk")
		
		if any(term in history_lower for term in ["stroke", "cerebrovascular", "neurological", "seizure", "epilepsy"]):
			urgency_multiplier *= 1.3
			reasons.append("Neurological history")
		
		if any(term in history_lower for term in ["asthma", "copd", "lung disease", "respiratory"]):
			urgency_multiplier *= 1.2
			reasons.append("Respiratory history")
		
		if any(term in history_lower for term in ["kidney disease", "renal", "dialysis", "liver disease", "hepatic"]):
			urgency_multiplier *= 1.3
			reasons.append("Organ dysfunction")
	
	# Enhanced pain and severity adjustments
	if pain_scale is not None:
		if pain_scale >= 9:
			urgency_multiplier *= 1.8
			reasons.append(f"Severe pain level ({pain_scale}/10) - immediate attention needed")
		elif pain_scale >= 8:
			urgency_multiplier *= 1.6
			reasons.append(f"Very high pain level ({pain_scale}/10)")
		elif pain_scale >= 7:
			urgency_multiplier *= 1.4
			reasons.append(f"High pain level ({pain_scale}/10)")
		elif pain_scale >= 5:
			urgency_multiplier *= 1.2
			reasons.append(f"Moderate pain level ({pain_scale}/10)")
		elif pain_scale > 0:
			reasons.append(f"Mild pain level ({pain_scale}/10)")
	
	if severity:
		if severity.lower() == "severe":
			urgency_multiplier *= 1.6
			reasons.append("Severe symptom severity")
		elif severity.lower() == "moderate":
			urgency_multiplier *= 1.2
			reasons.append("Moderate symptom severity")
		else:
			reasons.append("Mild symptom severity")
	
	# Enhanced emergency pattern detection
	emergency_found = False
	emergency_reasons = []
	
	for pattern in EMERGENCY_PATTERNS:
		if pattern.search(text):
			emergency_found = True
			emergency_reasons.append(f"Emergency red flag detected")
	
	if emergency_found:
		return TriageResult(
			level="Emergency",
			reasons=emergency_reasons + reasons,
			actions=[
				"🚨 Call your local emergency number immediately (911, 999, 112, etc.)",
				"🚨 Do not drive yourself - use emergency services",
				"🚨 If unconscious, call emergency services and begin CPR if trained",
				"🚨 Stay with the person until help arrives",
				"🚨 Do not delay - every minute counts in emergencies",
			],
		)
	
	# Enhanced urgent pattern detection
	urgent_reasons: List[str] = []
	urgent_count = 0
	
	for pattern in URGENT_PATTERNS:
		if pattern.search(text):
			urgent_count += 1
			urgent_reasons.append(f"Urgent concern detected")
	
	# Enhanced age-specific urgent conditions
	if age is not None:
		if age >= 65 and any(term in text.lower() for term in ["fever", "temperature", "chills", "confusion"]):
			urgent_reasons.append("Age 65+ with fever/confusion - high risk")
			urgent_count += 2
		if age < 3 and any(term in text.lower() for term in ["fever", "temperature", "chills"]):
			urgent_reasons.append("Child under 3 with fever - high risk")
			urgent_count += 2
		if age < 1 and any(term in text.lower() for term in ["fever", "temperature"]):
			urgent_reasons.append("Infant with fever - immediate attention needed")
			urgent_count += 3
		if age < 6 and any(term in text.lower() for term in ["croup", "barking cough", "stridor"]):
			urgent_reasons.append("Young child with respiratory distress - urgent")
			urgent_count += 2
	
	# Enhanced duration-based urgent conditions
	if duration_hours is not None:
		if duration_hours > 24 and any(term in text.lower() for term in ["fever", "pain", "nausea", "vomiting", "diarrhea"]):
			urgent_reasons.append("Symptoms persisting > 24 hours")
			urgent_count += 1
		if duration_hours > 48 and any(term in text.lower() for term in ["fever", "pain", "nausea", "vomiting"]):
			urgent_reasons.append("Symptoms persisting > 48 hours")
			urgent_count += 1
	
	# Enhanced severity-based urgent conditions
	if pain_scale is not None and pain_scale >= 7:
		urgent_reasons.append(f"High pain level ({pain_scale}/10) - urgent evaluation needed")
		urgent_count += 1
	
	if severity and severity.lower() == "severe":
		urgent_reasons.append("Severe symptom severity - urgent evaluation needed")
		urgent_count += 1
	
	# Apply enhanced urgency multiplier
	if urgent_count > 0:
		adjusted_urgency = urgent_count * urgency_multiplier
		if adjusted_urgency >= 3.0:
			return TriageResult(
				level="Urgent",
				reasons=urgent_reasons + reasons,
				actions=[
					"🏥 Seek urgent care or contact your healthcare provider within 12 hours",
					"🏥 Consider visiting urgent care center or emergency department",
					"📞 Call your doctor's office for same-day appointment",
					"⚠️ If symptoms worsen or new red flags develop, call emergency services",
					"📝 Keep track of symptoms and any changes",
					"🔄 Monitor closely and seek immediate care if condition deteriorates",
				],
			)
		elif adjusted_urgency >= 2.0:
			return TriageResult(
				level="Urgent",
				reasons=urgent_reasons + reasons,
				actions=[
					"🏥 Seek urgent care or contact your healthcare provider within 24 hours",
					"🏥 Consider visiting urgent care center if symptoms worsen",
					"📞 Call your doctor's office for appointment within 1-2 days",
					"⚠️ If symptoms worsen or new red flags develop, seek immediate care",
					"📝 Keep track of symptoms and any changes",
				],
			)
	
	# Enhanced routine vs self-care based on duration and severity
	if duration_hours is not None and duration_hours > 168:  # 7 days
		return TriageResult(
			level="Routine",
			reasons=["Symptoms persist > 7 days"] + reasons,
			actions=[
				"📅 Schedule a routine appointment with your primary care provider",
				"📝 Keep a detailed symptom diary and bring it to your visit",
				"📊 Note symptom patterns, triggers, and any treatments tried",
				"🔄 Monitor symptoms and seek care if they worsen",
				"💊 Consider over-the-counter treatments as appropriate",
			],
		)
	
	# Check for moderate symptoms that might need routine care
	moderate_symptoms = any(term in text.lower() for term in [
		"persistent", "ongoing", "recurring", "chronic", "daily", "frequent", "intermittent"
	])
	
	if moderate_symptoms and duration_hours and duration_hours > 72:  # 3 days
		return TriageResult(
			level="Routine",
			reasons=["Moderate persistent symptoms"] + reasons,
			actions=[
				"📅 Schedule appointment with your healthcare provider within 1-2 weeks",
				"📝 Document symptoms, triggers, and treatments tried",
				"🔄 Continue monitoring and seek care if symptoms worsen",
				"💊 Consider over-the-counter treatments as appropriate",
			],
		)
	
	# Enhanced self-care recommendations
	return TriageResult(
		level="Self-care",
		reasons=["No urgent red flags detected"] + reasons,
		actions=[
			"🏠 Consider rest, fluids, and over-the-counter symptom relief as appropriate",
			"📊 Monitor symptoms closely for any changes or worsening",
			"📝 Keep track of symptom progression and triggers",
			"🔄 If symptoms worsen, persist beyond 3 days, or new symptoms develop, seek medical advice",
			"📞 Contact healthcare provider if you have concerns",
			"💊 Use appropriate over-the-counter medications as directed",
			"🥤 Stay hydrated and get adequate rest",
		],
	)
