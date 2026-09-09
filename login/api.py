from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from student_profile.models import Student


User = get_user_model()


def error_response(code, message, http_status, fields=None):
    return Response(
        {"error": {"code": code, "message": message, "fields": fields or {}}},
        status=http_status,
    )


def student_payload(student, request=None):
    user = student.user
    photo_url = None
    if student.photo:
        photo_url = student.photo.url
        if request is not None:
            photo_url = request.build_absolute_uri(photo_url)
    return {
        "id": user.id,
        "student_id": student.student_id,
        "login_id": user.username,
        "name": student.name,
        "email": student.email or user.email,
        "role": "student",
        "photo_url": photo_url,
        "class": (
            {"id": student.class_fk_id, "name": student.class_fk.class_name}
            if student.class_fk_id else None
        ),
        "section": (
            {"id": student.section_id, "name": student.section.section_name}
            if student.section_id else None
        ),
    }


class StudentLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(trim_whitespace=True)
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class StudentLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=StudentLoginSerializer, responses={200: OpenApiResponse(description="Student JWT session created")}, tags=["Student authentication"])
    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", "Please provide a login ID/email and password.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        identifier = serializer.validated_data["identifier"]
        password = serializer.validated_data["password"]
        user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).order_by("id").first()
        if user is None or not user.check_password(password):
            return error_response("invalid_credentials", "Invalid login ID/email or password.", status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return error_response("account_inactive", "Your account is inactive. Contact admin.", status.HTTP_403_FORBIDDEN)
        authenticated_user = authenticate(request=request, username=user.username, password=password)
        if authenticated_user is None:
            return error_response("invalid_credentials", "Invalid login ID/email or password.", status.HTTP_401_UNAUTHORIZED)
        if not authenticated_user.groups.filter(name__iexact="Student").exists():
            return error_response("role_not_allowed", "This account cannot access the Student app.", status.HTTP_403_FORBIDDEN)
        try:
            student = Student.objects.select_related("class_fk", "section").get(user=authenticated_user)
        except Student.DoesNotExist:
            return error_response("student_profile_missing", "Student profile is missing. Contact admin.", status.HTTP_403_FORBIDDEN)

        authenticated_user.last_login = timezone.now()
        authenticated_user.save(update_fields=["last_login"])
        refresh = RefreshToken.for_user(authenticated_user)
        refresh["role"] = "student"
        refresh["student_id"] = student.student_id
        return Response({"access": str(refresh.access_token), "refresh": str(refresh), "user": student_payload(student, request)})


class StudentMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="StudentMeResponse",
                fields={"user": serializers.DictField()},
            )
        },
        tags=["Student authentication"],
    )
    def get(self, request):
        if not request.user.is_active:
            return error_response("account_inactive", "Your account is inactive. Contact admin.", status.HTTP_403_FORBIDDEN)
        if not request.user.groups.filter(name__iexact="Student").exists():
            return error_response("role_not_allowed", "This account cannot access the Student app.", status.HTTP_403_FORBIDDEN)
        try:
            student = Student.objects.select_related("class_fk", "section").get(user=request.user)
        except Student.DoesNotExist:
            return error_response("student_profile_missing", "Student profile is missing. Contact admin.", status.HTTP_403_FORBIDDEN)
        return Response({"user": student_payload(student, request)})


class StudentTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Student authentication"])
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code >= 400:
            return error_response("token_invalid", "The session has expired. Please log in again.", status.HTTP_401_UNAUTHORIZED)
        return response

    def handle_exception(self, exc):
        if isinstance(exc, TokenError):
            return error_response("token_invalid", "The session has expired. Please log in again.", status.HTTP_401_UNAUTHORIZED)
        response = super().handle_exception(exc)
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            return error_response("token_invalid", "The session has expired. Please log in again.", status.HTTP_401_UNAUTHORIZED)
        return response


class StudentLogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=LogoutSerializer, responses={204: OpenApiResponse(description="Session revoked")}, tags=["Student authentication"])
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", "A refresh token is required.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return error_response("token_invalid", "The session is already invalid or expired.", status.HTTP_401_UNAUTHORIZED)
        return Response(status=status.HTTP_204_NO_CONTENT)
