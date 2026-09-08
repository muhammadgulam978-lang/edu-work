# Grade Predictor — Teacher Portal (EduPilot)

Ye app aapke shared spec ke **Section 12 (Early Risk Detection)** aur
**Section 13 (Teacher Dashboard)** ko implement karta hai — Teacher Dashboard →
Analytics → Grade Predictor. Baaki screens (student side, What-If simulator,
Target Grade Planner) isi models/services par easily build ho sakte hain —
agli iteration mein add kar sakte hain.

## Files
```
grade_predictor/
  models.py     -> GradePredictorConfig, StudentGradePrediction, PredictionHistory,
                    GradeRiskIntervention, PredictionAlert
  services.py   -> prediction engine (weighted score + trend + confidence + risk + probability)
  views.py      -> teacher_grade_predictor_dashboard, student_prediction_detail, create_intervention
  urls.py       -> /teacher/grade-predictor/...
  admin.py
  templates/grade_predictor/teacher_dashboard.html   -> matches your Fee Vouchers page theme
  templates/grade_predictor/prediction_detail.html
  static/grade_predictor/css/grade_predictor.css     -> teal-green / mint theme variables
```

## Ab real EduPilot models se wired hai

- `StudentGradePrediction.subject` → `admin_panel.Subject`
- `StudentGradePrediction.class_room` → `admin_panel.Class`
- `StudentGradePrediction.student` → `student_profile.Student`
- `services.get_assessment_records()` → ab `exam_system.CentralizedResult`
  se real data khींchta hai: `CentralizedResult → AnswerSheet →
  ExamSchedule → (subject, ExamPlan.exam_type)`. `ExamPlan.exam_type`
  (WEEKLY/MONTHLY/MIDTERM/FINAL) automatically weightage category
  (quiz/class_test/midterm/final_exam) mein map ho jata hai.
- Grading scale ab aapke `CentralizedResult.GRADE_CHOICES` (A+, A, B, C,
  D, F) se exactly match karta hai.

**1 cheez jo verify karni hai:** `views.py` → `_teacher_class_rooms()`
mein maine `admin_panel.AssignedPeriod` ko `teacher` aur `class_fk` field
names se guess kiya hai (waisa hi naming pattern jaisa `QuestionBank` mein
hai). Agar aapke `AssignedPeriod` model mein field names alag hain, to
sirf `.filter(teacher=teacher)` aur `.values_list("class_fk_id", ...)`
lines adjust karni hongi — baaki sab kuch real models se already wired
hai.

**Templates → `{% extends "teacher_dashboard/base.html" %}`**
   Apne existing base template ka naam/path daalo (wahi jo Fee Vouchers
   page use karta hai) taake header + sidebar automatically inherit ho
   jayein — maine sirf `content` block likha hai, poora page duplicate
   nahi kiya.

## Setup steps

1. App ko project mein copy karo aur `INSTALLED_APPS` mein add karo:
   ```python
   INSTALLED_APPS = [
       ...,
       "grade_predictor",
   ]
   ```
2. Main `urls.py` mein include karo:
   ```python
   path("teacher/", include("grade_predictor.urls")),
   ```
3. `python manage.py makemigrations grade_predictor && python manage.py migrate`
4. Admin panel se ek `GradePredictorConfig` row bana lo (grading scale,
   weightages, risk thresholds) — nahi banaoge to sensible defaults use
   hongi.
5. Predictions calculate/refresh karne ke liye, jab bhi naya assessment
   result save ho, ye call karo (signal ya management command se):
   ```python
   from grade_predictor.services import save_prediction
   save_prediction(student, subject, class_room)
   ```

## Prediction model (spec section 19)

V1 deliberately statistical hai, deep-learning nahi (jaisa spec mein
recommend kiya gaya hai):
- **Current score** = weighted average across assessment categories
  (weights configurable in admin)
- **Trend/projection** = simple linear regression over the chronological
  score sequence
- **Final prediction** = 60% current weighted score + 40% trend
  projection (blend so one outlier assessment doesn't swing it)
- **Confidence** = based on how many assessments are recorded vs.
  configured minimum
- **Grade probability spread** = narrows automatically as confidence
  increases

Jab enough historical data ho jaye (spec ke mutabiq), `_trend_projection`
aur `_grade_probability` ko gradient-boosting model se replace kiya ja
sakta hai — baaki pipeline (explain → risk → dashboard) same rahega.
