# # student_profile/email_utils.py
# # =====================================
# # Student ko welcome email bhejo
# # jisme login credentials hote hain
# # =====================================

# from django.core.mail import send_mail
# from django.conf import settings
# from django.template.loader import render_to_string
# from django.utils.html import strip_tags


# def send_student_credentials_email(student, raw_password):
#     """
#     Naya student account banne par email bhejo.

#     Parameters:
#         student     : Student model instance
#         raw_password: Plain text password (hashing se pehle wala)

#     Usage (admin view mein):
#         from student_profile.email_utils import send_student_credentials_email
#         send_student_credentials_email(student_obj, "plain_password_here")
#     """

#     if not student.email:
#         return False, "Student ka email address nahi hai."

#     subject = f"Welcome to EduPilot — Your Login Credentials"

#     # School name settings se lo, fallback hai
#     school_name = getattr(settings, 'SCHOOL_NAME', 'EduPilot School')
#     login_url   = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000') + '/student/login/'

#     # Plain text message
#     message = f"""
# Assalam-o-Alaikum {student.name},

# Welcome to {school_name}!

# Aapka student account successfully create ho gaya hai.
# Neeche aapki login details hain — inhe safe rakhein.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━
#   USERNAME : {student.user.username}
#   PASSWORD : {raw_password}
# ━━━━━━━━━━━━━━━━━━━━━━━━━━

# Login karne ke liye yahan jayein:
# {login_url}

# Login karne ke baad apna password zaroor change karein.

# Class    : {student.class_fk.class_name if student.class_fk else 'Not assigned'}
# Roll No  : {student.roll_no if hasattr(student, 'roll_no') else 'N/A'}

# Regards,
# {school_name} Administration
# """

#     try:
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[student.email],
#             fail_silently=False,
#         )
#         return True, "Email successfully send ho gayi."
#     except Exception as e:
#         return False, f"Email send nahi hui: {str(e)}"


# def send_bulk_credentials_email(students_with_passwords):
#     """
#     Multiple students ko ek saath email bhejo.

#     Parameters:
#         students_with_passwords: list of tuples — [(student, raw_password), ...]

#     Returns:
#         dict with success_count, failed_count, errors
#     """
#     success_count = 0
#     failed_count  = 0
#     errors        = []

#     for student, raw_password in students_with_passwords:
#         ok, msg = send_student_credentials_email(student, raw_password)
#         if ok:
#             success_count += 1
#         else:
#             failed_count += 1
#             errors.append(f"{student.name}: {msg}")

#     return {
#         'success_count': success_count,
#         'failed_count':  failed_count,
#         'errors':        errors,
#     }


# def send_password_reset_email(student, new_password):
#     """
#     Admin ne password reset kiya — student ko naya password email karo.
#     """
#     if not student.email:
#         return False, "Student ka email address nahi hai."

#     school_name = getattr(settings, 'SCHOOL_NAME', 'EduPilot School')
#     login_url   = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000') + '/student/login/'

#     subject = f"{school_name} — Aapka Password Reset Ho Gaya"

#     message = f"""
# Assalam-o-Alaikum {student.name},

# Aapka password admin ne reset kar diya hai.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━
#   USERNAME : {student.user.username}
#   NEW PASSWORD : {new_password}
# ━━━━━━━━━━━━━━━━━━━━━━━━━━

# Login karne ke liye:
# {login_url}

# Agar aapne password reset request nahi ki thi to
# foran school administration se rabta karein.

# Regards,
# {school_name} Administration
# """

#     try:
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[student.email],
#             fail_silently=False,
#         )
#         return True, "Password reset email send ho gayi."
#     except Exception as e:
#         return False, f"Email send nahi hui: {str(e)}"






from django.core.mail import send_mail
from django.conf import settings


def send_student_credentials_email(student, password):

    try:
        subject = "Student Account Created"

        message = f"""
Hello {student.name},

Your student portal account has been created successfully.

Login Details:

Username: {student.user.username}
Password: {password}

Login URL:
http://127.0.0.1:8000/

Thanks
School Management System
"""

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [student.email],
            fail_silently=False,
        )

        print("EMAIL SENT SUCCESSFULLY")

        return True, "Email sent successfully"

    except Exception as e:

        print("EMAIL ERROR:", str(e))

        return False, str(e)


def send_password_reset_email(student, password):

    try:

        subject = "Student Password Reset"

        message = f"""
Hello {student.name},

Your password has been reset.

New Login Details:

Username: {student.user.username}
Password: {password}

Login URL:
http://127.0.0.1:8000/

Thanks
School Management System
"""

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [student.email],
            fail_silently=False,
        )

        print("PASSWORD RESET EMAIL SENT")

        return True, "Password reset email sent"

    except Exception as e:

        print("RESET EMAIL ERROR:", str(e))

        return False, str(e)