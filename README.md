# CarePilot: Quick Medical Triage Demo (Non-Diagnostic)

CarePilot is a Streamlit web app that collects symptoms via a short survey, performs lightweight condition suggestions (non-diagnostic), recommends a triage level, and provides helpful resources. It also includes optional anonymous feedback for learning and improvement.

Important: This app is for informational and educational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment.

## Features

- Symptom survey with clear disclaimers and consent.
- Zero-shot condition suggestion using a pretrained model (no training required).
- Rule-based triage: Emergency / Urgent / Routine / Self-care.
- Actionable guidance and links to reputable resources.
- Optional anonymous feedback stored locally.

## Quickstart

### 🚀 Easy Setup (Recommended)

**Windows users:**

```bash
setup.bat
```

**All platforms:**

```bash
python setup_carepilot.py
```

This will guide you through the entire setup process automatically!

### 📋 Manual Setup

### 1) Prerequisites

- Python 3.8+ (3.9–3.11 recommended)
- Internet connection (to download the pretrained model on first run)
- Supabase account (optional, for authentication and data persistence)

### 2) Install

```bash
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# Windows Command Prompt
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 3) Configure Supabase (Optional)

If you want authentication and data persistence:

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Copy `env.example` to `.env` and fill in your values:
   ```bash
   copy env.example .env
   ```
3. Get your project URL and anon key from your Supabase dashboard
4. Update `.env` with your actual values:
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   ```
5. Create the required tables in your Supabase SQL editor:

   ```sql
   -- Note: auth.users table is automatically created by Supabase Auth
   -- It contains: id, email, created_at, updated_at, email_confirmed_at, etc.

   -- Create surveys table (links to auth.users)
   CREATE TABLE surveys (
     id BIGSERIAL PRIMARY KEY,
     user_id UUID REFERENCES auth.users(id),
     age INTEGER NOT NULL,
     duration_hours DECIMAL NOT NULL,
     symptoms_text TEXT NOT NULL,
     medical_history TEXT,
     pain_scale INTEGER NOT NULL,
     severity TEXT NOT NULL,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );

   -- Create feedback table (links to auth.users)
   CREATE TABLE feedback (
     id BIGSERIAL PRIMARY KEY,
     user_id UUID REFERENCES auth.users(id),
     symptoms TEXT NOT NULL,
     predictions JSONB,
     correct_condition TEXT,
     helpful_score TEXT NOT NULL,
     comments TEXT,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );

   -- Enable Row Level Security
   ALTER TABLE surveys ENABLE ROW LEVEL SECURITY;
   ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

   -- Create policies (users can only see their own data)
   CREATE POLICY "Users can view own surveys" ON surveys FOR SELECT USING (auth.uid() = user_id);
   CREATE POLICY "Users can insert own surveys" ON surveys FOR INSERT WITH CHECK (auth.uid() = user_id);

   CREATE POLICY "Users can view own feedback" ON feedback FOR SELECT USING (auth.uid() = user_id);
   CREATE POLICY "Users can insert own feedback" ON feedback FOR INSERT WITH CHECK (auth.uid() = user_id);
   ```

6. **View user data** in your Supabase dashboard:

   - Go to **Authentication** → **Users** to see registered users
   - Go to **Table Editor** → **surveys** to see survey submissions
   - Go to **Table Editor** → **feedback** to see feedback data

   Or run this SQL query to see all data joined:

   ```sql
   SELECT
     u.email,
     u.created_at as user_created,
     s.age,
     s.symptoms_text,
     s.created_at as survey_created
   FROM auth.users u
   LEFT JOIN surveys s ON u.id = s.user_id
   ORDER BY s.created_at DESC;
   ```

### 4) Run

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## 🛠️ Database Management Tools

### View Stored Data

```bash
# View all data
python view_data.py

# Show statistics
python view_data.py stats

# Export data to JSON
python view_data.py export
```

### Test Database Functionality

```bash
# Run comprehensive database tests
python test_database.py
```

### Setup Database Tables

```bash
# Create required database tables
python setup_database.py
```

## 📊 What Gets Stored

### User Data (auth.users table)

- User ID, email, creation timestamp
- Email confirmation status
- User metadata (name, signup source, etc.)

### Survey Data (surveys table)

- User ID (linked to auth.users)
- Age, symptom duration, symptoms text
- Medical history, pain scale, severity
- Submission timestamp

### Feedback Data (feedback table)

- User ID (linked to auth.users)
- Symptoms, predictions, correct condition
- Helpfulness score, comments
- Submission timestamp

## 🔒 Security Features

- **Row Level Security (RLS)** - Users can only access their own data
- **Secure Authentication** - Via Supabase Auth
- **Data Validation** - Automatic user ID validation
- **Privacy Protection** - No personal data in survey responses

## 📚 Documentation

- `README.md` - This file (general app information)
- `DATABASE_SETUP.md` - Detailed database setup guide
- `env.example` - Environment variables template

**Note:** If Supabase is not configured, the app will work without authentication but won't save data persistently.

## Project Structure

```
CarePilot/
  app.py                  # Streamlit UI and flow
  detectors.py            # Zero-shot condition suggestion
  triage.py               # Rule-based triage logic
  data/resources.json     # Helpful links and resources
  storage/feedback.jsonl  # Anonymous feedback (app creates if missing)
  requirements.txt        # Python dependencies
  README.md               # This file
```

## Notes on Models and Training

This demo uses zero-shot classification via a pretrained NLI model (`facebook/bart-large-mnli`) to suggest likely conditions from symptom text. No training is required to get started. If you want to fine-tune or add your own models later, you can replace the logic in `detectors.py`.

## Privacy and Safety

- The app does not collect personally identifiable information by default.
- Feedback is stored locally in `storage/feedback.jsonl`. You can delete this file at any time.
- This tool is not a medical device and does not provide diagnoses. In an emergency, call your local emergency number immediately.

## Troubleshooting

- If model download is slow or blocked, try a VPN or pre-download Hugging Face models.
- If you see CUDA/torch errors, the app will still run on CPU.
