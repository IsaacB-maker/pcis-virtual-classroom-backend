
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from .models import Student, StudentRegistrationCode


User = get_user_model()


class StudentRegistrationSerializer(serializers.Serializer):
    admission_number = serializers.CharField(max_length=50)
    registration_code = serializers.CharField(
        write_only=True,
        trim_whitespace=True,
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_admission_number(self, value):
        value = value.strip()

        try:
            student = Student.objects.get(
                admission_number__iexact=value
            )
        except Student.DoesNotExist:
            raise serializers.ValidationError(
                "No student record was found for this admission number. "
                "Please contact the school administration."
            )

        if (
            student.registration_status
            == Student.RegistrationStatus.REGISTERED
        ):
            raise serializers.ValidationError(
                "This student has already registered. "
                "Please use the Login page."
            )

        if student.user_id is not None:
            raise serializers.ValidationError(
                "An account already exists for this student. "
                "Please contact the school administration."
            )

        return student.admission_number

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "The passwords do not match."
            })

        admission_number = attrs["admission_number"]
        submitted_code = attrs["registration_code"]

        try:
            student = Student.objects.get(
                admission_number__iexact=admission_number
            )
            registration_code = student.registration_code
        except (
            Student.DoesNotExist,
            StudentRegistrationCode.DoesNotExist,
        ):
            raise serializers.ValidationError({
                "registration_code": (
                    "A valid school registration code is required. "
                    "Please contact the school administration."
                )
            })

        if registration_code.used_at is not None:
            raise serializers.ValidationError({
                "registration_code": (
                    "This registration code has already been used. "
                    "Please use the Login page if you have an account."
                )
            })

        # A code with no expiry date remains valid until used
        # or replaced by authorized school administration.
        if (
            registration_code.expires_at is not None
            and registration_code.expires_at <= timezone.now()
        ):
            raise serializers.ValidationError({
                "registration_code": (
                    "This registration code has expired. "
                    "Please contact the school administration."
                )
            })

        if not check_password(
            submitted_code,
            registration_code.code_hash,
        ):
            raise serializers.ValidationError({
                "registration_code": (
                    "The registration code is incorrect."
                )
            })

        attrs["student_record"] = student
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        admission_number = validated_data["admission_number"]
        submitted_code = validated_data["registration_code"]

        student = (
            Student.objects.select_for_update()
            .get(admission_number__iexact=admission_number)
        )

        registration_code = (
            StudentRegistrationCode.objects.select_for_update()
            .get(student=student)
        )

        # Recheck registration eligibility inside the transaction.
        if (
            student.user_id is not None
            or student.registration_status
            == Student.RegistrationStatus.REGISTERED
        ):
            raise serializers.ValidationError(
                "This student has already registered. "
                "Please use the Login page."
            )

        code_expired = (
            registration_code.expires_at is not None
            and registration_code.expires_at <= timezone.now()
        )

        if (
            registration_code.used_at is not None
            or code_expired
            or not check_password(
                submitted_code,
                registration_code.code_hash,
            )
        ):
            raise serializers.ValidationError({
                "registration_code": (
                    "This registration code is invalid, expired, "
                    "or already used."
                )
            })

        # The student cannot choose their own name, class, or fee status.
        username = student.admission_number

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                "An account already exists for this admission number. "
                "Please contact the school administration."
            )

        user = User.objects.create_user(
            username=username,
            password=validated_data["password"],
            email=student.email or "",
        )

        student.user = user
        student.registration_status = (
            Student.RegistrationStatus.REGISTERED
        )
        student.save(update_fields=[
            "user",
            "registration_status",
            "updated_at",
        ])

        # A registration code can only be used once.
        registration_code.used_at = timezone.now()
        registration_code.save(update_fields=["used_at"])

        return student
