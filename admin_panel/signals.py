from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import Admission, Class, Section


# =============================== SECTION ASSIGNMENT ===============================
@receiver(post_save, sender=Admission)
def assign_section(sender, instance, created, **kwargs):
    """
    Automatically assign a Section to a new Admission if capacity allows.
    """
    if created and instance.section is None:
        sections = Section.objects.filter(
            academic_year=instance.academic_year,
            class_fk=instance.class_fk
        ).order_by('section_name')

        for section in sections:
            assigned_count = Admission.objects.filter(section=section).count()
            if assigned_count < section.capacity:  # changed: was section_strength → now capacity
                instance.section = section
                instance.save(update_fields=['section'])
                break


# =============================== USER GROUP ASSIGNMENT ===============================
@receiver(post_save, sender=User)
def assign_default_group(sender, instance, created, **kwargs):
    """
    Automatically assign a default Group (role) to newly created users.
    You can modify this logic as needed.
    """
    if created:
        # Example: Assign every new user to 'Student' group by default.
        # You can customize based on username, email domain, etc.
        default_group, _ = Group.objects.get_or_create(name='Student')
        instance.groups.add(default_group)


# admin_panel/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from .models import UserRole

@receiver(post_save, sender=User)
def assign_permissions_based_on_role(sender, instance, created, **kwargs):
    """
    Jab bhi naya user create hota hai, uska role check hota hai aur
    us role ke name ke hisaab se permissions assign hoti hain.
    """
    if not created:
        return

    try:
        user_role = UserRole.objects.get(user=instance)
        role = user_role.role
        if not role:
            return

        role_name = role.name.lower()

        # 🧑‍🏫 TEACHER → sab teacher_ prefix permissions
        if role_name == "teacher":
            permissions = Permission.objects.filter(codename__startswith="teacher_")
            role.permissions.set(permissions)

        # 🎓 STUDENT → sab student_ prefix permissions
        elif role_name == "student":
            permissions = Permission.objects.filter(codename__startswith="student_")
            role.permissions.set(permissions)

        # 👨‍👩‍👧‍👦 PARENT → sab parent_ prefix permissions
        elif role_name == "parent":
            permissions = Permission.objects.filter(codename__startswith="parent_")
            role.permissions.set(permissions)

        # 🧑‍💼 ADMIN → sabhi permissions
        elif role_name == "admin":
            role.permissions.set(Permission.objects.all())

        # ⚙️ CUSTOM ROLE → manually admin panel me assign hoga
        else:
            pass

        # ✅ user ko uske role group me daal do
        instance.groups.add(role)
        instance.save()

    except UserRole.DoesNotExist:
        pass

# ==========================================================================================
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group

@receiver(post_save, sender=User)
def assign_group_on_creation(sender, instance, created, **kwargs):
    """
    Automatically assign users to groups based on their role or username.
    """
    if not created:
        return

    username = instance.username.lower()

    # 🔹 Superuser → Admin group
    if instance.is_superuser:
        group, _ = Group.objects.get_or_create(name="Admin")
        instance.groups.add(group)
        print(f"✅ Superuser '{instance.username}' added to Admin group")

    # 🔹 Normal users → assign based on name
    elif "teacher" in username:
        group, _ = Group.objects.get_or_create(name="Teacher")
        instance.groups.add(group)
        print(f"👨‍🏫 {instance.username} added to Teacher group")

    elif "student" in username:
        group, _ = Group.objects.get_or_create(name="Student")
        instance.groups.add(group)
        print(f"🎓 {instance.username} added to Student group")

    elif "parent" in username:
        group, _ = Group.objects.get_or_create(name="Parent")
        instance.groups.add(group)
        print(f"👨‍👩‍👧 {instance.username} added to Parent group")


# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth.models import User
# from .models import UserRole, Role, Permission


# @receiver(post_save, sender=User)
# def assign_default_permissions(sender, instance, created, **kwargs):
#     """
#     Jab bhi koi naya user create hota hai,
#     uska role check hota hai aur uss role ke mutabiq
#     default permissions assign kar di jaati hain.
#     """
#     if not created:
#         return  # sirf naye users ke liye chale

#     try:
#         user_role = UserRole.objects.get(user=instance)
#         role = user_role.role

#         if not role:
#             return

#         role_name = role.name.lower()

#         # --- AUTO PERMISSION LOGIC ---
#         if role_name == "teacher":
#             # Teacher dashboard ke tamam permissions assign karo
#             teacher_perms = Permission.objects.filter(code__startswith="teacher_")
#             role.permissions.set(teacher_perms)

#         elif role_name == "student":
#             # Student dashboard ke tamam permissions assign karo
#             student_perms = Permission.objects.filter(code__startswith="student_")
#             role.permissions.set(student_perms)

#         elif role_name == "parent":
#             # Parent dashboard ke tamam permissions assign karo
#             parent_perms = Permission.objects.filter(code__startswith="parent_")
#             role.permissions.set(parent_perms)

#         elif role_name == "admin":
#             # Admin ko sab permissions milen
#             all_perms = Permission.objects.all()
#             role.permissions.set(all_perms)

#         else:
#             # Custom roles ke liye kuch nahi karna
#             # Admin manually permission assign karega create-role form se
#             pass

#         role.save()

#     except UserRole.DoesNotExist:
#         pass



# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Admission, Class, Section

# @receiver(post_save, sender=Admission)
# def assign_section(sender, instance, created, **kwargs):
#     if created and instance.section is None:
#         sections = Section.objects.filter(
#             academic_year=instance.academic_year,
#             class_fk=instance.class_fk
#         ).order_by('section_name')

#         for section in sections:
#             assigned_count = Admission.objects.filter(section=section).count()
#             if assigned_count < section.section_strength:
#                 instance.section = section
#                 instance.save()
#                 break



# # =================================user role permission=========================
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth.models import User
# from .models import UserRole

# @receiver(post_save, sender=User)
# def create_or_update_user_role(sender, instance, created, **kwargs):
#     # get_or_create prevents duplicate UserRole
#     role, _ = UserRole.objects.get_or_create(user=instance)
#     role.save()

