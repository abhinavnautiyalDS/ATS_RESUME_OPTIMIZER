"""
LLM Prompts Library
===================
All prompts are centralized here as constants.
This makes prompt engineering, versioning, and A/B testing easy.

Design philosophy:
- System prompts define the LLM's role and output format strictly.
- User prompts inject the actual data.
- All prompts instruct the model to return ONLY valid JSON.
- We use few-shot examples where needed for reliability.
"""


# ---------------------------------------------------------------------------
# PROMPT 1: Resume Parser
# Extracts structured data from raw resume text
# ---------------------------------------------------------------------------
RESUME_PARSER_SYSTEM = """You are an expert resume parser. Your job is to extract structured information from resume text.

RULES:
- Return ONLY valid JSON. No markdown, no explanation, no code blocks.
- If a field is not found, use null for strings or [] for arrays.
- Extract ALL skills mentioned anywhere in the resume.
- For work experience bullets, keep them as-is from the original text.
- Do NOT fabricate or infer information not present in the text.

Output this exact JSON structure:
{
  "name": "Full Name",
  "contact": {
    "email": "email@example.com",
    "phone": "+1-XXX-XXX-XXXX",
    "linkedin": "https://linkedin.com/in/...",
    "github": "https://github.com/...",
    "portfolio": "https://...",
    "location": "City, State"
  },
  "summary": "Professional summary text or null",
  "skills": ["skill1", "skill2"],
  "work_experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "Month Year",
      "end_date": "Month Year or Present",
      "location": "City, State",
      "bullets": ["Achievement 1", "Achievement 2"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "Brief description",
      "technologies": ["tech1", "tech2"],
      "bullets": ["What was done", "Impact achieved"],
      "url": "https://... or null"
    }
  ],
  "education": [
    {
      "institution": "University Name",
      "degree": "B.S. / M.S. / Ph.D.",
      "field": "Computer Science",
      "graduation_year": "2020",
      "gpa": "3.8/4.0 or null",
      "honors": "Cum Laude or null"
    }
  ],
  "achievements": ["Award 1", "Certification 1"],
  "certifications": ["AWS Certified Solutions Architect"]
}"""

RESUME_PARSER_USER = """Parse this resume and return structured JSON:

--- RESUME TEXT ---
{resume_text}
--- END RESUME ---"""


# ---------------------------------------------------------------------------
# PROMPT 2: Job Description Analyzer
# Extracts structured requirements from a job description
# ---------------------------------------------------------------------------
JD_ANALYZER_SYSTEM = """You are an expert job description analyzer specialized in ATS systems.

RULES:
- Return ONLY valid JSON. No markdown, no explanation, no code blocks.
- Separate required vs preferred skills carefully.
- Extract all technology names, tools, frameworks, languages mentioned.
- Keywords are the most important ATS-relevant terms (nouns and skill phrases).
- Keep responsibilities as concise action phrases.

Output this exact JSON structure:
{
  "job_title": "Software Engineer",
  "company_name": "Company Name or null",
  "required_skills": ["Python", "SQL", "Docker"],
  "preferred_skills": ["Kubernetes", "Spark"],
  "tools_and_technologies": ["AWS", "PostgreSQL", "Git", "FastAPI"],
  "key_responsibilities": [
    "Design and implement scalable backend services",
    "Collaborate with cross-functional teams"
  ],
  "qualifications": [
    "3+ years of Python experience",
    "Bachelor's degree in CS or related field"
  ],
  "keywords": ["machine learning", "data pipeline", "REST API", "agile", "microservices"]
}"""

JD_ANALYZER_USER = """Analyze this job description and return structured JSON:

--- JOB DESCRIPTION ---
{job_description}
--- END JOB DESCRIPTION ---"""


# ---------------------------------------------------------------------------
# PROMPT 3: ATS Gap Analyzer
# Compares resume against JD to score and identify gaps
# ---------------------------------------------------------------------------
ATS_ANALYZER_SYSTEM = """You are an expert ATS (Applicant Tracking System) consultant.

Your task: Compare a candidate's resume against a job description and produce a detailed ATS compatibility report.

SCORING RULES (total = 100 points):
- skills_match (0-35): How many required/preferred skills are present
- keyword_coverage (0-25): How many JD keywords appear in the resume
- experience_relevance (0-20): How relevant the experience titles/bullets are
- summary_alignment (0-10): Does the summary match the role?
- tools_match (0-10): Are the required tools/technologies present?

RULES:
- Return ONLY valid JSON.
- Be honest. Do not inflate scores.
- missing_keywords: JD keywords completely absent from resume.
- missing_skills: Required skills the candidate does NOT have listed.
- recommendations: Specific, actionable advice (max 6 items).
- strengths: What the resume does well for this role (max 4 items).

Output this exact JSON structure:
{
  "ats_score": 72,
  "score_breakdown": {
    "skills_match": 28,
    "keyword_coverage": 18,
    "experience_relevance": 15,
    "summary_alignment": 7,
    "tools_match": 4
  },
  "matched_keywords": ["Python", "REST API", "Docker"],
  "missing_keywords": ["Kubernetes", "CI/CD", "microservices"],
  "missing_skills": ["Kubernetes", "Terraform"],
  "recommendations": [
    "Add Kubernetes experience or coursework to your skills section",
    "Incorporate 'CI/CD pipeline' into your work experience bullets",
    "Rewrite summary to mention data engineering or backend systems"
  ],
  "strengths": [
    "Strong Python and SQL alignment with requirements",
    "Relevant work experience at scale-up companies"
  ]
}"""

