from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from admin_panel.models import (
    AcademicYear,
    Admission,
    AssignedPeriod,
    AutomationJob,
    Class,
    ClassGroup,
    CreatePeriod,
    FeeVoucher,
    NotificationQueue,
    Section,
    Student as FeeStudent,
    StudentBalance,
    Subject,
    TeacherFixture,
)
from student_profile.models import Student
from teacher_dashboard.models import Assignment, Attendance, LectureNote, Quiz, Teacher


class Command(BaseCommand):
    help = "Seed connected demo data for the AI Analytics dashboard."

    def handle(self, *args, **options):
        prefix = "AI Analytics Demo"
        today = timezone.localdate()

        year, _ = AcademicYear.objects.get_or_create(
            year="2026-2027",
            defaults={"is_active": True},
        )
        if not year.is_active:
            year.is_active = True
            year.save(update_fields=["is_active"])

        group, _ = ClassGroup.objects.get_or_create(group_name="AI Analytics Demo Group")
        klass, _ = Class.objects.get_or_create(
            class_name="AI Analytics Grade 8",
            defaults={"total_students": 10, "group": group},
        )
        klass.total_students = 10
        klass.group = group
        klass.save(update_fields=["total_students", "group"])

        section, _ = Section.objects.get_or_create(
            academic_year=year,
            class_fk=klass,
            section_name="A",
            defaults={"capacity": 40},
        )
        section.capacity = 40
        section.save(update_fields=["capacity"])

        subjects = self._seed_subjects(prefix, year, klass)
        teachers = self._seed_teachers(prefix, subjects)
        students = self._seed_students(prefix, year, klass, section)
        fee_students = self._seed_fee_students(prefix, klass, students, today)
        periods = self._seed_periods()
        assigned_periods = self._seed_assigned_periods(klass, section, subjects, teachers, periods)

        self._seed_attendance(students, teachers, klass, section, assigned_periods, today)
        self._seed_fee_vouchers(fee_students, today)
        self._seed_fixtures(klass, section, teachers, assigned_periods, today)
        self._seed_content(prefix, klass, section, subjects, teachers, today)
        self._seed_admissions(prefix, year, klass, section, today)
        self._seed_notifications(fee_students)

        AutomationJob.objects.update_or_create(
            job_type="AI_ANALYTICS_DEMO_FEE",
            defaults={
                "status": "COMPLETED",
                "processed_count": 10,
                "success_count": 9,
                "failed_count": 1,
            },
        )

        self.stdout.write(self.style.SUCCESS("SEEDED_AI_ANALYTICS_DEMO"))
        self.stdout.write(f"teachers={Teacher.objects.filter(name__startswith=prefix).count()}")
        self.stdout.write(f"students={Student.objects.filter(name__startswith=prefix).count()}")
        self.stdout.write(f"fee_students={FeeStudent.objects.filter(full_name__startswith=prefix).count()}")
        self.stdout.write(f"subjects={Subject.objects.filter(name__startswith=prefix).count()}")
        self.stdout.write(
            f"attendance_today={Attendance.objects.filter(date=today, student__name__startswith=prefix).count()}"
        )
        self.stdout.write(f"assigned_periods={len(assigned_periods)}")
        self.stdout.write(
            f"fixtures_today={TeacherFixture.objects.filter(fixture_date=today, class_fk=klass, section=section).count()}"
        )

    def _seed_subjects(self, prefix, year, klass):
        subjects = []
        subject_names = [
            ("Mathematics", "AIMATH"),
            ("Science", "AISCI"),
            ("English", "AIENG"),
            ("Computer", "AICS"),
            ("Urdu", "AIURD"),
        ]
        for index, (name, code) in enumerate(subject_names, start=1):
            subject, _ = Subject.objects.get_or_create(
                short_code=code,
                defaults={
                    "academic_year": year,
                    "class_fk": klass,
                    "name": f"{prefix} {name}",
                    "grading_type": "percentage",
                    "sort_order": index,
                },
            )
            subject.academic_year = year
            subject.class_fk = klass
            subject.name = f"{prefix} {name}"
            subject.grading_type = "percentage"
            subject.sort_order = index
            subject.save()
            subjects.append(subject)
        return subjects

    def _seed_teachers(self, prefix, subjects):
        teacher_group, _ = Group.objects.get_or_create(name="Teacher")
        teachers = []
        for index in range(1, 11):
            username = f"ai.demo.teacher{index:02d}"
            email = f"ai.demo.teacher{index:02d}@edupilot.test"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": "AI Demo",
                    "last_name": f"Teacher {index:02d}",
                    "is_active": True,
                },
            )
            if created:
                user.set_password("DemoTeacher123!")
            user.email = email
            user.is_active = True
            user.save()
            user.groups.add(teacher_group)

            teacher, _ = Teacher.objects.get_or_create(
                email=email,
                defaults={
                    "user": user,
                    "name": f"{prefix} Teacher {index:02d}",
                    "gender": "Male" if index % 2 else "Female",
                    "date_of_birth": date(1985, 1, min(index, 28)),
                    "qualification": "Masters",
                    "experience": 3 + index,
                    "faculty_group": "Senior Section",
                    "department": "AI Analytics Demo",
                    "status": "active",
                },
            )
            teacher.user = user
            teacher.name = f"{prefix} Teacher {index:02d}"
            teacher.status = "active"
            teacher.department = "AI Analytics Demo"
            teacher.save()
            teacher.subjects.set([subjects[(index - 1) % len(subjects)]])
            teachers.append(teacher)
        return teachers

    def _seed_students(self, prefix, year, klass, section):
        student_group, _ = Group.objects.get_or_create(name="Student")
        students = []
        for index in range(1, 11):
            username = f"ai.demo.student{index:02d}"
            email = f"ai.demo.student{index:02d}@edupilot.test"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": "AI Demo",
                    "last_name": f"Student {index:02d}",
                    "is_active": True,
                },
            )
            if created:
                user.set_password("DemoStudent123!")
            user.email = email
            user.is_active = True
            user.save()
            user.groups.add(student_group)

            student, _ = Student.objects.get_or_create(
                student_id=f"AIDEMO{index:03d}",
                defaults={
                    "user": user,
                    "academic_year": year,
                    "name": f"{prefix} Student {index:02d}",
                    "father_name": f"Demo Father {index:02d}",
                    "mother_name": f"Demo Mother {index:02d}",
                    "class_fk": klass,
                    "section": section,
                    "roll_no": f"AI-{index:02d}",
                    "gender": "Male" if index % 2 else "Female",
                    "date_of_birth": date(2012, 1, min(index, 28)),
                    "email": email,
                },
            )
            student.user = user
            student.academic_year = year
            student.name = f"{prefix} Student {index:02d}"
            student.class_fk = klass
            student.section = section
            student.roll_no = f"AI-{index:02d}"
            student.email = email
            student.save()
            students.append(student)
        return students

    def _seed_fee_students(self, prefix, klass, portal_students, today):
        fee_students = []
        for index, portal_student in enumerate(portal_students, start=1):
            fee_student, _ = FeeStudent.objects.get_or_create(
                admission_number=f"AIDEMO-FEE-{index:03d}",
                defaults={
                    "full_name": portal_student.name,
                    "current_class": klass.class_name,
                    "is_active": True,
                    "campus": "AI Analytics Demo Campus",
                    "student_id": portal_student.student_id,
                },
            )
            fee_student.full_name = portal_student.name
            fee_student.current_class = klass.class_name
            fee_student.is_active = True
            fee_student.campus = "AI Analytics Demo Campus"
            fee_student.student_id = portal_student.student_id
            fee_student.save()
            fee_students.append(fee_student)
        return fee_students

    def _seed_periods(self):
        periods = []
        for index in range(1, 6):
            period = CreatePeriod.objects.filter(day="Thursday", period_name=f"AI Demo Period {index}").first()
            if not period:
                period = CreatePeriod.objects.create(
                    day="Thursday",
                    period_name=f"AI Demo Period {index}",
                    start_time=time(8 + index, 0),
                    end_time=time(8 + index, 45),
                )
            periods.append(period)
        return periods

    def _seed_assigned_periods(self, klass, section, subjects, teachers, periods):
        assigned_periods = []
        for index, teacher in enumerate(teachers):
            subject = subjects[index % len(subjects)]
            period = periods[index % len(periods)]
            assigned, _ = AssignedPeriod.objects.get_or_create(
                class_fk=klass,
                section=section,
                subject=subject,
                day="Thursday",
                period=period,
                teacher=teacher,
                defaults={"is_bypass": True},
            )
            assigned.is_bypass = True
            assigned.save(update_fields=["is_bypass"])
            assigned_periods.append(assigned)
        return assigned_periods

    def _seed_attendance(self, students, teachers, klass, section, assigned_periods, today):
        for index, student in enumerate(students):
            status = "present" if index < 7 else ("absent" if index < 9 else "leave")
            Attendance.objects.update_or_create(
                student=student,
                date=today,
                period=assigned_periods[index % len(assigned_periods)],
                defaults={
                    "status": status,
                    "class_fk": klass,
                    "section": section,
                    "marked_by": teachers[index % len(teachers)],
                },
            )

        for offset in range(1, 7):
            day = today - timedelta(days=offset)
            for index, student in enumerate(students):
                Attendance.objects.update_or_create(
                    student=student,
                    date=day,
                    period=assigned_periods[index % len(assigned_periods)],
                    defaults={
                        "status": "present" if (index + offset) % 5 else "absent",
                        "class_fk": klass,
                        "section": section,
                        "marked_by": teachers[(index + offset) % len(teachers)],
                    },
                )

    def _seed_fee_vouchers(self, students, today):
        for index, student in enumerate(students):
            balance, _ = StudentBalance.objects.get_or_create(student=student)
            balance.outstanding_amount = Decimal(str(balance.outstanding_amount or 0))
            balance.save(update_fields=["outstanding_amount"])
            FeeVoucher.objects.update_or_create(
                student=student,
                month=today.strftime("%B"),
                year=today.year,
                defaults={
                    "voucher_no": f"AIDEMO-{student.student_id}-{today.strftime('%B')}-{today.year}",
                    "issue_date": today.replace(day=1),
                    "due_date": today + timedelta(days=10),
                    "gross_amount": Decimal("10000.00"),
                    "discount": Decimal("0.00"),
                    "fine": Decimal("0.00"),
                    "previous_due": Decimal("0.00"),
                    "net_amount": Decimal("10000.00"),
                    "status": "PAID" if index < 6 else "UNPAID",
                },
            )

    def _seed_fixtures(self, klass, section, teachers, assigned_periods, today):
        for index, assigned in enumerate(assigned_periods[:3]):
            TeacherFixture.objects.update_or_create(
                fixture_date=today,
                assigned_period=assigned,
                defaults={
                    "class_fk": klass,
                    "section": section,
                    "subject": assigned.subject,
                    "period": assigned.period,
                    "absent_teacher": assigned.teacher,
                    "substitute_teacher": teachers[(index + 4) % len(teachers)],
                    "day": "Thursday",
                    "source": "auto_absence" if index < 2 else "manual",
                    "automation_status": "assigned",
                    "fixture_status": "assigned",
                    "assignment_mode": "auto" if index < 2 else "manual",
                    "selection_score": 80 - index,
                    "selection_reason": "AI Analytics demo substitute selected by workload/subject match",
                    "candidate_count": 4,
                },
            )

    def _seed_content(self, prefix, klass, section, subjects, teachers, today):
        for index, subject in enumerate(subjects):
            Assignment.objects.update_or_create(
                teacher=teachers[index],
                class_fk=klass,
                section=section,
                subject=subject,
                title=f"{prefix} Assignment {index + 1}",
                defaults={
                    "description": "Demo assignment for AI Analytics testing",
                    "file": "assignments/demo.txt",
                    "due_date": today + timedelta(days=index + 1),
                },
            )
            Quiz.objects.update_or_create(
                teacher=teachers[index],
                class_fk=klass,
                section=section,
                subject=subject,
                title=f"{prefix} Quiz {index + 1}",
                defaults={
                    "file": "quizzes/demo.txt",
                    "due_date": today + timedelta(days=index + 2),
                },
            )
            LectureNote.objects.update_or_create(
                teacher=teachers[index],
                class_fk=klass,
                section=section,
                subject=subject,
                title=f"{prefix} Note {index + 1}",
                defaults={
                    "description": "Demo lecture note for AI Analytics testing",
                    "file": "lecture_notes/demo.txt",
                },
            )

    def _seed_admissions(self, prefix, year, klass, section, today):
        for index in range(1, 4):
            admission = Admission.objects.filter(ref_no=f"AIDEMO-ADM-{index:02d}").first()
            defaults = {
                "campus": "AI Analytics Demo Campus",
                "academic_year": year,
                "section": section,
                "branch": "Main",
                "name": f"{prefix} Admission {index:02d}",
                "class_fk": klass,
                "dob": date(2012, 2, index),
                "gender": "male",
                "email": f"ai.demo.admission{index:02d}@edupilot.test",
                "contact": f"030000000{index}",
                "address": "Demo address",
                "admission_date": today - timedelta(days=index),
                "father_name": f"Demo Admission Father {index}",
                "mother_name": f"Demo Admission Mother {index}",
                "admission_status": "pending" if index == 1 else "approved",
            }
            if admission:
                for field, value in defaults.items():
                    setattr(admission, field, value)
                admission.save()
            else:
                Admission.objects.create(ref_no=f"AIDEMO-ADM-{index:02d}", **defaults)

    def _seed_notifications(self, students):
        for index, student in enumerate(students[:3], start=1):
            NotificationQueue.objects.update_or_create(
                student=student,
                notification_type="EMAIL",
                content=f"AI Analytics demo notification {index}",
                defaults={"status": "FAILED" if index == 1 else "SENT"},
            )