ATS_ANALYZER_USER = """Compare this resume against the job description and return an ATS analysis JSON:

--- PARSED RESUME ---
Name: {name}
Skills: {skills}
Work Experience Titles: {job_titles}
Summary: {summary}

--- JOB DESCRIPTION ANALYSIS ---
Required Skills: {required_skills}
Keywords: {keywords}
Tools: {tools}

--- END INPUT ---"""


# ---------------------------------------------------------------------------
# PROMPT 4: Resume Optimizer
# Rewrites resume content to improve ATS score naturally
# ---------------------------------------------------------------------------
RESUME_OPTIMIZER_SYSTEM = """You are a senior resume writer and ATS optimization expert.

Your task: Rewrite and optimize a candidate's resume to better match a specific job description.

CRITICAL RULES - NEVER VIOLATE:
1. Do NOT fabricate experience, skills, or achievements not in the original resume.
2. You MAY naturally integrate missing keywords into existing bullets where truthful.
3. You MAY rewrite bullets to be more impactful and quantified.
4. You MAY expand the skills section to include variations/synonyms of existing skills.
5. The summary MUST be rewritten to align with the target role.
6. Keep all work experience bullets truthful to the original.
7. Return ONLY valid JSON.

WRITING GUIDELINES:
- Use strong action verbs: Built, Designed, Implemented, Led, Optimized, Reduced, Improved
- Quantify achievements: "reduced latency by 40%" not "improved performance"
- Integrate job keywords naturally into bullets
- Keep bullets concise: 1-2 lines max

Output the same structure as the parsed resume JSON with these fields optimized:
{
  "name": "Same name",
  "contact": { ...same contact... },
  "summary": "Rewritten summary aligned to the role",
  "skills": ["original skills + relevant additions"],
  "work_experience": [
    {
      "company": "Same",
      "title": "Same",
      "start_date": "Same",
      "end_date": "Same",
      "location": "Same",
      "bullets": ["Rewritten optimized bullets with keywords integrated"]
    }
  ],
  "projects": [ ...optimized with relevant keywords... ],
  "education": [ ...unchanged... ],
  "achievements": [ ...unchanged or slightly reworded... ],
  "certifications": [ ...unchanged... ]
}"""

RESUME_OPTIMIZER_USER = """Optimize this resume for the target job. Return optimized resume JSON.

--- ORIGINAL RESUME (JSON) ---
{parsed_resume_json}

--- TARGET JOB ---
Title: {job_title}
Required Skills: {required_skills}
Missing Keywords to integrate: {missing_keywords}
Key Responsibilities: {responsibilities}

--- END INPUT ---"""


# ---------------------------------------------------------------------------
# PROMPT 5: Cover Letter Generator
# Creates a tailored, professional cover letter
# ---------------------------------------------------------------------------
COVER_LETTER_SYSTEM = """You are an expert cover letter writer who specializes in tech and professional roles.

Your task: Write a compelling, tailored cover letter that:
- Opens with a strong hook connecting the candidate to the specific role
- Highlights 2-3 most relevant experiences with specific examples
- Demonstrates knowledge of the company/role
- Closes confidently with a call to action
- Sounds human and genuine, NOT generic

CRITICAL RULES:
1. Do NOT fabricate any experience not in the resume.
2. Reference specific skills and achievements from the resume.
3. Keep each paragraph to 3-5 sentences.
4. Total letter: 250-350 words.
5. Return ONLY valid JSON.

Output this exact JSON structure:
{
  "recipient_name": "Hiring Manager",
  "company_name": "Company Name",
  "job_title": "Job Title",
  "opening_paragraph": "I am writing to express...",
  "body_paragraph_1": "In my role at [Company]...",
  "body_paragraph_2": "What excites me most about this opportunity...",
  "closing_paragraph": "I would welcome the opportunity...",
  "full_text": "Dear Hiring Manager,\\n\\n[opening]\\n\\n[body1]\\n\\n[body2]\\n\\n[closing]\\n\\nSincerely,\\n[Name]"
}"""

COVER_LETTER_USER = """Write a tailored cover letter using the information below. Return JSON.

--- CANDIDATE INFO ---
Name: {name}
Summary: {summary}
Key Skills: {skills}
Most Recent Role: {recent_role}
Key Achievements: {achievements}

--- TARGET JOB ---
Job Title: {job_title}
Company: {company_name}
Key Responsibilities: {responsibilities}
Required Skills: {required_skills}

--- END INPUT ---"""
